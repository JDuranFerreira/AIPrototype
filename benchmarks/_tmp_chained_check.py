"""Spec check for the chained two-step port (CF 2026-10-12): evaluate/uses/tool_ops/candidates/
generation gating/show_work/counts_thing against the campaign spec."""
import sys
from fractions import Fraction

sys.path.insert(0, ".")

from brainlike import expressions as twin          # noqa: E402  (the flag home / orphan twin)
from brainlike import storyreader as sr            # noqa: E402

fails = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        fails.append(name)


atoms = {"A": sr.Lin(6), "B": sr.Lin(4), "C": sr.Lin(3)}

# -- evaluate: inner/outer plain only; unknown atoms / non-plain ops are not ours -------------
v = sr.evaluate("(A*B)-C", atoms)
check("evaluate (A*B)-C = 21", v is not None and v.c == Fraction(21))
v = sr.evaluate("(A+B)*C", atoms)
check("evaluate (A+B)*C = 30", v is not None and v.c == Fraction(30))
v = sr.evaluate("(A-B)+C", atoms)
check("evaluate (A-B)+C = 5", v is not None and v.c == Fraction(5))
check("evaluate (A/B)-C -> None (division excluded)", sr.evaluate("(A/B)-C", atoms) is None)
u = sr.evaluate("(A/B)*C", atoms)                     # division form falls through to the UNITARY tool
check("evaluate (A/B)*C = 4.5 via unitary (u gate unbypassed)", u is not None and u.c == Fraction(9, 2))
check("evaluate (A*B)-D -> None (unknown atom)", sr.evaluate("(A*B)-D", atoms) is None)
check("evaluate (A*B)%C -> None (non-plain op)", sr.evaluate("(A*B)%C", atoms) is None)
check("evaluate (A*B)*C, missing atom -> None", sr.evaluate("(A*B)*C", {"A": sr.Lin(6)}) is None)

# -- uses / tool_ops ------------------------------------------------------------------------
check("uses (A*B)-C -> (A, B, C)", sr.uses("(A*B)-C") == ("A", "B", "C"))
check("uses memoises", sr.uses("(A*B)-C") == ("A", "B", "C"))
check("tool_ops chained -> ()", sr.tool_ops("(A*B)*C") == ())
check("tool_ops unitary -> ('u',)", sr.tool_ops("(A/B)*C") == ("u",))
check("tool_ops plain pair -> ()", sr.tool_ops("A+B") == ())
check("tool_ops ruled -> ('%',)", sr.tool_ops("A%B") == ("%",))

# -- show_work / counts_thing: None / lenient on chained (campaign Landing 1) ----------------
check("show_work chained -> None", sr.show_work("(A*B)-C", atoms) is None)
check("counts_thing chained -> True (lenient)", sr.counts_thing(None, "(A*B)-C", "pen") is True)

# -- candidates gate exemption: the source line must exempt _CHAINED from the u-only rule -----
src = open("brainlike/storyreader.py", encoding="utf-8").read()
check("candidates gate exempts _CHAINED",
      'if expr.startswith("(") and "u" not in allowed and not _CHAINED.match(expr):' in src)
check("_CHAINED matches the chained form", bool(sr._CHAINED.match("(A*B)-C")))
check("_CHAINED rejects division inner", not sr._CHAINED.match("(A/B)*C"))


def all_exprs(d):
    return [e for es in d.values() for e in es]


# -- generation gating -----------------------------------------------------------------------
out = sr.expressions(atoms, "")                      # flag off (expressions._TWO_STEP is False)
check("flag off: zero paren forms", not any(e.startswith("(") for e in all_exprs(out)))
check("two_step=False: zero paren forms", not any(e.startswith("(") for e in all_exprs(sr.expressions(atoms, "", two_step=False))))

on = all_exprs(sr.expressions(atoms, "", two_step=True))
paren = [e for e in on if e.startswith("(")]
check("two_step=True (3 atoms): chained generated", len(paren) > 0)
check("every generated form parses as _CHAINED", all(sr._CHAINED.match(e) for e in paren))
check("(A*B)-C generated for value 21", any(e == "(A*B)-C" for e in sr.expressions(atoms, "", two_step=True).get(Fraction(21), [])))

n12 = {f"P{i}": sr.Lin(i + 2) for i in range(12)}
n13 = {f"P{i}": sr.Lin(i + 2) for i in range(13)}
check("12 base atoms: cap admits", any(e.startswith("(") for e in all_exprs(sr.expressions(n12, "", two_step=True))))
check("13 base atoms: cap blocks", not any(e.startswith("(") for e in all_exprs(sr.expressions(n13, "", two_step=True))))

twin._TWO_STEP = True                                # default two_step=None must follow the flag
try:
    check("default follows _TWO_STEP=True", any(e.startswith("(") for e in all_exprs(sr.expressions(atoms, ""))))
finally:
    twin._TWO_STEP = False
check("default follows _TWO_STEP=False", not any(e.startswith("(") for e in all_exprs(sr.expressions(atoms, ""))))

# -- byte parity of the _CHAINED definition --------------------------------------------------
t_line = [l for l in open("brainlike/expressions.py", encoding="utf-8").read().splitlines() if l.startswith("_CHAINED =")][0]
l_line = [l for l in src.splitlines() if l.startswith("_CHAINED =")][0]
check("_CHAINED byte-identical to twin", t_line == l_line)

print()
print("FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
