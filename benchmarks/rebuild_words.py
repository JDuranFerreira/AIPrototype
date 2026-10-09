"""Re-sort the real brain's word statistics by kind of situation (playground scenes, counting lessons), by replaying
the exact lessons it had (same seeds). Saves nothing unless every count matches the old statistics exactly.

  python benchmarks/rebuild_words.py brain_state            # check only
  python benchmarks/rebuild_words.py brain_state --save     # check, and save if it matches
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.kindergarten import WordLearner      # noqa: E402
from brainlike.primary import LEVELS, counting_scene  # noqa: E402
from brainlike.regions import Mind                   # noqa: E402
from brainlike.world import World                    # noqa: E402


def replay(lessons):
    """The real brain's history: kindergarten word lessons first (2000 scenes each), then school rounds alternating
    P1, P2, each with counting scenes seeded by the school stories taught before it."""
    rounds = [("P1", "P2")[i % 2] for i in range(lessons.get("rounds_P1", 0) + lessons.get("rounds_P2", 0))]
    counting = sum(LEVELS[lv]["counting"] for lv in rounds)
    playground = lessons["scenes"] - counting
    w = WordLearner()
    for k in range(0, playground, 2000):
        world = World(seed=1000 + k)
        for _ in range(2000):
            w.observe(*world.scene())
    stories = 0
    for lv in rounds:
        r = random.Random(5000 + stories)
        for _ in range(LEVELS[lv]["counting"]):
            w.observe(*counting_scene(r, LEVELS[lv]["count_to"]), context="counting")
        stories += LEVELS[lv]["stories"]
    return w


def main():
    state = Path(sys.argv[1])
    mind = Mind.load(state)
    old = mind.kindergarten.words
    new = replay(mind.kindergarten.lessons)
    same_words = dict(old.word) == dict(new.word)
    old_pair = {w: dict(f) for w, f in old.pair.items()}
    new_pair = {w: dict(f) for w, f in new.pair.items()}
    same_pairs = old_pair == new_pair
    print(f"scenes old {old.n} new {new.n} | word counts identical: {same_words} | word-feature counts identical: {same_pairs}")
    for w in ("red", "tom", "seven", "big", "the"):
        print(f"  {w:6} old meaning {old.meaning(w)}  ->  new {new.meaning(w)}")
    if "--save" in sys.argv:
        if not (same_words and same_pairs and old.n == new.n):
            print("not saved: the replay doesn't match exactly")
            return
        mind.kindergarten.words = new
        mind.kindergarten._lex = None
        mind.save(state)
        print("saved")


if __name__ == "__main__":
    main()
