"""Diagnosis: does the brain keep what it learned (P1 after P2)? Does saving it lose knowledge? Where do grade-1
questions go in the chat?

  python benchmarks/diagnose_school.py

One fresh brain, stages: kindergarten -> P1 -> P2 -> P1 again -> P2 again (each school round with real stories).
After every stage the SAME fixed tests are taken (read only): ASDiv grade 1 and 2 (test half), the round-1 P1
and P2 world exams, and the P1 / P2 real-story exams.
"""
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from asdiv import load_asdiv                                    # noqa: E402
from brainlike import primary                                   # noqa: E402
from brainlike.kindergarten import Kindergarten                 # noqa: E402
from brainlike.regions import Mind                              # noqa: E402
from brainlike.serve import handle_kindergarten                 # noqa: E402

FIXED = {lv: primary.exam_items(lv, "A", 0) for lv in primary.LEVELS}


def measure(kg):
    row = {}
    for g in (1, 2):
        o = primary.outside_exam(kg, g)
        row[f"ASDiv{g}"] = f"{o['right']:2}/{o['n']} (und {o['understood']:2}, guess {o['guess_right']:2})"
    for lv in primary.LEVELS:
        row[f"{lv} world"] = f"{primary.take_exam(kg, FIXED[lv])['score']:.0%}"
        r = primary.real_exam(kg, lv)
        row[f"{lv} real"] = f"{r['right']:2}/{r['n']}"
    f = kg.frames.table
    row["frame keys"] = len(f["S"]) + len(f["Q"])
    row["pairs"] = sum(len(e["m"]) for t in f.values() for e in t.values())
    return row


def show(stage, row, t):
    print(f"{stage:14} " + " | ".join(f"{k} {v}" for k, v in row.items()) + f" | {t:.0f}s", flush=True)


def main():
    mind = Mind()
    t = time.time()
    mind.kindergarten.teach("all")
    show("kindergarten", measure(mind.kindergarten), time.time() - t)
    sleep = "nosleep" not in sys.argv
    print("with sleep" if sleep else "without sleep")
    for stage in ["P1", "P2", "P1", "P2"]:
        t = time.time()
        primary.file_report(mind, primary.run_level(mind, stage, log=lambda *_: None, sleep=sleep))
        show(f"{stage} round {mind.kindergarten.lessons[f'rounds_{stage}']}", measure(mind.kindergarten), time.time() - t)

    # memory: the real brain is saved and loaded after every command (counts are pruned when saved)
    kg = mind.kindergarten
    reloaded = Kindergarten(json.loads(json.dumps(kg.state())))
    unpruned = Kindergarten(json.loads(json.dumps({**kg.state(), "frames": kg.frames.state(prune=False)})))
    print("\nsaved and loaded (pruned):", measure(reloaded))
    print("saved and loaded (no pruning):", measure(unpruned))
    print(f"state size: {len(json.dumps(kg.state())) / 1e6:.2f} MB pruned, "
          f"{len(json.dumps({**kg.state(), 'frames': kg.frames.state(prune=False)})) / 1e6:.2f} MB unpruned")

    # regions: where a grade-1 question goes when it is typed in the chat
    routes = {}
    for x in load_asdiv(1):
        r = handle_kindergarten(copy.deepcopy(mind), "ask", {"action": "ask", "problem": x["text"]})
        where = "kindergarten (acted out)" if r and r.get("kind") == "story" else \
            "kindergarten (other)" if r else ("not a story for it: " +
                                              ("no digit / 'some'" if not Kindergarten.is_story(x["text"]) else
                                               "it couldn't act it out"))
        routes[where] = routes.get(where, 0) + 1
    print("\nASDiv grade 1 typed in the chat goes to:", routes)


if __name__ == "__main__":
    main()
