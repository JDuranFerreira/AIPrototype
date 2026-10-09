"""Does a teacher's agreement actually reach the persisted doubt memory? Reads a story it gets right,
agrees with it, and reports what changed in mind.doubts. Read-only (nothing is saved)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                        # noqa: E402
from brainlike.storyreader import learn_from_answer                       # noqa: E402

STORY = ("There were 17 oranges in the basket. Five oranges were taken from the basket. "
         "Now there are 12 oranges. How many oranges are left in the basket?")
ANSWER = 12


def main():
    mind = Mind.load(HERE.parent / "brain_state")
    doubts = mind.doubts
    before = {"answer": dict(doubts.checks.get("answer", {})), "words": len(doubts.words),
              "total": sum(doubts.words.values())}
    reader = mind.language.reading.reader()
    got, how, _ = reader.solve(STORY)
    print(f"it answers: {got} ({how})")
    same_reader = reader.doubts is doubts
    print(f"reader.doubts is mind.doubts: {same_reader}")
    r = learn_from_answer(STORY, ANSWER, reader, reader.frames, weight=1)
    after = {"answer": dict(doubts.checks.get("answer", {})), "words": len(doubts.words),
             "total": sum(doubts.words.values())}
    print(f"lesson: {r.get('learned')!r} agreed={r.get('agreed')}")
    print(f"before: {before}")
    print(f"after:  {after}")
    print(f"passed counter moved: {before['answer'].get('passed', 0)} -> {after['answer'].get('passed', 0)}")
    print(f"word counters moved:  {before['words']} words / {before['total']} doubts "
          f"-> {after['words']} words / {after['total']} doubts")
    if not same_reader:
        print("!! the reader's doubt memory is NOT the mind's - confirmations are lost")


if __name__ == "__main__":
    main()
