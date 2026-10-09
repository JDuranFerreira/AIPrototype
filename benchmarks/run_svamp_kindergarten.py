"""SVAMP read by the kindergarten region: acting the story out with learned frames, no language model.

A fresh kindergarten is taught from the simulated world only (scenes, facts, events, stories); it never
sees a SVAMP problem. Then it reads SVAMP problems and answers only if it understood them.

  python benchmarks/run_svamp_kindergarten.py            # the test set: the first 300 SVAMP (same as the models)
  python benchmarks/run_svamp_kindergarten.py dev        # SVAMP 300-599, used while improving perception
  python benchmarks/run_svamp_kindergarten.py test show  # also print what it did on each problem

"Simple" problems = two numbers and one + or - (templates N0+N1, N0-N1, N1-N0), decided from SVAMP's own
equations, not from what the brain can do.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from run_reader import load_svamp                                  # noqa: E402
from brainlike.kindergarten import Kindergarten                    # noqa: E402

SIMPLE = {"(N0+N1)", "(N1+N0)", "(N0-N1)", "(N1-N0)"}


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "test"
    show = "show" in sys.argv
    rows = load_svamp("svamp_dev.csv")
    rows, offset = (rows[:300], 0) if split == "test" else (rows[300:600], 300)
    t = time.time()
    k = Kindergarten()
    k.teach("all")
    print(f"taught from the simulated world in {time.time() - t:.1f} s; story exam on new stories: "
          f"{k.take_exam()['right']}/{k.exam['of']}")
    reader = k.reader()
    results, t = [], time.time()
    for i, r in enumerate(rows):
        got, how, trace = reader.solve(r["text"])
        sure = got is not None and how == "understood every sentence"
        results.append({"i": i + offset, "got": None if got is None else str(got), "guessed": got is not None,
                        "answered": sure, "right": sure and got == r["answer"],
                        "guess_right": got is not None and got == r["answer"], "simple": r["template"] in SIMPLE})
        if show:
            mark = ("OK " if results[-1]["right"] else "NO ") if sure else ("?? " if got is None else
                                                                            ("g+ " if results[-1]["guess_right"] else "g- "))
            print(f"{mark}#{i + offset} {r['text']}\n     -> {got} (right {r['answer']}; {how})")
            for x in trace:
                print(f"        {x['clause']}  |  {'; '.join(x['did']) or '-'}  |  {x['how']}")
    dt = (time.time() - t) / len(rows)
    llms = {}
    if split == "test":
        for f in sorted((HERE / "results").glob("svamp300_*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            llms[f"{d['model']} {d['mode']}"] = {a["i"]: a["right"] for a in d["answers"]}

    def line(name, sel):
        n = len(sel)
        ans = sum(x["answered"] for x in sel)
        ok = sum(x["right"] for x in sel)
        guess = sum(x["guess_right"] for x in sel)
        out = (f"  {name:24} {n:4} | understood {ans:3} ({ans / n:.0%}), right {ok:3} = {ok / n:.1%} of all, "
               f"{(ok / ans if ans else 0):.0%} of those | answering everything: {guess / n:.1%}")
        for m, right in llms.items():
            out += f" | {m}: {sum(right[x['i']] for x in sel) / n:.0%}"
        return out
    print(f"SVAMP {split} ({len(rows)} problems, {dt * 1000:.1f} ms per problem, CPU, no language model)")
    print(line("all", results))
    print(line("simple (one + or -)", [x for x in results if x["simple"]]))
    print(line("not simple", [x for x in results if not x["simple"]]))
    answered = [x for x in results if x["answered"]]
    if answered and llms:
        print(line("only those it answered", answered))
    dest = HERE / "results" / f"svamp_{split}_kindergarten.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps({"split": split, "results": results, "ms_per_problem": round(dt * 1000, 2)}, indent=1),
                    encoding="utf-8")


if __name__ == "__main__":
    main()
