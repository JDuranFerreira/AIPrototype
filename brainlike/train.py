"""Raise two brains the same way and compare them.

  modular : a router + 4 small modules; one module wakes per problem
  dense   : one big module of the same total size; everything wakes every time

Each "day" the brain meets new problems and learns by trial and error; each
"night" it sleeps and replays its memories. Some problems are never shown:
they measure whether it learned the RULES or only memorised facts.

Run:  python -m brainlike.train
"""
import argparse

import numpy as np

from . import task
from .brain import Brain


def held_out_accuracy(brain, problems):
    by_op = {op: [] for op in task.OPS}
    for p in problems:
        guess, _ = brain.first_guess(p)
        by_op[task.parse(p)[1]].append(task.check(p, guess))
    overall = np.mean([v for vs in by_op.values() for v in vs])
    return overall, {op: np.mean(vs) if vs else float("nan") for op, vs in by_op.items()}


def specialisation(brain):
    """For each operator: which module does the router send it to?"""
    counts = {op: np.zeros(len(brain.modules), dtype=int) for op in task.OPS}
    for p in task.all_problems():
        _, k = brain.first_guess(p)
        counts[task.parse(p)[1]][k] += 1
    return counts


def raise_brain(name, brain, train, test, days, sleep_rounds, quiet=False):
    per_day = max(1, len(train) // days)
    history = []
    if not quiet:
        print(f"\n=== {name}: {brain.total_params:,} weights, "
              f"{brain.active_params:,} used per new problem ===")
        print(f"{'day':>3} {'new':>4} {'avg tries':>9} {'memories':>8} "
              f"{'unseen right 1st try':>21}   + / - / *")
    for day in range(days):
        batch = train[day * per_day:(day + 1) * per_day]
        tries = [brain.solve(p)["tries"] for p in batch]
        brain.sleep(rounds=sleep_rounds)
        acc, ops = held_out_accuracy(brain, test)
        history.append((np.mean(tries), acc))
        if not quiet:
            print(f"{day + 1:>3} {len(batch):>4} {np.mean(tries):>9.1f} {len(brain.memory):>8} "
                  f"{acc:>20.0%}   " + " / ".join(f"{ops[o]:.0%}" for o in task.OPS))
    return history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--sleep", type=int, default=100, help="replay rounds per night")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--save", default="experiment_state", help="where to keep the modular brain (never brain_state/, the brain you teach)")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    problems = task.all_problems()
    rng.shuffle(problems)
    test, train = problems[:60], problems[60:]
    print(f"{len(train)} problems to learn from, {len(test)} never shown (the exam)")

    modular = Brain(n_modules=4, n_hidden=24, seed=args.seed)
    dense = Brain(n_modules=1, n_hidden=99, seed=args.seed)   # same total size
    sections = Brain(n_hidden=32, seed=args.seed, sections=True)   # one section per operation, never mixed

    raise_brain("MODULAR (router + 4 modules)", modular, train, test, args.days, args.sleep)
    raise_brain("DENSE (one big module)", dense, train, test, args.days, args.sleep)
    raise_brain("SECTIONS (addition / subtraction / multiplication)", sections, train, test, args.days, args.sleep)

    print("\nWhere the modular brain sends each kind of problem (count per module):")
    for op, c in specialisation(modular).items():
        print(f"  {op}  " + "  ".join(f"m{i}:{n:>3}" for i, n in enumerate(c)))

    modular.save(args.save)
    print(f"\nModular brain saved to {args.save}/ (weights + memory.json of what it learned)")


if __name__ == "__main__":
    main()
