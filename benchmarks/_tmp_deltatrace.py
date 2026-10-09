"""Trace the delta stories with the delta reading on: value, rivals, doubts, checks.

  python benchmarks/_tmp_deltatrace.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402

import brainlike.storyreader as sr                              # noqa: E402

STORIES = [
    ("plums", "17 plums were in the basket. More plums were added to the basket. Now there are 21 plums. "
              "How many plums were added to the basket?"),
    ("Will", "For Halloween Will got fifteen pounds of candy. After giving nine pounds of candy to Haley, "
             "he had six pounds of candy left. How many pounds did he give to Haley?"),
    ("Adam", "Adam put eighteen items in the shopping cart. After deleting some items from the shopping "
             "cart, there are eight items in the shopping cart. How many items did Adam delete?"),
    ("furniture", "A furniture store had fifteen chairs. After selling some chairs, there are three chairs "
                  "in the store. How many chairs did they sell?"),
    ("cookies", "A package had eighteen cookies in it. After eating some cookies from the package, there "
                "are nine cookies in the package. How many were eaten?"),
    ("batteries", "Tom used 2 batteries on his flashlights, 15 in his toys and 2 in his clocks. How many "
                  "batteries did Tom use?"),
    ("shoes", "During a sale, a shoe store sold 2 pairs of sneakers, 4 pairs of boots, 7 pairs of dress "
              "shoes and 4 pairs of sandals. How many pairs of shoes did the store sell?"),
    ("Hilt", "Mrs. Hilt ate 5 apples every hour. How many apples had she eaten at the end of 3 hours?"),
]


def main():
    if "on" in sys.argv:
        sr._CHANGE_FIX_DELTA = True
        print("[delta reading ON]")
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for name, text in STORIES:
        value, how, trace = reader.solve(text)
        last = trace[-1]
        print(f"{name:<10} -> {value!s:<6} {how}")
        print(f"           did: {last.get('did')}  sure={last.get('sure')} unknown={last.get('unknown')}")
        if last.get("doubts"):
            print(f"           doubts: {last['doubts']}")
        if last.get("checks"):
            print(f"           checks: {last['checks']}")


if __name__ == "__main__":
    main()
