"""List the comparative rows of an ASDiv split (more/fewer ... than): want / got / claim / how."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import re                                                   # noqa: E402
from brainlike import primary                               # noqa: E402
from brainlike.regions import Mind                          # noqa: E402

COMPARE = re.compile(r"\b(?:more|fewer|less|fewer)\b.*\bthan\b|\bthan\b", re.I)


def main():
    grade = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
    state = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "namesfix" else HERE.parent / "brain_state"
    if "namesfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._NAMES_FIX = True
        print("[namesfix on]")
    mind = Mind.load(state, {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, "test")
    rows = [r for r in exam["rows"] if COMPARE.search(r["text"])]
    print(f"comparative rows: {len(rows)} of {exam['n']}")
    right = claimed = 0
    for r in rows:
        right += r["right"]
        claimed += r["understood"]
        print(f"  {'CLAIM' if r['understood'] else '     '} want {str(r['answer']):>6} "
              f"got {str(r['got']):>6} {'RIGHT' if r['right'] else '     '} {r['how'][:26]:<26} :: {r['text'][:90]}")
    print(f"right {right}, claims {claimed}")


if __name__ == "__main__":
    main()
