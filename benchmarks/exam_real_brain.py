"""Read-only exam of the real brain on one level: a world exam it has never seen (the next round's exam set), the real-
story exam and the outside ASDiv exam of that grade. Nothing is learned and brain_state/ is not written.

  python benchmarks/exam_real_brain.py P1
"""
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def main():
    level = sys.argv[1]
    kg = Mind.load(HERE.parent / "brain_state").language.reading
    rounds = kg.lessons.get(f"rounds_{level}", 0)
    items = primary.exam_items(level, "A", rounds)            # the next round's exam: it has never seen these stories
    exam = primary.take_exam(kg, items)
    by = defaultdict(lambda: [0, 0])
    for r in exam["rows"]:
        by[r["topic"]][0] += r["ok"]
        by[r["topic"]][1] += 1
    lv = primary.LEVELS[level]
    print(f"{level} world exam (exam set {rounds + 1}, {len(items)} new stories): {exam['score']:.1%} "
          f"-> {primary.al(exam['score'])}; it said it understood {exam['predicted']:.0%}")
    print("  by topic: " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in by.items()))
    for r in [r for r in exam["rows"] if not r["ok"]][:6]:
        print(f"  wrong: {r['question']} = {r['expected']} -> {r['got']}")
    real = primary.real_exam(kg, level)
    print(f"real-story exam ({real['n']} word problems people wrote, never read): right {real['right']}, "
          f"understood {real['understood']}, if it always answers {real['guess_right']}")
    o = primary.outside_exam(kg, lv["asdiv"], "test")
    print(f"ASDiv grade {lv['asdiv']} test half ({o['n']} problems, no language model): right {o['right']} "
          f"({o['right'] / o['n']:.1%}), understood {o['understood']}, if it always answers {o['guess_right']}")


if __name__ == "__main__":
    main()
