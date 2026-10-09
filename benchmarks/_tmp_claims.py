"""The remaining wrong-claim rows: full statement/answer trace."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                              # noqa: E402
import brainlike.storyreader as sr                              # noqa: E402

ROWS = [
    ("pennies", "Mrs. Hilt has two pennies, two dimes, and two nickels. Jacob has four pennies, "
     "one dime, and one nickel.", "How much money do they have altogether?"),
    ("book", "Mrs. Hilt picked up a book that has 17 pages in it. She read 11 of the pages.",
     "How many pages does she have left to read?"),
    ("baker", "A baker sold twelve cakes.", "Now he has three cakes. How many cakes did the baker have at first?"),
    ("grapes", "A chef bought 2 purple grapes and 2 green grapes.",
     "If he already had 3 grapes, how many grapes does he have now?"),
    ("clown", "A clown gave away eleven balloons to girls and three balloons to boys.",
     "How many balloons did the clown give away?"),
    ("marbles", "Two marbles are in the basket. Two marbles are taken out of the basket.",
     "How many marbles are left in the basket?"),
]


def main():
    for a in sys.argv[1:]:
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for name, story, qtext in ROWS:
        v, how, tr = reader.solve(story + " " + qtext)
        print(f"--- {name}: answer {v} | {how}")
        for t in tr:
            tag = "Q:" if t.get("question") else "  "
            print(f"   {tag} {t['clause'][:72]}")
            print(f"       did={t.get('did')} how={t.get('how')} chance={t.get('c')}")


if __name__ == "__main__":
    main()
