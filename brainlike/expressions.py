"""Small expressions over a story's slots: build, evaluate, show the working, and which atoms
an explanation uses.

Extracted from storyreader.py (size plan step 2, 2026-10-09); storyreader re-exports every name
here so old imports keep working. Depends only on model (Lin, fmt) and coordination (the tool
step finders).
"""
import re
from collections import defaultdict
from fractions import Fraction

from .coordination import dec, gcd_steps, group_steps, lcm_steps, percent_steps, unitary_steps
from .model import Lin, fmt


# ---- explanations: small expressions over the slots ----------------------------------------------------

_TERM = r"([A-Z][A-Za-z0-9.@:]*)(?:([*/])2)?"
_EXPR = re.compile(rf"^{_TERM}(?:([-+*/~%&^#$!\\|]){_TERM})?$")
# division with a remainder (P3): a%b what is left over, a&b how many full groups, a^b how many groups are needed
_WHOLE = "%&^\\|"
# P5-P6 rules: a!b a percent of b ('@' is taken: it marks days and colours), a#b the greatest common factor, a$b the least common multiple; 'q' (a square:
# side x side) lets a number be multiplied by itself; \ floor division, | ceiling division
_RULED = "%&^#$!\\|"
# S1: the unitary method, 'u': (a/b)*c, the value of ONE (a / b), then of c of them; three numbers at once
_UNITARY = re.compile(r"^\(([A-Z][A-Za-z0-9.@:]*)/([A-Z][A-Za-z0-9.@:]*)\)\*([A-Z][A-Za-z0-9.@:]*)$")
# Multi-op (CF 2026-10-12, _TWO_STEP): a chained two-step '(a*b)-c' -- one plain pair worked out,
# then one more plain step with a third atom ('(l*w)*h' a volume, '(each*want)-give' three steps).
# Inner and outer ops stay plain (+, -, *): no division (that is the unitary tool's, gated by 'u'),
# no ruled ops (tools stay single). Generation is flag-gated; parsing is unconditional, like _UNITARY.
_TWO_STEP = True
_CHAINED = re.compile(r"^\(([A-Z][A-Za-z0-9.@:]*)([-+*])([A-Z][A-Za-z0-9.@:]*)\)([-+*])([A-Z][A-Za-z0-9.@:]*)$")


