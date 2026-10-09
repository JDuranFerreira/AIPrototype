"""Trace the furniture-chairs row (the row _RELCL_FIX+_CHANGE_PROMOTE regress 12 -> None).

  python benchmarks/_tmp_chairstrace.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                               # noqa: E402
from brainlike.regions import Mind                          # noqa: E402
import brainlike.storyreader as sr                          # noqa: E402


def run(mind, fix_relcl, fix_promote, text):
    sr._RELCL_FIX = fix_relcl
    sr._CHANGE_PROMOTE = fix_promote
    reader = mind.language.reading.reader()
    sit = sr.Situation()
    sit.units = reader.frames.units
    v, how, tr = reader.solve(text, sit=sit)
    print(f"[relcl={fix_relcl} promote={fix_promote}] answer {v} | {how}")
    for k in sorted(sit.cells, key=str):
        print(f"    cell {k} = {sit.cells[k]}")
    for t in tr:
        print(f"    {t['clause'][:58]!r:62} did={t['did']} how={t['how']}")
    print()


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    rows = primary.outside_exam(mind.language.reading, 1, "test")["rows"]
    row = next(r for r in rows if "furniture" in r["text"])
    print(f"want {row['answer']} :: {row['text']}\n")
    for relcl, promote in ((False, False), (True, False), (False, True), (True, True)):
        run(mind, relcl, promote, row["text"])


if __name__ == "__main__":
    main()
