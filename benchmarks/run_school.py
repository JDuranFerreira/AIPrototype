"""The world-based primary school, measured: a fresh brain goes through kindergarten, P1 and P2 (all from
the simulated world), then reads ASDiv grade 1 and grade 2 with no language model. The language models
answer the same problems (benchmarks/results/asdiv*_*.json, from run_llm_per_problem.py).

  python benchmarks/run_school.py            # one round of P1 and P2, world stories only
  python benchmarks/run_school.py 2 real     # two rounds, each with real stories (MAWPS, without ASDiv/SVAMP)

ASDiv's problems of each grade are split in two: the even ones are the dev half (looked at while
improving the brain's perception), the odd ones the test half (never looked at). Both are shown.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                       # noqa: E402
from brainlike.regions import Mind                   # noqa: E402


def main():
    t = time.time()
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    real = len(sys.argv) > 2 and sys.argv[2] == "real"
    mind = Mind()
    mind.kindergarten.teach("all")
    for r in range(rounds):
        for level in primary.LEVELS:
            e = primary.run_level(mind, level, log=lambda *_: None, real=real)
            tries = " -> ".join(f"{a['exam']} {a['score']:.0%}" for a in e["attempts"])
            print(f"round {r + 1} {level}: readiness {e['readiness']:.0%}, exam {tries} ({e['grade']}); says it understood "
                  f"{e['predicted']:.0%}" + (f"; real-story exam {e['real']['right']}/{e['real']['n']}" if real else ""))
    print(f"(taught in {time.time() - t:.0f} s, CPU, no language model)\n")
    out = {}
    for grade in (1, 2):
        llms = {}
        for f in sorted((HERE / "results").glob(f"asdiv{grade}_*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            llms[f"{d['model']}"] = {a["i"]: a["right"] for a in d["answers"]}
        for split in ("dev", "test"):
            t = time.time()
            r = primary.outside_exam(mind.kindergarten, grade, split)
            ms = (time.time() - t) / r["n"] * 1000
            idx = [i for i in range(r["n"] * 2 + 1) if (i % 2 == 1) == (split == "test")][:r["n"]]
            line = (f"ASDiv grade {grade} {split:4} ({r['n']:3}): brain understood {r['understood']:3}, right "
                    f"{r['right'] / r['n']:5.1%} ({r['right'] / max(1, r['understood']):.0%} of those) | always answering "
                    f"{r['guess_right'] / r['n']:5.1%} | {ms:.1f} ms/problem")
            for m, right in llms.items():
                line += f" | {m}: {sum(right.get(i, False) for i in idx) / r['n']:.1%}"
                und = [i for i, row in zip(idx, r["rows"]) if row["understood"]]
                if und:
                    line += f" ({sum(right.get(i, False) for i in und) / len(und):.0%} on the ones it understood)"
            print(line)
            out[f"{grade}-{split}"] = {k: r[k] for k in ("n", "understood", "right", "guess_right")}
    name = f"school_asdiv_{rounds}rounds_{'real' if real else 'world'}.json"
    (HERE / "results" / name).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
