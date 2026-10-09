"""Measure the code lesson on the brain: the S1 'each one holds N' family before and after it is taught.

The lesson itself lives in brainlike/coding.py (the same one the Brain tab's **Code** button runs), so
teaching material has one home; this benchmark only measures the before/after and the rewards.

  python benchmarks/teach_coding.py             # measure, teach, use, and save the brain
  python benchmarks/teach_coding.py --dry-run   # measure and teach, save nothing
  python benchmarks/teach_coding.py --teach-only  # skip the before/after: just the lesson
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
try:                                    # the working has − and ✓ in it: don't let the console's code page crash us
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
from brainlike import coding, serve                                      # noqa: E402
from brainlike.regions import Mind                                       # noqa: E402

# the S1 family: the exact questions it used to get wrong (it multiplied instead of rounding up)
FAMILY = ["There are 715 people. Each boat holds 93 people. How many boats do they need?",
          "There are 428 people. Each car holds 11 people. How many cars are needed?",
          "344 children. Each bus can hold 4 children. How many buses do they need?",
          "32 children are going on a trip. 3 children can ride in each tent. How many tents do they need?"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(HERE.parent / "brain_state"))
    ap.add_argument("--dry-run", action="store_true", help="teach a copy and save nothing")
    ap.add_argument("--teach-only", action="store_true", help="no before/after: just the lesson")
    args = ap.parse_args()
    mind = Mind.load(args.state)
    before = []
    if not args.teach_only:
        before = [(q, serve.handle(mind, {"action": "ask", "problem": q}).get("answer")) for q in FAMILY]
        print("the S1 family BEFORE any recipe:")
        for q, a in before:
            print(f"  {a}   {q[:80]}")
    entry = coding.run_level(mind)
    if before:
        after = [(q, serve.handle(mind, {"action": "ask", "problem": q}).get("answer")) for q in FAMILY]
        print("the S1 family AFTER the recipes:")
        for (q, b), (_, a) in zip(before, after):
            print(f"  before {b} -> after {a}   {q[:70]}")
    print(f"code exam: {entry['score']:.0%} -> {entry['grade']}   "
          f"(tools {entry['tools']['kept']}/{entry['tools']['of']}, "
          f"recipes {entry['recipes']['kept']}/{entry['recipes']['of']})")
    print(f"rewards for the tools: {json.dumps(mind.coordination.summary(), ensure_ascii=False)}")
    if not args.dry_run:
        from brainlike import primary
        primary.file_report(mind, entry, subject="code")
        mind.save(args.state)
        print(f"saved to {args.state}")


if __name__ == "__main__":
    main()
