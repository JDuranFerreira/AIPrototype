"""Measure the reasoner's trainer, and check the vectorized one against the original loop.

  python benchmarks/bench_reasoner.py profile [N]     cProfile one epoch over the first N GSM8K worked
                                                      solutions (default 100)
  python benchmarks/bench_reasoner.py parity          original loop vs vectorized: same mistakes, same
                                                      weights, same plans
  python benchmarks/bench_reasoner.py train [ARGS]    run train_reasoner.py with ARGS; always passes
                                                      --no-save (run train_reasoner.py directly to save)

parity trains both versions on a fixed mixed subset (200 SVAMP + 100 ASDiv + 200 GSM8K + the school's
bar models) for 2 epochs with the same seed, and compares the per-epoch mistake counts, the averaged
weights exactly, and read() on 150 problems neither has seen.
"""
import cProfile
import json
import pstats
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.reasoner import Reasoner, _h                               # noqa: E402
from run_reader import load_svamp                                         # noqa: E402
from train_reasoner import worked_examples                                # noqa: E402


def reference_train(r, examples, epochs=2, seed=0, log=None):
    """The original reasoner.train() loop: one _h hash per feature string, one NumPy gather
    per candidate, W summed into `total` after every step.  Kept here as the yardstick to match.
    Gold canonicalisation (r._gold) and candidate rules are shared with Reasoner, so this stays a
    pure test of the *loop*, not of the problem representation."""
    total = np.zeros_like(r.W)
    count = 0
    rng = np.random.default_rng(seed)
    order = np.arange(len(examples))
    for epoch in range(epochs):
        rng.shuffle(order)
        mistakes = 0
        for n in order:
            text, steps = examples[n]
            story, consts, qfeats = r._setup(text)
            pool = story + consts
            used = set()
            for s in range(len(steps) + 1):
                if s < len(steps):
                    op, ra, rb = steps[s]
                    gold = r._gold(pool, op, ra, rb, len(story))
                else:
                    gold = "STOP"
                cands = r._cands(pool, used, qfeats, s)
                gold_feats = next((f for c, f in cands if c == gold), None)
                if gold_feats is None:
                    break                          # the worked solution does something the reasoner can't
                best, best_feats, best_score = None, None, -1e30
                for c, f in cands:
                    sc = r._score(f)
                    if sc > best_score:
                        best, best_feats, best_score = c, f, sc
                if best != gold:
                    mistakes += 1
                    np.add.at(r.W, [_h(f) for f in gold_feats], 1.0)
                    np.add.at(r.W, [_h(f) for f in best_feats], -1.0)
                if gold == "STOP":
                    break
                op, i, j = gold
                used.update((i, j))
                pool = pool + [r._apply(pool, op, i, j, s)]
                total += r.W
                count += 1
        if log:
            log(f"  epoch {epoch + 1}: {mistakes} wrong steps")
    r.W = (total / max(count, 1)).astype(np.float32)
    return r


def profile(n):
    examples, seen = worked_examples()
    off = seen["svamp-train"][0] + seen["asdiv"][0]
    gsm = examples[off:off + n]
    print(f"{len(gsm)} GSM8K worked solutions, 1 epoch")
    r = Reasoner()
    prof = cProfile.Profile()
    t0 = time.time()
    prof.enable()
    r.train(gsm, epochs=1)
    prof.disable()
    print(f"one epoch over {len(gsm)}: {time.time() - t0:.1f}s")
    pstats.Stats(prof).strip_dirs().sort_stats("cumulative").print_stats(25)
    return 0


def parity():
    examples, seen = worked_examples()
    a = seen["svamp-train"][0]
    b = a + seen["asdiv"][0]
    c = b + seen["gsm8k"][0]
    subset = examples[:200] + examples[a:a + 100] + examples[b:b + 200] + examples[c:]
    print(f"subset: {len(subset)} worked solutions, 2 epochs, seed 0")
    ref_log, fast_log = [], []
    t0 = time.time()
    ref = reference_train(Reasoner(), subset, epochs=2, seed=0, log=ref_log.append)
    t1 = time.time()
    fast = Reasoner().train(subset, epochs=2, seed=0, log=fast_log.append)
    t2 = time.time()
    print(f"original loop {t1 - t0:.1f}s   vectorized {t2 - t1:.1f}s   ({(t1 - t0) / max(t2 - t1, 1e-9):.1f}x)")
    for name, log in (("original  ", ref_log), ("vectorized", fast_log)):
        print(f"  {name}: " + "   ".join(s.strip() for s in log))
    ok = ref_log == fast_log
    print(f"mistake counts identical: {ok}")
    same_w = bool(np.array_equal(ref.W, fast.W))
    print(f"averaged weights bitwise identical: {same_w}"
          f"   (max |diff| = {float(np.abs(ref.W - fast.W).max()):g})")
    print(f"non-zero weights: {ref.n_weights:,} vs {fast.n_weights:,}")
    ok = ok and same_w and ref.n_weights == fast.n_weights

    # the low-RAM trainer (cache=False, rebuilds gold paths each epoch) must give the same weights
    fast2 = Reasoner().train(subset, epochs=2, seed=0, cache=False)
    same_nocache = bool(np.array_equal(ref.W, fast2.W))
    print(f"no-cache trainer bitwise identical too: {same_nocache}")
    ok = ok and same_nocache

    # the plans the arithmetic region would run, on problems neither model was trained on
    problems = [r["text"] for r in load_svamp("svamp_dev.csv")][:100]
    gsm = [json.loads(line) for line in open(HERE / "gsm8k_test.jsonl", encoding="utf-8")]
    random.Random(0).shuffle(gsm)
    problems += [g["question"] for g in gsm[:50]]
    t0 = time.time()
    agree = sum(ref.read(text) == fast.read(text) for text in problems)
    print(f"read() plans identical on {agree}/{len(problems)} unseen problems"
          f"   ({(time.time() - t0) * 1000 / len(problems):.1f} ms per problem, vectorized scorer)")
    ok = ok and agree == len(problems)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "profile":
        return profile(int(argv[2]) if len(argv) > 2 else 100)
    if mode == "parity":
        return parity()
    if mode == "train":
        args = argv[2:]
        if "--no-save" not in args:
            args.append("--no-save")             # this tool never writes brain_state; run train_reasoner.py to save
        sys.argv = [argv[0]] + args
        from train_reasoner import main as train_main
        train_main()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

