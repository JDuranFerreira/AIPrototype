"""Where the reasoner fails, and what it costs in memory.

  python benchmarks/analyze_reasoner.py coverage   # can the candidate space express every worked
                                                   # solution? + RAM the training cache needs
  python benchmarks/analyze_reasoner.py steps      # teacher-forced step errors of the saved model:
                                                   # SVAMP (gold equations) and GSM8K test
  python benchmarks/analyze_reasoner.py outcome    # SVAMP outcome split: right / no plan / wrong
"""
import csv
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys as _sys
_sys.path.insert(0, str(HERE.parent))
_sys.path.insert(0, str(HERE))
from brainlike import compose                                             # noqa: E402
from brainlike.reasoner import Reasoner, steps_from_expression, steps_from_gsm8k  # noqa: E402
from brainlike.reader import fill, prefix_to_template                     # noqa: E402
from run_reader import load_svamp                                         # noqa: E402
from train_reasoner import worked_examples, plan_value                    # noqa: E402


def _rss_mb():
    """-> (working set MiB, peak working set MiB) of this process (Windows)."""
    import ctypes

    class PM(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    pm = PM()
    pm.cb = ctypes.sizeof(PM)
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pm), pm.cb)
    return pm.WorkingSetSize / 2 ** 20, pm.PeakWorkingSetSize / 2 ** 20


def coverage():
    """For every worked solution: is the gold step a candidate at each point, and if not, why not?"""
    r = Reasoner()
    examples, seen = worked_examples()
    marks, start = {}, 0
    for k, (a, _b) in seen.items():
        marks[start] = k
        start += a
    totals, cache_bytes = {}, 0
    t0 = time.time()
    for n, (text, steps) in enumerate(examples):
        src = max((b, v) for b, v in marks.items() if b <= n)[1]
        story, consts, qfeats = r._setup(text)
        pool, used, s_bytes = story + consts, set(), 0
        broken = None
        for s in range(len(steps) + 1):
            if s < len(steps):
                op, ra, rb = steps[s]
                gold = r._gold(pool, op, ra, rb, len(story))
            else:
                gold = "STOP"
            cands = r._cands(pool, used, qfeats, s)
            s_bytes += sum(len(f) for _c, f in cands) * 4 + (len(cands) + 1) * 4
            if any(c == gold for c, _f in cands):
                pass                                   # expressible; keep following the gold path
            else:
                if gold == "STOP":
                    broken = "stop-at-step-0" if s == 0 else "no-stop"
                else:
                    op, i, j = gold
                    a, b = pool[i], pool[j]
                    if i == j:
                        broken = "same-pair"
                    elif a.kind == "const" and b.kind == "const":
                        broken = "const-const"
                    elif op in "+*" and j < i and a.kind != "const" and b.kind != "const":
                        broken = "commutative-order"   # "2+12" written with the later number first
                    elif op == "-" and a.value - b.value < 0:
                        broken = "negative-result"
                    elif op == "/" and b.value == 0:
                        broken = "divide-by-zero"
                    else:
                        broken = "not-generated"
                break
            if gold == "STOP":
                break
            op, i, j = gold
            used.update((i, j))
            pool = pool + [r._apply(pool, op, i, j, s)]
        key = (src, broken or "ok")
        totals[key] = totals.get(key, 0) + 1
        cache_bytes += s_bytes
    print(f"worked solutions: {len(examples)}   pass in {time.time() - t0:.0f}s")
    for src in seen:
        ok = totals.get((src, "ok"), 0)
        all_ = ok + sum(v for (s2, b), v in totals.items() if s2 == src and b != "ok")
        print(f"  {src:12s} complete path {ok}/{all_} = {ok / max(all_, 1):.1%}")
        for (s2, b), v in sorted(totals.items(), key=lambda kv: -kv[1]):
            if s2 == src and b != "ok":
                print(f"      blocked by {b:20s} {v}")
    ok_all = sum(v for (s, b), v in totals.items() if b == "ok")
    print(f"ALL: {ok_all}/{len(examples)} = {ok_all / len(examples):.1%} fully expressible")
    print(f"gold-path cache would need {cache_bytes / 2 ** 30:.2f} GiB ({cache_bytes / 2 ** 20:.0f} MiB)")
    ws, peak = _rss_mb()
    print(f"this process: {ws:.0f} MiB working set, peak {peak:.0f} MiB")
    return 0