def expressions(atoms, ops=""):
    """All small explanations: value -> [expression]. Atoms must be known numbers (learning). ops: the
    whole-group rules it was taught (%, &, ^); it can't explain anything with a rule it doesn't know."""
    base = [(a, v.c) for a, v in atoms.items() if isinstance(a, str)]
    terms = list(base) + [(f"{a}*2", v * 2) for a, v in base if not a.startswith(("N", "K"))] + \
        [(f"{a}/2", v / 2) for a, v in base if not a.startswith(("N", "K"))]
    out = defaultdict(list)
    for a, v in terms:
        out[v].append(a)
    root = lambda t: re.split(r"[*/]2$", t)[0]
    if "u" in ops:                                                    # first one (a / b), then c of them
        for a, va in base:
            for b, vb in base:
                if a == b or not vb or va == vb:
                    continue
                one = va / vb
                for c, vc in base:
                    if c in (a, b) or vc == vb or vc == 1:
                        continue
                    out[one * vc].append(f"({a}/{b})*{c}")
    if "q" in ops:                                                    # the square rule: side x side
        for a, va in base:
            if 1 < va <= 1000:
                out[va * va].append(f"{a}*{a}")
    if _TWO_STEP and len(base) <= 12:
        # chained two-steps over plain base atoms only: one pair worked out, then one more
        # plain step ('(l*w)*h', '(each*want)-give'). No division (the unitary tool's) and no
        # ruled ops inside: plain arithmetic needs no tool permission, so generation needs no
        # ops gate beyond the flag. The third atom is never one of the inner two ('(a+b)-b'
        # is just 'a' -- the plain form already says that).
        inners = []
        for i, (a, va) in enumerate(base):
            for j, (b, vb) in enumerate(base):
                if i == j:
                    continue
                if i < j:
                    inners.append((va + vb, a, "+", b))
                    inners.append((va * vb, a, "*", b))
                inners.append((va - vb, a, "-", b))
        for v, a, o, b in inners:
            for c, vc in base:
                if c == a or c == b:
                    continue
                out[v + vc].append(f"({a}{o}{b})+{c}")
                out[v * vc].append(f"({a}{o}{b})*{c}")
                out[v - vc].append(f"({a}{o}{b})-{c}")
    for i, (a, va) in enumerate(terms):
        for j, (b, vb) in enumerate(terms):
            if i == j or root(a) == root(b):
                continue
            plain = a == root(a) and b == root(b)
            if i < j:
                out[va + vb].append(f"{a}+{b}")
                if plain:
                    out[va * vb].append(f"{a}*{b}")
                    out[abs(va - vb)].append(f"{a}~{b}")
            out[va - vb].append(f"{a}-{b}")
            if plain and vb:
                out[va / vb].append(f"{a}/{b}")
            if "!" in ops and plain and 0 < va <= 100 and a[0] in "NQ":       # va percent of vb (a number it is told)
                out[va * vb / 100].append(f"{a}!{b}")
            if plain and i < j and va > 0 and vb > 0 and va.denominator == 1 and vb.denominator == 1 and \
                    ("#" in ops or "$" in ops):
                from math import gcd
                g = gcd(int(va), int(vb))
                if "#" in ops:
                    out[Fraction(g)].append(f"{a}#{b}")
                if "$" in ops:
                    out[Fraction(int(va) * int(vb) // g)].append(f"{a}${b}")
            if ops and plain and vb > 0 and va > 0 and va.denominator == 1 and vb.denominator == 1 and va > vb:
                q, r = divmod(int(va), int(vb))
                if "&" in ops:
                    out[Fraction(q)].append(f"{a}&{b}")
                if "^" in ops:
                    out[Fraction(q + (r > 0))].append(f"{a}^{b}")
                if r and "%" in ops:
                    out[Fraction(r)].append(f"{a}%{b}")
                if "\\" in ops:
                    out[Fraction(q)].append(f"{a}\\{b}")
                if "|" in ops:
                    out[Fraction(q + (r > 0))].append(f"{a}|{b}")
    return out


def show_work(expr, atoms):
    """The working for a whole-groups step, and its check by undoing it ('3\u00d75 + 2 = 17 \u2713')."""
    ch = _CHAINED.match(expr)
    if ch:
        # a chained two-step: work out the plain pair first, then the plain outer step.
        ia, iop, ib, oop, oc = ch.groups()
        if iop not in "+-*" or oop not in "+-*" or ia not in atoms or ib not in atoms or oc not in atoms:
            return None
        a, b, c = atoms[ia], atoms[ib], atoms[oc]
        inner_v = { "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a.times(b)}[iop]()
        if inner_v is None:
            return None
        inner_work = { "+": lambda: f"{a.c} + {b.c} = {inner_v.c}",
                       "-": lambda: f"{a.c} \u2212 {b.c} = {inner_v.c}",
                       "*": lambda: f"{a.c} \u00d7 {b.c} = {inner_v.c}" }[iop]()
        outer_v = { "+": lambda: inner_v + c, "-": lambda: inner_v - c, "*": lambda: inner_v.times(c)}[oop]()
        if outer_v is None:
            return None
        outer_work = { "+": lambda: f"{fmt(inner_v.c)} + {fmt(c.c)} = {fmt(outer_v.c)}",
                       "-": lambda: f"{fmt(inner_v.c)} \u2212 {fmt(c.c)} = {fmt(outer_v.c)}",
                       "*": lambda: f"{fmt(inner_v.c)} \u00d7 {fmt(c.c)} = {fmt(outer_v.c)}" }[oop]()
        check = { "+": lambda: f"check {fmt(outer_v.c)} \u2212 {fmt(c.c)} = {fmt(outer_v.c - c.c)} \u2713",
                  "-": lambda: f"check {fmt(outer_v.c)} + {fmt(c.c)} = {fmt(outer_v.c + c.c)} \u2713",
                  "*": lambda: f"check {fmt(outer_v.c)} \u00f7 {fmt(c.c)} = {fmt(outer_v.c / c.c)} \u2713" }[oop]()
        return f"{inner_work}; {outer_work}; {check}"
    u = _UNITARY.match(expr)
    if u:
        a, b, c = (atoms.get(x) for x in u.groups())
        if a is None or b is None or c is None or not (a.known and b.known and c.known) or not b.c:
            return None
        v, work = unitary_steps(a.c, b.c, c.c)
        return f"{work}; check {dec(v)} \u00f7 {dec(c.c)} \u00d7 {dec(b.c)} = {dec(v / c.c * b.c)} \u2713"
    m = _EXPR.match(expr)
    if not m or not m[3] or m[1] not in atoms or m[4] not in atoms:
        return None
    a, b = atoms[m[1]], atoms[m[4]]
    if not (a.known and b.known):
        return None
    if m[3] == "*" and m[1] == m[4]:
        return f"a square: side \u00d7 side = {fmt(a.c)} \u00d7 {fmt(a.c)} = {fmt(a.c * a.c)}"
    if m[3] == "!":
        return percent_steps(a.c, b.c)[1]
    if m[3] == "f":                                      # floor division
        if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        q = a.c // b.c
        return f"{a.c} // {b.c} = {q} (floor)"
    if m[3] == "h":                                      # ceiling division
        if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        q = -(-a.c // b.c)
        return f"{a.c} // {b.c} = {q} (ceiling)"
    if m[3] in "#$" and a.c > 0 and b.c > 0 and a.c.denominator == 1 and b.c.denominator == 1:
        v, work = (gcd_steps if m[3] == "#" else lcm_steps)(a.c, b.c)
        check = (f"check: {int(a.c)} \u00f7 {v} and {int(b.c)} \u00f7 {v} have no remainder \u2713" if m[3] == "#" else
                 f"check: {v} \u00f7 {int(a.c)} = {v // int(a.c)}, {v} \u00f7 {int(b.c)} = {v // int(b.c)} \u2713")
        return f"{work}; {check}"
    if m[3] not in _WHOLE:
        return None
    if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
        return None
    q, r, work = group_steps(a.c, b.c)
    need = f"; {q} + 1 = {q + 1} needed" if m[3] == "^" and r else ""
    ok = "\u2713" if q * int(b.c) + r == a.c else "\u2717"
    return f"{work}{need}; check {q}\u00d7{int(b.c)} + {r} = {q * int(b.c) + r} {ok}"


def evaluate(expr, atoms):
    ch = _CHAINED.match(expr)
    if ch:
        # a chained two-step: work out the plain pair first, then the plain outer step.
        # Only what generation emits (+, -, * both layers); anything else is not ours.
        ia, iop, ib, oop, oc = ch.groups()
        if iop not in "+-*" or oop not in "+-*" or ia not in atoms or ib not in atoms or oc not in atoms:
            return None
        a, b, c = atoms[ia], atoms[ib], atoms[oc]
        inner = { "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a.times(b)}[iop]()
        if inner is None:
            return None
        return {"+": lambda: inner + c, "-": lambda: inner - c, "*": lambda: inner.times(c)}[oop]()
    u = _UNITARY.match(expr)
    if u:                                                  # the unitary method: one, then many
        a, b, c = (atoms.get(x) for x in u.groups())
        if a is None or b is None or c is None or not b.known or b.c == 0:
            return None
        one = a.scale(1 / b.c)
        return one.times(c)
    m = _EXPR.match(expr)
    if not m:
        return None

    def term(name, op):
        if name not in atoms:
            return None
        v = atoms[name]
        return v if not op else (v.scale(2) if op == "*" else v.scale(Fraction(1, 2)))
    a = term(m[1], m[2])
    if a is None or not m[3]:
        return a
    b = term(m[4], m[5])
    if b is None:
        return None
    if m[3] == "~":                                        # the difference: bigger minus smaller
        if not (a.known and b.known):
            return None
        return Lin(abs(a.c - b.c))
    if m[3] == "!":                                        # a percent of b
        if not a.known:
            return None
        return b.scale(a.c / 100)
    if m[3] in "#$":                                       # greatest common factor, least common multiple
        if not (a.known and b.known) or a.c <= 0 or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        from math import gcd
        g = gcd(int(a.c), int(b.c))
        return Lin(g if m[3] == "#" else int(a.c) * int(b.c) // g)
    if m[3] in _WHOLE:                                     # whole groups: only for whole numbers it knows
        if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        q, r = divmod(int(a.c), int(b.c))
        return Lin({"%": r, "&": q, "^": q + (r > 0), "f": q, "h": q + (r > 0)}[m[3]])
    return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a.times(b), "/": lambda: a.over(b)}[m[3]]()


def write(sit, clause, target, v):
    if target.startswith("F:"):
        sit.write_first(*clause.cell(target[2:]), v)
    else:
        sit.write(*clause.cell(target), v)


def change_cell(sit, key, topic=False):
    """The cell a change clause should really act on when its own frame target holds nothing yet:
    the KNOWN cell of the same noun (its own owner first, then the ownerless one, then a lone
    other), else -- when `topic` -- the story's current topic cell (elliptical clauses: '1 flies
    away' means 1 of what the story is about). -> the cell key, or None."""
    if key is None:
        return None
    known = [k for k, c in sit.cells.items() if k[1] == key[1] and c[1].bind(sit.bound).known]
    for want in (key[0], None):
        same = [k for k in known if k[0] == want]
        if len(same) == 1:
            return same[0]
        if len(same) > 1:
            return None                              # ambiguous: which of them changed?
    if len(known) == 1:
        return known[0]
    if topic and sit.thing and not known:
        by_topic = [k for k, c in sit.cells.items() if k[1] == sit.thing[0]
                    and c[1].bind(sit.bound).known]
        if len(by_topic) == 1:
            return by_topic[0]
    return None


_USES = {}                          # explanation -> the atoms it uses (memoized: see uses())

_TOOL_OPS = "%&^#$!\\|"                # the operators that are tools (unitary and square have their own forms)


def tool_ops(expr):
    """Which tools one explanation used: its operator character, or the two special forms —
    the unitary method '(a/b)*c' and the square 'a*a'. -> tuple of ops (empty if no tool)."""
    if _UNITARY.match(expr):
        return ("u",)
    if _CHAINED.match(expr):
        return ()                      # plain pairs and a plain outer step: no tools in either layer
    m = _EXPR.match(expr)
    if not m or not m[3]:
        return ()
    if m[3] == "*" and m[1] == m[4]:
        return ("q",)
    return (m[3],) if m[3] in _TOOL_OPS else ()


def uses(expr):
    """The atoms an explanation uses ('N1+N2' -> ['N1', 'N2']). Memoized: a lesson asks about the same
    few thousand explanations millions of times, and this was the single hottest call in the brain
    (30M calls / 61M regex matches in one P1 lesson). -> tuple (every caller only iterates, indexes
    or counts it)."""
    got = _USES.get(expr)
    if got is None:
        u = _UNITARY.match(expr)
        ch = _CHAINED.match(expr) if u is None else None
        if u:
            got = tuple(u.groups())
        elif ch is not None:
            got = (ch.group(1), ch.group(3), ch.group(5))
        else:
            m = _EXPR.match(expr)
            got = tuple(x for x in (m[1], m[4]) if x) if m else ()
        if len(_USES) < 100000:      # the pool of explanations is small and closed; a guard all the same
            _USES[expr] = got
    return got


