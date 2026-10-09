"""The monitor region: notices when the brain is unsure or wrong, before the
teacher has to (like the anterior cingulate cortex, with the parietal number
sense).

Number sense
  People estimate before they calculate: 7*8 is "about 50", so 15 must be
  wrong. Here every number is perceived fuzzily, within ±20% (Weber's law:
  the bigger the number, the fuzzier), and the fuzz is carried through the
  calculation. The real answer is always inside the range, so an answer
  outside it is certainly wrong, while answers near the truth (54 for 7*8)
  can't be told apart. It catches big mistakes, not small ones.

Confidence
  How sure the brain is of an answer: facts from memory and rules count as
  sure, a section's guess counts as its own confidence, and the answer is only
  as sure as its weakest step.

Checking by undoing
  An exact check: 2+6 = 8 is checked with 8-6 = 2, 9-4 = 5 with 5+4 = 9,
  56/8 = 7 with 7*8 = 56, and 7*8 = 56 by taking 8 away seven times and
  landing on 0 (division as repeated subtraction). So the subtraction section
  checks the addition section's work and the other way round. The check only
  uses facts the brain KNOWS, never the fact being checked or its flipped
  twin; if it would need anything else, it says it can't check.

Doubts
  Things the brain knows that disagree with each other: a memory that breaks
  a rule, that number sense says can't be right, or that fails its undo check.
"""
from fractions import Fraction

from . import compose, rules

WEBER = Fraction(1, 5)        # numbers are perceived within ±20%


def _leaf(n):
    n = Fraction(n)
    lo, hi = n * (1 - WEBER), n * (1 + WEBER)
    return (min(lo, hi), max(lo, hi))


def estimate(tree):
    """-> (low, high): where the answer must lie, or None if it can't tell (dividing by about 0)."""
    if isinstance(tree, Fraction):
        return _leaf(tree)
    if tree[0] == "neg":
        r = estimate(tree[1])
        return None if r is None else (-r[1], -r[0])
    a, b = estimate(tree[1]), estimate(tree[2])
    if a is None or b is None:
        return None
    op = tree[0]
    if op in compose.REMAINDER_OPS or op == "%":
        if op in ("rem", "%"):
            return (Fraction(0), max(b[1], Fraction(0)))        # what is left is less than the divisor
        if b[0] <= 0 <= b[1]:
            return None
        lo, hi = a[0] / b[1], a[1] / b[0]
        return (lo - 1, hi + 1)                                 # whole groups: about a / b
    if op == "^":
        return None                                             # a power grows too fast to sense a size for
    if op == "+":
        return (a[0] + b[0], a[1] + b[1])
    if op == "-":
        return (a[0] - b[1], a[1] - b[0])
    if op == "/":
        if b[0] <= 0 <= b[1]:
            return None
        b = (1 / b[1], 1 / b[0])
    products = [x * y for x in a for y in b]
    return (min(products), max(products))


def sense(problem, answer):
    """Does the answer make sense to number sense? -> {"ok", "low", "high"} or None."""
    try:
        r = estimate(compose.parse(problem))
        value = compose.to_value(answer)
    except ValueError:
        return None
    if r is None:
        return None
    return {"ok": r[0] <= value <= r[1], "low": compose.fmt(_round(r[0])), "high": compose.fmt(_round(r[1]))}


def _round(x):
    """Estimates are rough, so show them roughly."""
    x = Fraction(x)
    return Fraction(round(x)) if abs(x) >= 1 else Fraction(round(x * 10), 10)


def _undo(problem, answer):
    """The check that undoes an operation: 2+6 = 8 -> 8-6 should be 2.
    -> (check expression, what it should give) or None."""
    try:
        tree = compose.parse(problem)
        value = compose.to_value(answer)
    except ValueError:
        return None
    if tree[0] not in "+-*/" or not (isinstance(tree[1], Fraction) and isinstance(tree[2], Fraction)):
        return None
    op, a, b = tree
    f = compose.fmt
    neg = lambda x: f"({f(x)})" if x < 0 else f(x)
    if op == "+":
        return f"{neg(value)}-{neg(b)}", a
    if op == "-":
        return f"{neg(value)}+{neg(b)}", a
    if op == "/":
        return f"{neg(value)}*{neg(b)}", a
    # multiplication: take the bigger number away, the smaller number of times, and land on 0
    if a.denominator != 1 or b.denominator != 1 or a < 0 or b < 0 or value < 0 or value.denominator != 1:
        return None
    times, size = (a, b) if a <= b else (b, a)
    if times == 0:
        return None                       # "0 times" can't be undone by taking away
    if times > 30:
        return None                       # too long to check by hand
    return f(value) + f"-{f(size)}" * int(times), Fraction(0)


def verify(brain, problem, answer):
    """Check an answer by undoing it, using only what the brain KNOWS, and
    never the fact being checked (nor its flipped twin, 8*7 for 7*8).
    -> {"ok": True/False, "check": "8-6 = 2"} or None if it can't check."""
    undo = _undo(problem, answer)
    if undo is None:
        return None
    check, expected = undo
    skip = {problem}
    tree = compose.parse(problem)
    if tree[0] in "+*":
        skip.add(f"{compose.fmt(tree[2])}{tree[0]}{compose.fmt(tree[1])}")

    def recall(p):
        return None if p in skip else brain.recall(p)

    def unknown(p):                       # never guess while checking
        return 0, {"source": "module"}

    worker = compose.Worker(unknown, rules.active(brain), recall=recall)
    try:
        got = worker.run(check)
    except ValueError:
        return None
    if any(s["source"] == "module" for s in worker.steps.values()) or any(k in skip for k in worker.steps):
        return None                       # it would need a fact it doesn't know: can't check
    shown = check if len(check) <= 24 else f"{check[:20]}…"
    return {"ok": got == expected, "check": f"{shown} = {compose.fmt(got)}", "expected": compose.fmt(expected)}


def confidence(steps, guess_confidence=None):
    """The answer is only as sure as its least sure step."""
    sure = [1.0 if s["source"] != "module" else float(s.get("confidence", 0.0)) for s in steps]
    if guess_confidence is not None:
        sure.append(float(guess_confidence))
    return min(sure) if sure else 1.0


def doubts(brain):
    """Contradictions inside what the brain knows (no math checker involved)."""
    found = []
    facts = rules.known_facts(brain)
    for name, r in brain.rules.items():
        if r.get("rejected"):
            continue
        _, breaks = rules.evidence(facts, r["lhs"], r["rhs"])
        for problem in breaks[:3]:
            found.append({"kind": "rule vs memory", "problem": problem, "answer": compose.fmt(brain.memory[problem]["answer"]),
                          "rule": name, "text": f"I remember {problem} = {compose.fmt(brain.memory[problem]['answer'])}, but the rule {name} says otherwise"})
    for problem, fact in brain.memory.items():
        s = sense(problem, fact["answer"])
        if s and not s["ok"]:
            found.append({"kind": "number sense", "problem": problem, "answer": compose.fmt(fact["answer"]),
                          "text": f"I remember {problem} = {compose.fmt(fact['answer'])}, but my number sense says it should be between {s['low']} and {s['high']}"})
            continue
        v = verify(brain, problem, fact["answer"])
        if v and not v["ok"]:
            found.append({"kind": "undo check", "problem": problem, "answer": compose.fmt(fact["answer"]),
                          "text": f"I remember {problem} = {compose.fmt(fact['answer'])}, but undoing it gives {v['check']} instead of {v['expected']}"})
    return found