def _teacher_forced(name, items, folder=None):
    """Follow each gold path; at every step ask the saved model whether it scores gold top-1."""
    r = Reasoner.load(folder or (HERE.parent / "brain_state" / "language"))
    if r is None:
        print("no saved reasoner (brain_state/language/reasoner.npz)")
        return 1
    n = plan_ok = uncovered = 0
    pos_hit, pos_tot, div = {}, {}, {}
    t0 = time.time()
    for text, steps in items:
        if not steps:
            continue
        n += 1
        story, consts, qfeats = r._setup(text)
        pool, used = story + consts, set()
        ok = True
        for s in range(len(steps) + 1):
            if s < len(steps):
                op, ra, rb = steps[s]
                gold = r._gold(pool, op, ra, rb, len(story))
            else:
                gold = "STOP"
            cands = r._cands(pool, used, qfeats, s)
            if not any(c == gold for c, _f in cands):
                uncovered += 1
                ok = False
                break
            best, best_sc = None, -1e30
            for c, f in cands:                       # same tie-break as read(): first max wins
                sc = r._score(f)
                if sc > best_sc:
                    best, best_sc = c, sc
            if s < len(steps):
                pos_tot[s] = pos_tot.get(s, 0) + 1
            if best == gold:
                if s < len(steps):
                    pos_hit[s] = pos_hit.get(s, 0) + 1
            else:
                ok = False
                if best == "STOP":
                    k = "stopped early"
                elif s == len(steps):
                    k = "missed STOP"
                elif best[0] != gold[0]:
                    k = "wrong op"
                else:
                    k = "wrong operands"
                div[k] = div.get(k, 0) + 1
                break
            if s < len(steps):
                used.update((gold[1], gold[2]))
                pool = pool + [r._apply(pool, *gold, s)]
        plan_ok += ok
    print(f"{name}: {n} problems teacher-forced in {time.time() - t0:.0f}s")
    print(f"  whole plan right (all steps + STOP): {plan_ok}/{n} = {plan_ok / max(n, 1):.1%}")
    print(f"  gold steps not in the candidate space: {uncovered}")
    for s in sorted(pos_tot):
        h = pos_hit.get(s, 0)
        print(f"  step {s}: top-1 {h}/{pos_tot[s]} = {h / pos_tot[s]:.0%}")
    print("  first divergence:", dict(sorted(div.items(), key=lambda kv: -kv[1])))
    return 0


def _svamp_items():
    """SVAMP dev with its gold Equation column -> (text, steps)."""
    out = []
    for row in csv.DictReader(open(HERE / "svamp_dev.csv", encoding="utf-8")):
        nums = [compose.fmt(Fraction(x)) for x in row["Numbers"].split()]
        text = row["Question"]
        for i, nv in enumerate(nums):
            text = text.replace(f"number{i}", nv)
        try:
            expr = fill(prefix_to_template(row["Equation"]), nums)
            out.append((text, steps_from_expression(text, expr) or []))
        except Exception:
            out.append((text, []))
    return out


def steps(folder=None):
    svamp = _svamp_items()
    ok_eq = sum(1 for _t, s in svamp if s)
    print(f"SVAMP: gold steps parsed for {ok_eq}/{len(svamp)} problems")
    _teacher_forced("SVAMP dev", svamp, folder)
    gsm = [json.loads(line) for line in open(HERE / "gsm8k_test.jsonl", encoding="utf-8")]
    _teacher_forced("GSM8K test", [(g["question"], steps_from_gsm8k(g["question"], g["answer"]) or [])
                                   for g in gsm], folder)
    return 0


def outcome(folder=None):
    r = Reasoner.load(folder or (HERE.parent / "brain_state" / "language"))
    if r is None:
        print("no saved reasoner")
        return 1
    items = [(x["text"], x["answer"]) for x in load_svamp("svamp_dev.csv")]
    right = none = wrong = 0
    for text, answer in items:
        plan = r.read(text)
        if plan is None:
            none += 1
            continue
        try:
            if plan_value(plan) == answer:
                right += 1
            else:
                wrong += 1
        except (ValueError, ZeroDivisionError, KeyError):
            wrong += 1
    n = len(items)
    print(f"SVAMP {n}: right {right} ({right / n:.1%}) | no plan {none} ({none / n:.1%})"
          f" | wrong plan {wrong} ({wrong / n:.1%})")
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    folder = argv[2] if len(argv) > 2 else None    # optional model folder for steps / outcome
    if mode == "coverage":
        return coverage()
    if mode == "steps":
        return steps(folder)
    if mode == "outcome":
        return outcome(folder)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
