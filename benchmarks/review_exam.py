"""After an exam, the teacher goes over the mistakes: for every world-exam story the real brain got wrong, it is told the
right answer and looks for the sentence it misread (as at school). Then it is tested on the same stories again and
on a NEW exam set it has never seen. The outside exams (ASDiv, the real-story exam) are never taught.

  python benchmarks/review_exam.py P1          (writes brain_state/: back it up first)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def by_topic(exam):
    by = defaultdict(lambda: [0, 0])
    for r in exam["rows"]:
        by[r["topic"]][0] += r["ok"]
        by[r["topic"]][1] += 1
    return ", ".join(f"{k} {a}/{b}" for k, (a, b) in by.items() if a < b) or "all right"


def main():
    level = sys.argv[1]
    state = HERE.parent / "brain_state"
    mind = Mind.load(state, {"model": "none", "url": ""})
    kg = mind.kindergarten
    rounds = kg.lessons.get(f"rounds_{level}", 0)
    items = primary.exam_items(level, "A", rounds)                     # the exam it just took
    exam = primary.take_exam(kg, items)
    wrong = [r for r in exam["rows"] if not r["ok"]]
    print(f"exam set {rounds + 1}: {exam['score']:.1%}, {len(wrong)} wrong ({by_topic(exam)})")
    for r in wrong:
        res = kg.learn_story(r["question"], r["expected"], taught_words=False)
        print(f"  told: {r['question']} = {r['expected']} (it said {r['got']}) -> {res.get('lesson')}")
    again = primary.take_exam(kg, items)
    print(f"same exam again: {again['score']:.1%} ({by_topic(again)})")
    new = primary.take_exam(kg, primary.exam_items(level, "B", rounds))   # a parallel exam it has never seen
    print(f"new exam it never saw: {new['score']:.1%} ({by_topic(new)})")
    o = primary.outside_exam(kg, primary.LEVELS[level]["asdiv"], "test")
    print(f"ASDiv grade {primary.LEVELS[level]['asdiv']} test half: right {o['right']}/{o['n']}, always answering {o['guess_right']}")
    mind.save(state)
    print("saved")


if __name__ == "__main__":
    main()
