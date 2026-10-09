"""Prototype: beam search in the reasoner's read(), greedy vs beam on saved models.

  python benchmarks/results/tmp_beam.py
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))
from brainlike.reasoner import Reasoner, MAX_STEPS    # noqa: E402
from brainlike import compose                         # noqa: E402
from train_reasoner import evaluate, load_svamp       # noqa: E402
import re                                             # noqa: E402


def beam_read(r, text, k=4, how="mean"):
    """Like Reasoner.read but keeps the k best partial plans by cumulative step score."""
    story, consts, qfeats = r._setup(text)
    if not story:
        return None
    whole = bool(re.search(r"\bhow many\b", text, re.I))
    # (scores, pool, used, shown)
    beams = [([0.0], story + consts, set(), [])]     # 0.0 so mean works before any step
    complete = []
    for s in range(MAX_STEPS + 1):
        nxt = []
        for scs, pool, used, shown in beams:
            cands = r._cands(pool, used, qfeats, s)
            scored = sorted(((r._score(f), c) for c, f in cands), key=lambda x: -x[0])
            for sc, choice in scored[:k]:            # only the top-k of each beam survive
                if choice == "STOP" or s == MAX_STEPS:
                    if shown:
                        total = scs + ([sc] if choice == "STOP" else [])
                        agg = sum(total) / len(total) if how == "mean" else sum(total)
                        complete.append((agg, shown, pool))
                else:
                    op, i, j = choice
                    used2 = used | {(i, j)}
                    nxt.append((scs + [sc], pool + [r._apply(pool, op, i, j, s)], used2,
                                shown + [(op, pool[i], pool[j])]))
        if not nxt:
            break
        nxt.sort(key=lambda b: -(sum(b[0]) / len(b[0])))
        beams = nxt[:k]
    if not complete:
        return None
    complete.sort(key=lambda x: -x[0])
    _agg, shown, pool = complete[0]
    answer = pool[-1].value
    if answer <= 0 or (whole and answer.denominator != 1):
        return None
    results = [q for q in pool if q.kind == "result"]
    lines, names = [], {}
    for n, (op, a, b) in enumerate(shown):
        ta = names.get(id(a), compose.fmt(a.value))
        tb = names.get(id(b), compose.fmt(b.value))
        expr = f"{ta}{op}{tb}"
        if n < len(shown) - 1:
            lines.append(f"r{n} = {expr}")
            names[id(results[n])] = f"r{n}"
        else:
            lines.append(expr)
    return "plan: " + "; ".join(lines)


def main():
    items = [(x["text"], x["answer"]) for x in load_svamp("svamp_dev.csv")]
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    how = sys.argv[3] if len(sys.argv) > 3 else "mean"
    models = [("old brain_state", None), ("new tmp_e1", "benchmarks/results/tmp_e1"),
              ("new tmp_e6", "benchmarks/results/tmp_e6"),
              ("new tmp_drv(e1 off)", "benchmarks/results/tmp_drv")]
    if which != "all":
        models = [(n, f) for n, f in models if which in n]
    for name, folder in models:
        r = Reasoner.load(folder) if folder else Reasoner.load(HERE.parent.parent / "brain_state" / "language")
        if r is None:
            print(f"{name}: no model")
            continue
        t0 = time.time()
        g_ok = evaluate(r, items)[0]
        t1 = time.time()
        b_ok = 0
        for text, answer in items:
            plan = beam_read(r, text, k=k, how=how)
            try:
                b_ok += plan is not None and __import__("train_reasoner").plan_value(plan) == answer
            except (ValueError, ZeroDivisionError, KeyError):
                pass
        t2 = time.time()
        print(f"{name}: greedy {g_ok/len(items):.1%} ({(t1-t0)*1000/len(items):.0f} ms) | "
              f"beam{k}-{how} {b_ok/len(items):.1%} ({(t2-t1)*1000/len(items):.0f} ms)", flush=True)


if __name__ == "__main__":
    main()
