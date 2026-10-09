"""How much should a corrected exam mistake count? On copies of the real brain: take exam set C, go over the mistakes with
the explanation counted K times, then take a DIFFERENT new exam (set B of a later round) to see if it helped or hurt.

  python benchmarks/try_review_weight.py P2 3 10 30
"""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def main():
    level, weights = sys.argv[1], [int(x) for x in sys.argv[2:]]
    base = Mind.load(HERE.parent / "brain_state").language.reading
    after = primary.exam_items(level, "B", 50)                  # a new exam nobody uses: the side-effect check
    before = primary.take_exam(base, after)["score"]
    others = {lv: primary.take_exam(base, primary.exam_items(lv, "B", 50))["score"] for lv in primary.LEVELS if lv != level}
    print(f"before: new {level} exam {before:.1%}; other levels " + " ".join(f"{k} {v:.1%}" for k, v in others.items()))
    for k in weights:
        kg = copy.deepcopy(base)
        primary.EXPLAINED = k
        r = primary.review_exam(kg, level, round_no=0)
        sc = primary.take_exam(kg, after)["score"]
        oth = " ".join(f"{lv} {primary.take_exam(kg, primary.exam_items(lv, 'B', 50))['score']:.1%}" for lv in others)
        print(f"explanation counted {k:2}x: exam {r['score']:.1%}, fixed {r['fixed']}/{len(r['reviewed'])}; "
              f"then a new {level} exam {sc:.1%}; other levels {oth}")


if __name__ == "__main__":
    main()
