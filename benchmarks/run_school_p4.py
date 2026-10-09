"""A fresh brain through the whole world-based school: kindergarten -> P1 -> P2 -> P3 -> P4 (one round each, with real
stories and sleep). After every stage: the world exams of every level, the kindergarten exam, and ASDiv grades 1-4,
dev half (looked at while improving) and test half (only measured). No language model.

  python benchmarks/run_school_p4.py [--save BRAIN.json]   -> results/school_p1_p4.json
"""
import copy
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def measure(kg):
    row = {lv: round(primary.take_exam(kg, primary.exam_items(lv, "A", 0))["score"], 3) for lv in primary.LEVELS}
    row["kindergarten"] = copy.deepcopy(kg).take_exam()["right"]
    for g in (1, 2, 3, 4):
        for split in ("dev", "test"):
            o = primary.outside_exam(kg, g, split)
            row[f"g{g} {split}"] = [o["right"], o["understood"], o["guess_right"], o["n"]]
    return row


def main():
    mind = Mind()
    rows = []
    t = time.time()
    mind.kindergarten.teach("all")
    rows.append(["kindergarten", measure(mind.kindergarten), round(time.time() - t)])
    print(rows[-1], flush=True)
    for lv in primary.LEVELS:
        t = time.time()
        entry = primary.run_level(mind, lv, log=lambda *_: None)
        primary.file_report(mind, entry)
        rows.append([lv, {**measure(mind.kindergarten), "grade": entry["grade"], "rules": entry.get("rules")},
                     round(time.time() - t)])
        print(rows[-1], flush=True)
    (HERE / "results" / "school_p1_p4.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    if "--save" in sys.argv:                          # the trained region, for later experiments
        Path(sys.argv[sys.argv.index("--save") + 1]).write_text(json.dumps(mind.kindergarten.state()), encoding="utf-8")


if __name__ == "__main__":
    main()
