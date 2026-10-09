"""Rules with letters, like n/n = 1, a*1 = a or a*0 = 0.

A rule is a shortcut: once the brain knows n/n = 1, it answers 453452/453452
in one step instead of doing long division. Rules come from two places:

  taught   the teacher types one ("n/n = 1")
  noticed  the brain looks at facts it already knows, guesses a general rule
           (induction: 300/300 = 1 and 453452/453452 = 1 -> maybe n/n = 1?)
           and asks the teacher before trusting it

Letters stand for any number; x still means times.
"""
import itertools
from fractions import Fraction

from . import compose

MIN_EXAMPLES = 2          # how many agreeing facts before it dares to suggest a rule
_SAMPLES = [Fraction(v) for v in ("0", "1", "2", "3", "7", "12", "1/2", "-4")]


def parse_rule(lhs, rhs):
    """-> (lhs tree, rhs tree, "n/n = 1"). Raises ValueError if it isn't a usable rule."""
    left = compose.parse(lhs, variables=True)
    right = compose.parse_side(rhs)
    names = compose.variables_in(left)
    if not names:
        raise ValueError("a rule needs a letter for 'any number', like n/n = 1")
    missing = compose.variables_in(right) - names
    if missing:
        raise ValueError(f"the right side uses {', '.join(sorted(missing))}, which the left side doesn't have")
    return left, right, f"{compose.to_text(left)} = {compose.to_text(right)}"


def is_rule(lhs):
    try:
        return bool(compose.variables_in(compose.parse(lhs, variables=True)))
    except ValueError:
        return False


def agrees_with_math(left, right):
    """Try the rule on a handful of numbers with exact arithmetic."""
    names = sorted(compose.variables_in(left))
    for values in itertools.product(_SAMPLES, repeat=len(names)):
        env = dict(zip(names, values))
        try:
            if compose.evaluate(left, env) != compose.evaluate(right, env):
                return False
        except ValueError:                        # e.g. 0/0: the rule just doesn't apply there
            continue
    return True


def active(brain):
    """Rules the brain trusts, ready for compose.Worker."""
    out = []
    for name, r in brain.rules.items():
        if not r.get("rejected"):
            left, right, _ = parse_rule(r["lhs"], r["rhs"])
            out.append((left, right, name))
    return out


def apply_to(brain, problem):
    """A single fact answered by a rule: -> (answer, rule name) or None."""
    tree = compose.parse(problem)
    for left, right, name in active(brain):
        bound = compose.match(left, tree)
        if bound is None:
            continue
        result = compose.substitute(right, bound)
        if isinstance(result, tuple) and result[0] == "neg" and isinstance(result[1], Fraction):
            result = -result[1]
        if isinstance(result, tuple):
            continue                  # needs arithmetic (a+b = b+a): the brain must do it, not the checker
        return result, name
    return None


def add(brain, lhs, rhs, examples=(), taught=True):
    left, right, name = parse_rule(lhs, rhs)
    brain.rules[name] = {"lhs": compose.to_text(left), "rhs": compose.to_text(right),
                         "taught": taught, "examples": list(examples)}
    return name, agrees_with_math(left, right)


def reject(brain, name):
    lhs, rhs = name.split(" = ", 1)
    brain.rules[name] = {"lhs": lhs, "rhs": rhs, "rejected": True}


# ---- noticing rules (induction) ---------------------------------------------
def _leaf(t):
    return isinstance(t, Fraction)


