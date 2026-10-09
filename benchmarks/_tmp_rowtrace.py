"""Trace ASDiv rows by keyword: what every statement writes to the cells, and how the question answers.

  python benchmarks/_tmp_rowtrace.py GRade KEYWORD [_FLAG ...]

Flags starting with '_' are switched on for the run (e.g. _CHANGE_PROMOTE).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                               # noqa: E402
from brainlike.regions import Mind                          # noqa: E402
import brainlike.storyreader as sr                          # noqa: E402


def trace(mind, text):
    reader = mind.language.reading.reader()
    sit = sr.Situation()
    sit.units = reader.frames.units
    v, how, tr = reader.solve(text, sit=sit)
    print(f"  answer {v} | {how}")
    for k in sorted(sit.cells, key=str):
        print(f"      cell {k} = {sit.cells[k]}")
    for t in tr:
        print(f"      {t['clause'][:62]!r:66} did={t['did']} how={t['how']}")


def main():
    args = sys.argv[1:]
    grade = int(args[0]) if args and args[0].isdigit() else 1
    key = next((a for a in args if not a.startswith("_") and not a.isdigit()), "")
    for a in args:
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    rows = primary.outside_exam(mind.language.reading, grade, "test")["rows"]
    hits = [r for r in rows if key.lower() in r["text"].lower()]
    if not hits:
        print(f"no row matches {key!r}")
        return
    for r in hits:
        print(f"\nwant {r['answer']} got {r['got']} claim={int(r['understood'])} "
              f"ok={int(r['guess_right'])} :: {r['text']}")
        trace(mind, r["text"])


if __name__ == "__main__":
    main()
