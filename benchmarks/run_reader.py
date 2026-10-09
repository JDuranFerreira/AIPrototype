"""Train the brain's reader on MAWPS + ASDiv-A and test it on SVAMP (the standard split), GSM8K and the
brain's own school word problems. No language model anywhere.

  python benchmarks/run_reader.py
"""
import csv
import json
import random
import sys
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import compose                                            # noqa: E402
from brainlike.curriculum import CURRICULUM                              # noqa: E402
from brainlike.reader import Reader, mask, number_sense, prefix_to_template, school_examples  # noqa: E402


def load_svamp(name):
    rows = []
    with open(HERE / name, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nums = [compose.fmt(Fraction(x)) for x in r["Numbers"].split()]
            text = r["Question"]
            for i, n in enumerate(nums):
                text = text.replace(f"number{i}", n)
            rows.append({"text": text, "answer": Fraction(r["Answer"]), "template": prefix_to_template(r["Equation"]),
                         "type": r.get("Type", "")})
    return rows


def as_example(row):
    masked, nums = mask(row["text"])
    return masked, nums, row["template"]


def solved(reader, text, answer):
    r = reader.read(text, number_sense)
    if not r:
        return False
    try:
        return compose.true_value(compose.normalize(r[0])) == answer
    except (ValueError, ZeroDivisionError):
        return False


def main():
    train, test = load_svamp("svamp_train.csv"), load_svamp("svamp_dev.csv")
    t = time.time()
    school = school_examples(CURRICULUM)                 # the teacher's bar models, weighted like 5 examples each
    reader = Reader().train([as_example(r) for r in train] + school * 5, epochs=15, l2=0, min_count=1)
    print(f"trained on {len(train)} MAWPS+ASDiv-A problems in {time.time() - t:.1f}s: "
          f"{len(reader.templates)} schemas, {reader.n_weights:,} weights")
    t = time.time()
    ok = sum(solved(reader, r["text"], r["answer"]) for r in test)
    per = (time.time() - t) / len(test)
    print(f"SVAMP (1000, unseen): {ok}/{len(test)} = {ok / len(test):.1%}   ({per * 1000:.1f} ms per problem, CPU)")
    by_type = {}
    for r in test:
        by_type.setdefault(r["type"], []).append(solved(reader, r["text"], r["answer"]))
    print("  by type:", {k: f"{sum(v)}/{len(v)}" for k, v in by_type.items()})
    gsm = [json.loads(line) for line in open(HERE / "gsm8k_test.jsonl", encoding="utf-8")]
    random.Random(0).shuffle(gsm)
    gsm = gsm[:200]
    ok = sum(solved(reader, g["question"], Fraction(g["answer"].split("####")[-1].strip().replace(",", ""))) for g in gsm)
    print(f"GSM8K (200 sampled): {ok}/200 = {ok / 200:.1%}")
    reader.save(HERE.parent / "brain_state" / "language")
    print("saved the reader into brain_state/language/")


if __name__ == "__main__":
    main()
