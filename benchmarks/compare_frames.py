"""Sentence-frame interference: pooled frame statistics vs per-situation ones, with and without sleep.

  python benchmarks/compare_frames.py pooled|balanced sleep|nosleep [SAY]

One fresh brain: kindergarten -> P1 -> P2 -> P1 -> P2 (each round with real stories). After every stage the same
fixed tests (read only): ASDiv grade 1 and 2, dev half (used for decisions) and test half (reported), as
right / understood / right when it always answers; and the round-1 P1 and P2 world exams.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Frames                        # noqa: E402

def measure(kg):
    row = {}
    for g in (1, 2):
        for split in ("dev", "test"):
            o = primary.outside_exam(kg, g, split)
            row[f"g{g} {split}"] = [o["right"], o["understood"], o["guess_right"], o["n"]]
    for lv in primary.LEVELS:
        row[f"{lv} world"] = round(primary.take_exam(kg, primary.exam_items(lv, "A", 0))["score"], 3)
    import copy
    row["kindergarten exam"] = copy.deepcopy(kg).take_exam()["right"]
    return row


def main():
    Frames.BALANCED = sys.argv[1] == "balanced"
    if "oldkinds" in sys.argv:                  # the P1-P2 stories before the need / rate / removed kinds were added
        sys.argv.remove("oldkinds")
        for lv in primary.LEVELS.values():
            lv["kinds"] = [k for k in lv["kinds"] if k not in ("need", "rate", "removed")]
        tag = "-oldkinds"
    else:
        tag = ""
    sleep = sys.argv[2] == "sleep"
    if len(sys.argv) > 3:
        Frames.SAY = int(sys.argv[3])
    name = f"{sys.argv[1]}-{sys.argv[2]}" + (f"-say{Frames.SAY}" if len(sys.argv) > 3 else "") + tag
    mind = Mind()
    rows = []
    t = time.time()
    mind.kindergarten.teach("all")
    rows.append(["kindergarten", measure(mind.kindergarten)])
    print(name, rows[-1], f"{time.time() - t:.0f}s", flush=True)
    for stage in ["P1", "P2", "P1", "P2"]:
        t = time.time()
        primary.run_level(mind, stage, log=lambda *_: None, sleep=sleep)
        rows.append([f"{stage} round {mind.kindergarten.lessons[f'rounds_{stage}']}", measure(mind.kindergarten)])
        print(name, rows[-1], f"{time.time() - t:.0f}s", flush=True)
    out = HERE / "results" / f"compare_frames_{name}{'-final' if 'final' in sys.argv else ''}.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
