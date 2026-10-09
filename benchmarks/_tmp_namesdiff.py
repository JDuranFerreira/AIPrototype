"""Row-level diff of an ASDiv exam with a storyreader flag off vs on (one process, toggle it).

  python benchmarks/_tmp_namesdiff.py [grade] [_FLAG_NAME]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                               # noqa: E402
from brainlike.regions import Mind                          # noqa: E402
import brainlike.storyreader as sr                          # noqa: E402

ATTRS = [a for a in sys.argv if a.startswith("_")] or ["_NAMES_FIX"]


def snap(grade, fix):
    for a in ATTRS:
        setattr(sr, a, fix)
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, "test")
    return {r["text"]: r for r in exam["rows"]}


def main():
    grade = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
    print(f"[rows off vs on: {', '.join(ATTRS)}]")
    off, on = snap(grade, False), snap(grade, True)
    for text in off:
        x, y = off[text], on[text]
        if (x["right"], x["understood"], x["guess_right"], str(x["got"])) != \
                (y["right"], y["understood"], y["guess_right"], str(y["got"])):
            print(f"{'RIGHT' if x['right'] else '     '} -> {'RIGHT' if y['right'] else '     '}  "
                  f"claim {int(x['understood'])}->{int(y['understood'])}  "
                  f"answerok {int(x['guess_right'])}->{int(y['guess_right'])}  "
                  f"got {x['got']}->{y['got']}  :: {text[:88]}")


if __name__ == "__main__":
    main()
