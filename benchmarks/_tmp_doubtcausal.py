"""Causal doubt tick check: when it misreads a story, only the blamed sentence's words are doubted
(question / one sentence), or - if nothing is found - the unsure ones. In memory only."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                        # noqa: E402
from brainlike.storyreader import learn_from_answer                       # noqa: E402

CASES = [
    ("misread sentence (comparative)", 15,
     "Ellen has six more balls than Marin. Marin has nine balls. How many balls does Ellen have?"),
    ("misread question", 4,
     "17 plums were in the basket. More plums were added to the basket. Now there are 21 plums. "
     "How many plums were added?"),
]


def main():
    mind = Mind.load(HERE.parent / "brain_state")
    doubts = mind.doubts
    for label, answer, text in CASES:
        reader = mind.language.reading.reader()
        before = dict(doubts.words)
        got, how, _ = reader.solve(text)
        r = learn_from_answer(text, answer, reader, reader.frames, weight=1)
        ticked = {w: n - before.get(w, 0) for w, n in doubts.words.items() if n > before.get(w, 0)}
        print(f"\n{label}: it said {got}")
        print(f"  lesson: {r.get('learned')}")
        print(f"  words doubted this call: {ticked or 'NONE'}")


if __name__ == "__main__":
    main()