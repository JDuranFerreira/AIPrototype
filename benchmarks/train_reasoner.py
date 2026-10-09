"""Train the brain's step-by-step reasoner on worked solutions written by people, then test it on
problems it has never seen. No language model anywhere.

Training: GSM8K train (7,473 step-by-step solutions) + MAWPS/ASDiv-A (3,138 equations) + ASDiv
(2,305 formulas) + the school's bar models.   Testing: SVAMP (1,000) and GSM8K test.

  python benchmarks/train_reasoner.py            # train, test, save into brain_state/language/
  python benchmarks/train_reasoner.py --no-save  # train + test only (low RAM: rebuilds the gold
                                                 # paths every epoch; add --cache to trade ~4 GiB
                                                 # RAM for ~3 min wall time)
  python benchmarks/train_reasoner.py --epochs 4
"""
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import compose, planner                                              # noqa: E402
from brainlike.curriculum import CURRICULUM                                         # noqa: E402
from brainlike.reasoner import Reasoner, steps_from_expression, steps_from_gsm8k    # noqa: E402
from run_reader import load_svamp                                                   # noqa: E402


def plan_value(plan):
    values = {}
    last = None
    for name, expr in planner.parse(plan):
        filled = re.sub(r"\br(\d+)\b", lambda m: f"({compose.fmt(values['r' + m.group(1)])})", expr)
        last = compose.true_value(compose.normalize(filled))
        if name:
            values[name] = last
    return last


def worked_examples():
    out, seen = [], {"svamp-train": [0, 0], "asdiv": [0, 0], "gsm8k": [0, 0], "school": [0, 0]}
    import csv
    with open(HERE / "svamp_train.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nums = [compose.fmt(Fraction(x)) for x in r["Numbers"].split()]
            text = r["Question"]
            for i, n in enumerate(nums):
                text = text.replace(f"number{i}", n)
            from brainlike.reader import prefix_to_template, fill
            expr = fill(prefix_to_template(r["Equation"]), nums)
            s = steps_from_expression(text, expr)
            seen["svamp-train"][1] += 1
            if s:
                out.append((text, s)); seen["svamp-train"][0] += 1
    for p in ET.parse(HERE / "asdiv.xml").getroot().iter("Problem"):
        text = f"{p.findtext('Body')} {p.findtext('Question')}"
        formula = (p.findtext("Formula") or "").split("=")[0]
        seen["asdiv"][1] += 1
        s = steps_from_expression(text, formula) if formula and re.fullmatch(r"[\d.+\-*/() ]+", formula) else None
        if s:
            out.append((text, s)); seen["asdiv"][0] += 1
    for line in open(HERE / "gsm8k_train.jsonl", encoding="utf-8"):
        g = json.loads(line)
        s = steps_from_gsm8k(g["question"], g["answer"])
        seen["gsm8k"][1] += 1
        if s:
            out.append((g["question"], s)); seen["gsm8k"][0] += 1
    for level in CURRICULUM.values():
        for part in level.values():
            for item in part["lessons"]:
                if item[0] == "word" and not re.search(r"\b(div|rem|divup)\b", item[2]) and not planner.is_plan(item[2]):
                    s = steps_from_expression(item[1], item[2])
                    seen["school"][1] += 1
                    if s:
                        out += [(item[1], s)] * 3; seen["school"][0] += 1
    return out, seen


def evaluate(reasoner, items):
    ok = 0
    t = time.time()
    for text, answer in items:
        plan = reasoner.read(text)
        try:
            ok += plan is not None and plan_value(plan) == answer
        except (ValueError, ZeroDivisionError, KeyError):
            pass
    return ok, (time.time() - t) / max(1, len(items))


def main():
    t = time.time()
    examples, seen = worked_examples()
    print("worked solutions it can learn from:", {k: f"{a}/{b}" for k, (a, b) in seen.items()},
          f"-> {len(examples)} ({time.time() - t:.0f}s)")
    epochs = int(sys.argv[sys.argv.index("--epochs") + 1]) if "--epochs" in sys.argv else 6
    t = time.time()
    reasoner = Reasoner().train(examples, epochs=epochs, log=print, cache="--cache" in sys.argv)
    print(f"trained in {time.time() - t:.0f}s, {reasoner.n_weights:,} non-zero weights")
    svamp = [(r["text"], r["answer"]) for r in load_svamp("svamp_dev.csv")]
    gsm = [json.loads(line) for line in open(HERE / "gsm8k_test.jsonl", encoding="utf-8")]
    random.Random(0).shuffle(gsm)
    gsm = [(g["question"], Fraction(g["answer"].split("####")[-1].strip().replace(",", ""))) for g in gsm]
    for name, items in [("SVAMP (1000)", svamp), ("SVAMP first 300", svamp[:300]), ("GSM8K first 100", gsm[:100]),
                        ("GSM8K 500", gsm[:500])]:
        ok, per = evaluate(reasoner, items)
        print(f"{name}: {ok}/{len(items)} = {ok / len(items):.1%}   ({per * 1000:.1f} ms per problem, CPU)")
    save_to = sys.argv[sys.argv.index("--save-to") + 1] if "--save-to" in sys.argv else None
    if save_to:
        reasoner.save(save_to)
        print(f"saved into {save_to}/reasoner.npz")
    elif "--no-save" not in sys.argv:
        reasoner.save(HERE.parent / "brain_state" / "language")
        print("saved into brain_state/language/reasoner.npz")


if __name__ == "__main__":
    main()