def candidates(problem, answer):
    """Rules this one fact could be an example of. 7*1 = 7 -> n*1 = n, ..."""
    try:
        tree = compose.parse(problem)
        value = compose.to_value(answer)
    except ValueError:
        return []
    if tree[0] == "neg" or not (_leaf(tree[1]) and _leaf(tree[2])):
        return []
    op, a, b = tree
    n, f = ("var", "n"), compose.fmt
    out = []
    if a == b:
        out.append(((op, n, n), value))                    # n/n = 1, n-n = 0
        if value == a * 2 and op == "+":
            out.append(((op, n, n), ("*", Fraction(2), n)))  # n+n = 2*n
    if value == a:
        out.append(((op, n, b), n))                        # n*1 = n, n+0 = n, n/1 = n
    if value == b:
        out.append(((op, a, n), n))                        # 1*n = n, 0+n = n
    out.append(((op, n, b), value))                        # n*0 = 0
    out.append(((op, a, n), value))                        # 0*n = 0, 0/n = 0
    x, y = ("var", "a"), ("var", "b")
    if op in "+*" and a != b:
        out.append(((op, x, y), (op, y, x)))               # order doesn't matter: a*b = b*a
    if op == "*" and b >= 1:
        out.append(((op, x, y), ("+", ("*", x, ("-", y, Fraction(1))), x)))   # repeated addition: a*b = a*(b-1)+a
    if op == "*" and b == 2 and value == a + a:
        out.append(((op, n, b), ("+", n, n)))              # doubling: n*2 = n+n
    if op == "*" and a == 2 and value == b + b:
        out.append(((op, a, n), ("+", n, n)))              # 2*n = n+n
    return [(compose.to_text(lhs), rhs if isinstance(rhs, tuple) else f(rhs)) for lhs, rhs in out]


def known_facts(brain):
    """Memory as (problem, tree, value), parsed once."""
    out = []
    for problem, fact in brain.memory.items():
        if fact.get("free"):
            continue
        try:
            out.append((problem, compose.parse(problem), compose.to_value(fact["answer"])))
        except ValueError:
            continue
    return out


def _from_memory(tree, remembered):
    """Work out the rule's other side using what the brain REMEMBERS where it
    can (a*b = b*a checks 3*7 against its memory of 7*3), and plain counting
    only for the joins between remembered facts."""
    if isinstance(tree, Fraction):
        return tree
    if tree[0] == "neg":
        return -_from_memory(tree[1], remembered)
    if _leaf(tree[1]) and _leaf(tree[2]):
        key = f"{compose.fmt(tree[1])}{tree[0]}{compose.fmt(tree[2])}"
        if key in remembered:
            return remembered[key]
    a, b = _from_memory(tree[1], remembered), _from_memory(tree[2], remembered)
    return compose.evaluate((tree[0], a, b))


def evidence(facts, lhs, rhs):
    """Facts that fit the rule, and facts that break it, judged against the
    brain's own memories."""
    left, right, _ = parse_rule(lhs, rhs)
    remembered = {problem: value for problem, _, value in facts}
    fits, breaks = [], []
    for problem, tree, value in facts:
        bound = compose.match(left, tree)
        if bound is None:
            continue
        other = compose.substitute(right, bound)
        if isinstance(other, tuple) and other == tree:
            continue                       # a*b = b*a on 3*3 says nothing
        try:
            expected = _from_memory(other, remembered)
        except ValueError:
            continue
        (fits if expected == value else breaks).append(problem)
    return fits, breaks


def _rhs_text(rhs):
    return compose.to_text(rhs) if isinstance(rhs, tuple) else rhs


def suggest(brain, facts):
    """The best new rule these facts point to, if the memory agrees with it.
    -> {"rule", "examples"} or None."""
    best = None
    seen = set()
    memory = known_facts(brain)
    for problem, answer in facts:
        for lhs, rhs in candidates(problem, answer):
            rhs = _rhs_text(rhs)
            try:
                _, _, name = parse_rule(lhs, rhs)
            except ValueError:
                continue
            if name in seen or name in brain.rules:
                continue
            seen.add(name)
            fits, breaks = evidence(memory, lhs, rhs)
            if breaks or len(fits) < MIN_EXAMPLES:
                continue
            if best is None or len(fits) > len(best["examples"]):
                best = {"rule": name, "examples": fits}
    if best:
        best["examples"] = best["examples"][:6]
    return best


def suggest_from_memory(brain):
    facts = [(p, f["answer"]) for p, f in brain.memory.items() if not f.get("free")]
    return suggest(brain, facts)
