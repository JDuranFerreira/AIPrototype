"""Clause-by-clause: what did each statement write in the rows doubt-release would newly claim?

  python benchmarks/_tmp_clausegap.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402

STORIES = [
    ("birds", "4 birds are sitting on a branch. 1 flies away. How many birds are left on the branch?"),
    ("marbles", "Two marbles are in the basket. Two marbles are taken out of the basket. "
                "How many marbles are in the basket now?"),
    ("book", "Mrs. Hilt picked up a book that has 17 pages in it. She read 11 of the pages. "
             "How many pages of the book had she read?"),
    ("oranges", "Some oranges were in the basket. Five oranges were taken from the basket. "
                "Now there are 3 oranges in the basket. How many oranges were in the basket before?"),
    ("marbles2", "There are some marbles in a box. Gale took 6 marbles out of the box. "
                 "There are now 4 marbles in the box. How many marbles were in the box before?"),
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for name, text in STORIES:
        value, how, trace = reader.solve(text)
        print(f"{name} -> {value!s} ({how})")
        for d in trace:
            tag = "Q" if d.get("question") else " "
            print(f"  {tag} {d['clause'][:70]!r:<72} did={d['did']} how={d['how']} sure={d['sure']}")


if __name__ == "__main__":
    main()
