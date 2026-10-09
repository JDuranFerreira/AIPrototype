"""What are the rival readings of the doubt-blocked g1-test rows? Read-only.

  python benchmarks/_tmp_rivals.py [FLAG]

Passes a spy list as `rivals` into Frames.answer: when the answer code appends a rival value,
the spy reads the answer frame's locals (the rival candidate x and the top reading `best`) and
records both readings' sureness, key and expression. For every doubt-blocked row it prints
whether the doubt is a rival doubt, and if so whether the CORRECT reading carries the higher
sureness (a sureness tie-break would release it) or not (it would not).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                    # noqa: E402
from brainlike.regions import Mind                               # noqa: E402
from brainlike.storyreader import Frames                         # noqa: E402

FLAG = next((a for a in sys.argv[1:] if a.startswith("_")), None)
if FLAG:
    import brainlike.storyreader as sr
    setattr(sr, FLAG, True)
    print(f"[{FLAG} switched on for this run]")


class Spy(list):
    """Records the competing readings the answer loop compares, via its frame locals."""

    def __init__(self):
        super().__init__()
        self.meta = None

    def append(self, v):
        f = sys._getframe(1)                       # the answer() frame
        x, best, val = f.f_locals.get("x"), f.f_locals.get("best"), f.f_locals.get("v")
        if x is not None and best is not None:
            self.meta = {"top_val": best[0], "top_c": best[2], "top_key": best[1].get("key"),
                         "top_expr": best[1].get("expr"), "riv_val": val.c if val else v,
                         "riv_c": x.get("c"), "riv_key": x.get("key"), "riv_expr": x.get("expr")}
        super().append(v)


_orig = Frames.answer


def answer(self, clause, sit, rivals=None, atoms_out=None):
    spy = rivals if isinstance(rivals, Spy) else Spy()
    out = _orig(self, clause, sit, spy, atoms_out)
    if isinstance(rivals, list) and rivals is not spy:
        rivals.extend(spy)
    BOX["spy"] = spy.meta if isinstance(rivals, Spy) or True else None
    BOX["spy"] = spy.meta
    BOX["top"] = out[1]
    return out


BOX = {}
Frames.answer = answer

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
exam = primary.outside_exam(mind.language.reading, 1, "test")
rows = [r for r in exam["rows"] if r["how"].startswith("not sure")]
print(f"{len(rows)} doubt-blocked rows:\n")
for r in rows:
    BOX.clear()
    got, how, trace = mind.language.reading.reader().solve(r["text"])
    doubts = next((t.get("doubts", []) for t in reversed(trace) if t.get("question")), [])
    has_rival = any(d.startswith("two ways") for d in doubts)
    tag = "RIGHT" if r["right"] else "wrong"
    print(f"  {tag} want {r['answer']:>4} got {str(r['got']):>4} :: {r['text'][:62]}")
    print(f"           rival doubt: {has_rival}")
    m = BOX.get("spy")
    if has_rival and m:
        top, riv = m, m
        print(f"           top: {m['top_key']} {m['top_expr']} = {m['top_val']} (c={m['top_c']})")
        print(f"           riv: {m['riv_key']} {m['riv_expr']} = {m['riv_val']} (c={m['riv_c']})")
        winner = "TOP" if str(m["top_val"]) == str(r["answer"]) else \
                 "RIVAL" if str(m["riv_val"]) == str(r["answer"]) else "neither"
        sure = "top surer" if (m["top_c"] or 0) > (m["riv_c"] or 0) else \
               "rival surer" if (m["riv_c"] or 0) > (m["top_c"] or 0) else "tied"
        print(f"           correct reading: {winner}; sureness: {sure}")
