"""Ask the brain a question and watch it try until it gets it right.

  python -m brainlike.demo 1+1            # uses the saved brain if there is one
  python -m brainlike.demo 1+1 --fresh    # a newborn brain that knows nothing
"""
import argparse
from pathlib import Path

from .brain import Brain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("problems", nargs="+", help="e.g. 1+1 7*8 5-9")
    ap.add_argument("--fresh", action="store_true", help="start from a newborn brain")
    ap.add_argument("--state", default="experiment_state", help="an experiment brain; the taught brain is used through serve.py")
    args = ap.parse_args()

    state = Path(args.state)
    if not args.fresh and (state / "meta.json").exists():
        brain = Brain.load(state)
        print(f"Loaded brain from {state}/ ({len(brain.memory)} memories)")
    else:
        brain = Brain()
        print("Newborn brain: knows nothing yet")

    for problem in args.problems + args.problems:        # second pass shows memory at work
        r = brain.solve(problem)
        if r["source"] == "memory":
            print(f"\n{problem} = {r['answer']}   remembered instantly (no module woke up)")
        else:
            print(f"\n{problem} = {r['answer']}   found by {r['source']} after {r['tries']} {'try' if r['tries'] == 1 else 'tries'}")
            if r["mistakes"]:
                print(f"   wrong guesses it learned from: {' '.join(map(str, r['mistakes']))}")

    brain.sleep(rounds=5)
    brain.save(state)
    print(f"\nSlept on it and saved to {state}/")


if __name__ == "__main__":
    main()
