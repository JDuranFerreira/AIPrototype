"""Port chained-form handlers from brainlike/expressions.py (orphan twin) into brainlike/storyreader.py.

Byte-exact copies: every block is sliced out of expressions.py by line number, never retyped.
Run from the repo root; aborts (AssertionError) if any anchor is missing or ambiguous.
"""

TWIN = "brainlike/expressions.py"
LIVE = "brainlike/storyreader.py"

twin = open(TWIN, encoding="utf-8", newline="").read().splitlines(keepends=True)


def block(i0, i1, startswith, endswith):
    """1-based inclusive slice of the twin, normalised to LF, with shape checks."""
    chunk = "".join(twin[i0 - 1:i1]).replace("\r\n", "\n")
    assert chunk.startswith(startswith), (i0, repr(chunk[:60]))
    assert chunk.rstrip("\n").endswith(endswith), (i1, repr(chunk[-60:]))
    return chunk


# ---- extract the four twin blocks --------------------------------------------------------
# A: generation block (twin 59-80), gated on the module flag + 12-atom cap
A = block(59, 80, "    if _TWO_STEP and len(base) <= 12:", 'out[v - vc].append(f"({a}{o}{b})-{c}")')
A = A.replace("if _TWO_STEP and len(base) <= 12:", "if two_step and len(base) <= 12:")
# B: evaluate chained branch (twin 173-184)
B = block(173, 184, "    ch = _CHAINED.match(expr)", "[oop]()")
assert "inner.times(c)" in B
# C: tool_ops chained early-out (twin 270-271)
C = block(270, 271, "    if _CHAINED.match(expr):", "no tools in either layer")
# D: uses chained branch (twin 288, 291-292)
D_ch = block(288, 288, "        ch = _CHAINED.match(expr) if u is None else None", "else None")
D_elif = block(291, 292, "        elif ch is not None:", "ch.group(5))")

live = open(LIVE, encoding="utf-8", newline="").read()
edits = []


def splice(old, new, why, count=1):
    global live
    n = live.count(old)
    assert n == count, f"{why}: anchor found {n}x (want {count}): {old[:70]!r}"
    live = live.replace(old, new, count)
    edits.append(why)


# ---- 0. delete the dead _DIM_DESC/_CUBE_WORDS block (never read anywhere; its insertion
#         split the _FLY_FIX comment, deletion restores it) ------------------------------
dead_start = "# Dimension adjectives (CF 2026-10-12, _DIM_DESC): 'long' / 'wide' / 'high' describe WHICH"
dead_end = '_CUBE_WORDS = {"cubic"}\n'
i = live.index(dead_start)
j = live.index(dead_end) + len(dead_end)
assert "only right before" in live[i - 80:i], "dim block not after the _FLY_FIX comment"
assert live[j:].lstrip().startswith("#     'away'/'off'"), "unexpected neighbourhood after the dead block"
live = live[:i] + live[j:]
assert "_DIM_DESC" not in live and "_DIM_WORDS" not in live and "_CUBE_WORDS" not in live
edits.append("delete dead _DIM_DESC/_DIM_WORDS/_CUBE_WORDS block")
old_block = """    if two_step:
        # chained two-steps over plain base atoms only
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
"""
splice(old_block, "", "remove old uncapped pre-terms two_step block")

q_tail = '                out[va * va].append(f"{a}*{a}")\n    for i, (a, va) in enumerate(terms):'
splice(q_tail,
       '                out[va * va].append(f"{a}*{a}")\n' + A + "    for i, (a, va) in enumerate(terms):",
       "insert twin generation block after the q block (12-atom cap, twin order)")

# ---- 2. evaluate(): chained branch first -----------------------------------------------
splice("def evaluate(expr, atoms):\n    u = _UNITARY.match(expr)",
       "def evaluate(expr, atoms):\n" + B + "    u = _UNITARY.match(expr)",
       "evaluate: chained branch")

# ---- 3. tool_ops(): chained early-out --------------------------------------------------
splice('    if _UNITARY.match(expr):\n        return ("u",)\n    m = _EXPR.match(expr)',
       '    if _UNITARY.match(expr):\n        return ("u",)\n' + C + "    m = _EXPR.match(expr)",
       "tool_ops: chained -> ()")

# ---- 4. uses(): chained branch ----------------------------------------------------------
splice("        u = _UNITARY.match(expr)\n        if u:\n            got = tuple(u.groups())\n        else:\n",
       "        u = _UNITARY.match(expr)\n" + D_ch + "        if u:\n            got = tuple(u.groups())\n"
       + D_elif + "        else:\n",
       "uses: chained -> (a, b, c)")

# ---- 5. candidates(): chained exempt from the unitary-only '(' gate ---------------------
splice('                if expr.startswith("(") and "u" not in allowed:',
       '                if expr.startswith("(") and "u" not in allowed and not _CHAINED.match(expr):',
       "candidates: chained gate exemption")

# ---- 1. expressions(): flag resolution + drop the old uncapped block --------------------
splice('def expressions(atoms, ops="", two_step=False):',
       'def expressions(atoms, ops="", two_step=None):', "signature two_step=False -> None")
splice('whole-group rules it was taught (%, &, ^); it can\'t explain anything with a rule it doesn\'t know."""\n'
       "    base = [(a, v.c) for a, v in atoms.items() if isinstance(a, str)]",
       'whole-group rules it was taught (%, &, ^); it can\'t explain anything with a rule it doesn\'t know."""\n'
       "    if two_step is None:                    # generation is flag-gated (CF 2026-10-12): the flag\n"
       "        from .expressions import _TWO_STEP  # lives in the twin module; late, reading never needs it\n"
       "        two_step = _TWO_STEP\n"
       "    base = [(a, v.c) for a, v in atoms.items() if isinstance(a, str)]",
       "gate: default two_step resolves from expressions._TWO_STEP")

open(LIVE, "w", encoding="utf-8", newline="").write(live)

# ---- final: _CHAINED still byte-identical to the twin -----------------------------------
t_line = [l for l in open(TWIN, encoding="utf-8").read().splitlines() if l.startswith("_CHAINED =")][0]
l_line = [l for l in live.splitlines() if l.startswith("_CHAINED =")][0]
assert t_line == l_line, "_CHAINED drifted"

print(f"OK ({len(edits)} edits)")
for e in edits:
    print(" -", e)
