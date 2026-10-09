"""The real-problem library: word problems people wrote, taught with their answers, from public sets that are NOT
the exams. Every problem that is the same as, or a near-copy of, an ASDiv (any grade) or SVAMP problem is removed.

Sources:
  svamp_train.csv   MAWPS + ASDiv-A train (3,138), one equation each
  gsm8k_train.jsonl GSM8K train (7,473), with the worked steps <<a*b=c>> of every solution

  python benchmarks/library.py            stats: sizes, near-copies removed, by number of steps
"""
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

NEAR = 0.5          # word overlap (numbers masked) at or above this = a near-copy (0.6-0.7 were same templates)


def words(text):
    t = re.sub(r"\d+(?:[.,]\d+)?", " N ", text.lower())
    return set(re.findall(r"[a-z]+|N", t))


class Exams:
    """ASDiv (all grades) and SVAMP: what the library must not contain."""

    def __init__(self):
        from asdiv import load_asdiv
        from run_reader import load_svamp
        self.sets = [words(x["text"]) for g in range(1, 7) for x in load_asdiv(g)] + \
            [words(x["text"]) for x in load_svamp("svamp_dev.csv")]
        self.index = {}
        for i, s in enumerate(self.sets):
            for w in s:
                self.index.setdefault(w, []).append(i)

    def nearest(self, text):
        ws = words(text)
        counts = {}
        for w in ws:
            if len(self.index.get(w, ())) > 400:            # common words don't help find candidates
                continue
            for i in self.index.get(w, ()):
                counts[i] = counts.get(i, 0) + 1
        best = 0.0
        # tie-break on the set index: counts come from iterating a set of words, so without this the
        # top-30 (and a borderline near=0.5 keep/remove) would change with Python's hash randomization
        for i, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:30]:
            s = self.sets[i]
            best = max(best, len(ws & s) / len(ws | s))
        return best


def gsm8k_steps(answer):
    """GSM8K solution -> (final answer, [(expression, value)]) from the <<...=...>> marks."""
    steps = [(m[0].strip(), m[1].strip()) for m in re.findall(r"<<([^=<>]+)=([^<>]+)>>", answer)]
    final = answer.split("####")[-1].strip().replace(",", "")
    return final, steps


def load(exams=None, max_steps=3):
    """-> list of {"text", "answer" (Fraction), "steps", "source", "near"}; near-copies of exam problems removed."""
    from run_reader import load_svamp
    exams = exams or Exams()
    out, removed = [], {"svamp_train": 0, "gsm8k_train": 0}
    for x in load_svamp("svamp_train.csv"):
        steps = sum(x["template"].count(c) for c in "+-*/")
        if x["answer"] < 0 or steps > max_steps:
            continue
        near = exams.nearest(x["text"])
        if near >= NEAR:
            removed["svamp_train"] += 1
            continue
        out.append({"text": x["text"], "answer": Fraction(x["answer"]), "steps": steps, "source": "svamp_train",
                    "ops": "".join(sorted({c for c in x["template"] if c in "+-*/"})), "near": round(near, 2)})
    for line in (HERE / "gsm8k_train.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(line)
        final, steps = gsm8k_steps(x["answer"])
        try:
            ans = Fraction(final)
        except ValueError:
            continue
        if not steps or len(steps) > max_steps or ans < 0:
            continue
        near = exams.nearest(x["question"])
        if near >= NEAR:
            removed["gsm8k_train"] += 1
            continue
        out.append({"text": x["question"], "answer": ans, "steps": len(steps), "source": "gsm8k_train",
                    "ops": "".join(sorted({c for e, _ in steps for c in e if c in "+-*/"})), "work": steps,
                    "near": round(near, 2)})
    return out, removed


if __name__ == "__main__":
    lib, removed = load()
    from collections import Counter
    print("library:", len(lib), "removed as near-copies of exam problems:", removed)
    print("by source and steps:", sorted(Counter((x["source"], x["steps"]) for x in lib).items()))
    print("word overlap with the nearest exam problem (kept):",
          sorted(Counter(round(x["near"], 1) for x in lib).items()))
