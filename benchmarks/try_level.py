"""Develop a school level quickly on a saved brain.

  python benchmarks/try_level.py build FILE                 a fresh brain: kindergarten + P1 + P2 (one round each), saved
  python benchmarks/try_level.py run FILE LEVEL [--save OUT] [--show TYPE]
        load FILE, one round of LEVEL, then the level's world exam by kind and the ASDiv DEV half of its grade,
        by ASDiv problem type (and the failing dev problems of TYPE)
  python benchmarks/try_level.py look FILE GRADE [--show TYPE]   read only: the ASDiv dev half of GRADE

The test half is printed as one number only.
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from asdiv import load_asdiv                                    # noqa: E402
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def load(path):
    mind = Mind()
    mind.install_reading(json.loads(Path(path).read_text(encoding="utf-8")))
    return mind


def save(mind, path):
    Path(path).write_text(json.dumps(mind.kindergarten.state()), encoding="utf-8")


def by_type(kg, grade, show=None):
    rows = [x for i, x in enumerate(primary.load_outside(grade)) if i % 2 == 0]
    types = {x["id"]: x.get("type", "?") for x in rows}
    o = primary.outside_exam(kg, grade, "dev")
    t = defaultdict(lambda: [0, 0, 0, 0])
    for r in o["rows"]:
        b = t[types.get(r["id"], "?")]
        b[0] += r["right"]
        b[1] += r["understood"]
        b[2] += r["guess_right"]
        b[3] += 1
    print(f"outside ({grade}) dev: right {o['right']}/{o['n']}, understood {o['understood']}, "
          f"always answering {o['guess_right']}")
    print("   by type (right/understood/always/n): " +
          "  ".join(f"{k} {a}/{b}/{c}/{n}" for k, (a, b, c, n) in sorted(t.items(), key=lambda kv: -kv[1][3])))
    if show:
        for r in o["rows"]:
            if types.get(r["id"]) == show and not r["right"]:
                print(f"   - {r['text'][:160]} = {r['answer']} -> {r['got']} ({r['how'][:60]})")
    test = primary.outside_exam(kg, grade, "test")
    print(f"outside ({grade}) test: right {test['right']}/{test['n']}, understood {test['understood']}, "
          f"always answering {test['guess_right']}")


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    show = sys.argv[sys.argv.index("--show") + 1] if "--show" in sys.argv else None
    t = time.time()
    if cmd == "build":
        mind = Mind()
        mind.kindergarten.teach("all")
        for lv in ("P1", "P2"):
            primary.run_level(mind, lv, log=lambda *_: None)
        save(mind, path)
        for g in (1, 2):
            by_type(mind.kindergarten, g)
    elif cmd == "run":
        level = sys.argv[3]
        mind = load(path)
        entry = primary.run_level(mind, level, log=print)
        if "--save" in sys.argv:
            save(mind, sys.argv[sys.argv.index("--save") + 1])
        exam = primary.take_exam(mind.kindergarten, primary.exam_items(level, "A", 0))
        k = defaultdict(lambda: [0, 0])
        for r in exam["rows"]:
            k[r["topic"]][0] += r["ok"]
            k[r["topic"]][1] += 1
        print(f"{level} world exam A (round 1): {exam['score']:.1%}  " + " ".join(f"{a} {b}/{c}" for a, (b, c) in k.items()))
        print(f"report card: {entry['grade']}, attempts {[round(a['score'], 3) for a in entry['attempts']]}")
        by_type(mind.kindergarten, primary.LEVELS[level]["asdiv"], show)
        for lv in primary.LEVELS:
            if lv != level and list(primary.LEVELS).index(lv) < list(primary.LEVELS).index(level):
                print(f"  still knows {lv}: {primary.take_exam(mind.kindergarten, primary.exam_items(lv, 'A', 0))['score']:.1%}")
    else:
        mind = load(path)
        by_type(mind.kindergarten, int(sys.argv[3]), show)
    print(f"{time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
