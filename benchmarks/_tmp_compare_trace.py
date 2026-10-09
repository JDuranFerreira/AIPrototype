"""Clause trace + final cells for the comparative-before-base rows.

  python benchmarks/_tmp_compare_trace.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Situation                     # noqa: E402

STORIES = [
    ("Ellen", "Ellen has six more balls than Marin. Marin has nine balls. "
              "How many balls does Ellen have?"),
    ("Brian", "Brian has four more plums than Paul. Paul has seven plums. "
              "How many plums does Brian have?"),
]


def main():
    if "namesfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._NAMES_FIX = True
        print("[namesfix on]")
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for name, text in STORIES:
        sit = Situation()
        value, how, trace = reader.solve(text, sit=sit)
        print(f"{name} -> {value!s} ({how})")
        for d in trace:
            tag = "Q" if d.get("question") else " "
            print(f"  {tag} {d['clause'][:70]!r:<72} did={d['did']} sure={d['sure']}")
            if d.get("doubts"):
                print(f"      doubts: {d['doubts']}")
        print("  cells:")
        for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
            first, now = (pair + [pair[-1]])[:2] if isinstance(pair, list) else (pair, pair)
            print(f"    {key!s:<40} now={now}  first={first}")


if __name__ == "__main__":
    main()
