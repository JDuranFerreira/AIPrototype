"""Which questions ask for the amount BEFORE ('before', 'to begin with', 'originally', 'at first'),
and how each fares now?

  python benchmarks/_tmp_beforeq.py [grade] [split]
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402

BEFORE_Q = re.compile(r"\b(before|originally|at first|to begin with|in the beginning|initially)\b", re.I)


def main():
    grade = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
    split = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "beforefix" else "test"
    if "beforefix" in sys.argv:
        import brainlike.storyreader as sr
        sr._BEFORE_FIX = True
        print("[beforefix on]")
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, split)
    rows = []
    for r in exam["rows"]:
        q = r["text"].split("?")[0].split(".")[-1]
        if BEFORE_Q.search(q):
            rows.append(r)
    print(f"before-questions: {len(rows)} of {exam['n']}")
    right = claimed = 0
    for r in rows:
        right += r["right"]
        claimed += r["understood"]
        print(f"  {'CLAIM' if r['understood'] else '     '} {'RIGHT' if r['right'] else '     '} "
              f"want {str(r['answer']):>6} got {str(r['got']):>6} {r['how'][:26]:<26} :: {r['text']}")
    print(f"right {right}, claims {claimed}")


if __name__ == "__main__":
    main()
