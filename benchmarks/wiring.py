"""Do the brain's connections and its efficiency improve? Measured, not claimed.

Every variant is raised exactly like brainlike.train does (the same problems, the same days, the
same sleep), and only the wiring changes. For each one:

  unseen      how often it is right FIRST try on problems it was never shown (rules, not facts)
  tries       how many wrong guesses it needed per new problem (how much work to learn)
  connected   connections used per new problem - the real cost, after pruning
  all weights how big it is in memory
  + / - / *   unseen accuracy per operation

  python benchmarks/wiring.py            # all variants, 3 seeds
  python benchmarks/wiring.py --seeds 1  # quicker
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import task                                # noqa: E402
from brainlike.brain import Brain                         # noqa: E402

# name -> extra wiring for the Brain (all off = today's brain)
VARIANTS = {
    "today": {},
    "sections": {"sections": True},
    "prune-use": {"prune": 0.02},
    "router-day": {"router_day": 0.5},
    # capacity where the work is hard: multiplication gets the neurons, the easy ones get fewer
    "sections-small": {"sections": True, "hidden_per_op": [16, 16, 16]},
    "sections-x-big": {"sections": True, "hidden_per_op": [12, 12, 60]},
    "sections-x-big+prune": {"sections": True, "hidden_per_op": [12, 12, 60], "prune": 0.02},
    "sections-small+prune": {"sections": True, "hidden_per_op": [16, 16, 16], "prune": 0.02},
}


def raise_one(brain, train, test, days, sleep_rounds):
    per_day = max(1, len(train) // days)
    tries = []
    for day in range(days):
        for p in train[day * per_day:(day + 1) * per_day]:
            tries.append(brain.solve(p)["tries"])
        brain.sleep(rounds=sleep_rounds)
    by_op = {op: [] for op in task.OPS}
    for p in test:
        guess, _ = brain.first_guess(p)
        by_op[task.parse(p)[1]].append(task.check(p, guess))
    unseen = float(np.mean([v for vs in by_op.values() for v in vs]))
    return {"unseen": unseen, "tries": float(np.mean(tries)),
            "ops": {op: float(np.mean(vs)) for op, vs in by_op.items()},
            "connected": brain.active_connections, "weights": brain.total_params}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--sleep", type=int, default=100)
    ap.add_argument("--only", default=None, help="run one variant only")
    args = ap.parse_args()
    names = [args.only] if args.only else list(VARIANTS)
    print(f"{args.days} days, {args.seeds} seeds, {len(task.all_problems()) - 60} problems to learn from, "
          f"60 never shown\n")
    head = f"{'variant':>18} {'unseen':>7} {'+':>5} {'-':>5} {'*':>5} {'tries':>6} {'connected':>10} {'of which':>9}"
    print(head)
    print("-" * len(head))
    for name in names:
        rows = []
        for seed in range(args.seeds):
            rng = np.random.default_rng(seed)
            problems = task.all_problems()
            rng.shuffle(problems)
            test, train = problems[:60], problems[60:]
            rows.append(raise_one(Brain(n_modules=4, n_hidden=24, seed=seed, **VARIANTS[name]),
                                  train, test, args.days, args.sleep))
        mean = {k: float(np.mean([r[k] for r in rows])) for k in ("unseen", "tries", "connected", "weights")}
        ops = {op: float(np.mean([r["ops"][op] for r in rows])) for op in task.OPS}
        spread = np.std([r["unseen"] for r in rows]) * 100
        print(f"{name:>18} {mean['unseen']:>6.0%}±{spread:>2.0f} {ops['+']:>5.0%} {ops['-']:>5.0%} "
              f"{ops['*']:>5.0%} {mean['tries']:>6.1f} {mean['connected']:>10,.0f} {mean['weights']:>9,.0f}")


if __name__ == "__main__":
    main()