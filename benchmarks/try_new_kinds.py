"""The new grade-1 situations (need, rate, removed): a fresh brain, kindergarten + one P1 round, then the P1 world
exam by kind and the ASDiv grade-1 DEV half, with the dev problems of those situations shown one by one.

  python benchmarks/try_new_kinds.py [oldkinds] [balanced] [blocking] [--save FILE]
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Frames                        # noqa: E402

NEW = ("need", "rate", "removed")
SITUATIONS = r"more .*need|need .*more|a day\b|per day|each day|every day|removed|got off|got on|taken out"


def main():
    Frames.BALANCED = "balanced" in sys.argv
    Frames.BLOCKING = "blocking" in sys.argv
    if "oldkinds" in sys.argv:
        for lv in primary.LEVELS.values():
            lv["kinds"] = [k for k in lv["kinds"] if k not in NEW]
    mind = Mind()
    mind.kindergarten.teach("all")
    primary.run_level(mind, "P1", log=lambda *_: None)
    kg = mind.kindergarten
    if "--save" in sys.argv:                       # for debugging: the trained region, as JSON
        import json
        Path(sys.argv[sys.argv.index("--save") + 1]).write_text(json.dumps(kg.state()), encoding="utf-8")
    exam = primary.take_exam(kg, primary.exam_items("P1", "A", 0))
    by = {}
    for r in exam["rows"]:
        b = by.setdefault(r["topic"], [0, 0])
        b[0] += r["ok"]
        b[1] += 1
    print("P1 world exam:", f"{exam['score']:.1%}", " ".join(f"{k} {a}/{b}" for k, (a, b) in by.items()))
    for split in ("dev", "test"):
        o = primary.outside_exam(kg, 1, split)
        print(f"ASDiv g1 {split}: right {o['right']}/{o['n']}, understood {o['understood']}, always answering {o['guess_right']}")
        if split == "dev":
            for r in o["rows"]:
                if re.search(SITUATIONS, r["text"], re.I):
                    print(f"  {'OK ' if r['right'] else 'ok?' if r['guess_right'] else ' - '} {r['text']} = {r['answer']}"
                          f"  -> {r['got']} ({r['how'][:70]})")


if __name__ == "__main__":
    main()
