"""Give the real brain its episodic memory: regenerate exactly the stories it lived through (same seeds; nothing is
learned from them here), keep a fair sample per stage, then (with --sleep) one night's sleep.

  python benchmarks/recall_episodes.py brain_state            # check
  python benchmarks/recall_episodes.py brain_state --sleep    # remember, sleep and save
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                       # noqa: E402
from brainlike.regions import Mind                   # noqa: E402
from brainlike.stories import Storyteller            # noqa: E402


def measure(kg):
    out = {}
    for g in (1, 2):
        o = primary.outside_exam(kg, g)
        out[f"ASDiv{g}"] = f"{o['right']}/{o['n']} (und {o['understood']}, guess {o['guess_right']})"
    for lv in primary.LEVELS:
        out[f"{lv} world"] = f"{primary.take_exam(kg, primary.exam_items(lv, 'A', 0))['score']:.1%}"
        out[f"{lv} real"] = primary.real_exam(kg, lv)["right"]
    out["kindergarten"] = kg.take_exam()["right"]
    return out


def main():
    state = Path(sys.argv[1])
    mind = Mind.load(state)
    kg = mind.kindergarten
    L = kg.lessons
    t = time.time()
    # kindergarten story lessons (3000 each, seeds 3000 + stories told before), then the school rounds
    rounds = [("P1", "P2")[i % 2] for i in range(L.get("rounds_P1", 0) + L.get("rounds_P2", 0))]
    kinder = L["stories"] - L.get("school_stories", 0)
    for k in range(0, kinder, 3000):
        teller = Storyteller(seed=3000 + k)
        for _ in range(3000):
            kg.remember("kindergarten", teller.tale())
    told = 0
    for lv in rounds:
        cfg = primary.LEVELS[lv]
        teller = primary.SchoolTeller(seed=6000 + told, kinds=cfg["kinds"], top=cfg["top"])
        for _ in range(cfg["stories"]):
            kg.remember(lv, teller.tale())
        told += cfg["stories"]
    for lv in primary.LEVELS:
        pool, _ = primary.real_stories(lv)
        for text, answer in pool[:L.get(f"real_{lv}", 0)]:
            kg.remember(f"real {lv}", real=(text, answer))
    print(f"remembered ({time.time() - t:.0f}s):", {k: f"{len(v)} of {kg.seen_episodes[k]}" for k, v in kg.episodes.items()})
    if "--sleep" in sys.argv:
        before = measure(kg)
        print("before sleep:", before)
        print("sleep:", kg.sleep(primary.SLEEP))
        print("after sleep: ", measure(kg))
        mind.save(state)
        print("saved")


if __name__ == "__main__":
    main()
