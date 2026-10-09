"""Missing numbers and comparing, for the arithmetic region.

Missing numbers (part-whole thinking, as in Singapore's model method)
  8 + ? = 11   the whole is 11 and one part is 8, so the missing part is 11 - 8.
  The brain learns this as an INVERSE RULE, one per shape:
      a+?=c  ->  c-a        ?+b=c  ->  c-b        a-?=c  ->  a-c       ?-b=c  ->  c+b
      a*?=c  ->  c/a        ?*b=c  ->  c/b        a/?=c  ->  a/c       ?/b=c  ->  c*b
  It can be taught a rule, or notice it from examples the teacher answered:
  it tries the few ways to combine the two known numbers and keeps the one
  that fits every example. It then works the answer out with its own
  arithmetic, and checks it by putting it back in ("8 + 3 is 11, yes").

Comparing
  Which is bigger, 45 or 54?   45 ? 54  (<, = or >)
  It works out 54 - 45 with its own arithmetic and reads the sign: comparing
  is subtracting (reading the sign of a number is perception).
"""
import re
from fractions import Fraction

from . import compose

_EQ = re.compile(r"^\s*(?P<l>[^=]+?)\s*=\s*(?P<r>[^=]+?)\s*$")
_SHAPE = re.compile(r"^\s*(\?|-?\d+(?:\.\d+)?)\s*([-+*/xX×÷])\s*(\?|-?\d+(?:\.\d+)?)\s*$")
_NUM = r"-?\d+(?:\.\d+)?(?:/\d+)?"                 # 45, 0.5, 3/4
_CMP_WORDS = re.compile(rf"^(?:which (?:number )?is (bigger|greater|larger|more|smaller|less|lesser),?\s*)"
                        rf"({_NUM})\s*(?:or|and)\s*({_NUM})\s*\??$", re.I)
_CMP_FILL = re.compile(rf"^\s*({_NUM})\s*(?:\?|_+|□)\s*({_NUM})\s*$")
_CMP_CHECK = re.compile(rf"^\s*(?:is\s+)?({_NUM})\s*(<=|>=|<|>|=)\s*({_NUM})\s*\??\s*$", re.I)
_OPS = {"x": "*", "X": "*", "×": "*", "÷": "/"}
CANDIDATES = ["c-a", "a-c", "c+a", "c*a", "c/a", "a/c"]     # ways to combine the two known numbers


def read_equation(text):
    """'8 + ? = 11' -> ('a+?=c', a, c) with a, c as text; or None."""
    m = _EQ.match(text)
    if not m or "?" not in text:
        return None
    left, right = m["l"], m["r"]
    if "?" in right and "?" not in left:
        left, right = right, left                       # 11 = 8 + ?  ->  8 + ? = 11
    s = _SHAPE.match(left)
    if not s or not re.fullmatch(r"\s*-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?\s*", right) or left.count("?") != 1:
        return None
    x, op, y = s[1], _OPS.get(s[2], s[2]), s[3]
    shape = f"a{op}?=c" if y == "?" else f"?{op}b=c"
    return shape, (x if y == "?" else y), right.strip()


def read_compare(text):
    """-> ('which', word, a, b) | ('fill', a, b) | ('check', a, sign, b) | None."""
    if m := _CMP_WORDS.match(text.strip()):
        return "which", m[1].lower(), m[2], m[3]
    if m := _CMP_CHECK.match(text):
        return "check", m[1], m[2], m[3]
    if m := _CMP_FILL.match(text):
        return "fill", m[1], m[2]
    return None


def _combine(how, known, total):
    return how.replace("a", f"({known})").replace("c", f"({total})")


def notice(examples):
    """examples: [(shape, known, total, answer)] -> {shape: how} for shapes where one way fits them all."""
    found = {}
    shapes = {e[0] for e in examples}
    for shape in shapes:
        mine = [e for e in examples if e[0] == shape]
        if len(mine) < 3:
            continue
        for how in CANDIDATES:
            try:
                if all(compose.true_value(_combine(how, k, t)) == compose.to_value(ans) for _, k, t, ans in mine):
                    found[shape] = how
                    break
            except (ValueError, ZeroDivisionError):
                continue
    return found


def solve(brain_work_out, solving, text):
    """Solve '8 + ? = 11' with a learned inverse rule. brain_work_out(problem) -> (value, steps).
    -> dict(answer, rule, steps, check) or None if it hasn't learned this shape."""
    eq = read_equation(text)
    if not eq:
        return None
    shape, known, total = eq
    how = solving.get(shape)
    if not how:
        return {"shape": shape, "answer": None}
    problem = compose.normalize(_combine(how, known, total))
    value, steps = brain_work_out(problem)
    filled = text.replace("?", f"({compose.fmt(value)})" if value < 0 else compose.fmt(value))
    lhs, rhs = filled.split("=")
    try:
        back = brain_work_out(compose.normalize(lhs if "?" in text.split("=")[0] else rhs))[0]
        check = back == compose.to_value(total)
    except ValueError:
        check = None
    return {"shape": shape, "rule": f"{shape} -> {how}", "problem": problem, "answer": compose.fmt(value),
            "steps": steps, "check": check}


_REMAINDER_Q = re.compile(r"^(?:what is )?(\d+)\s*(?:÷|/|divided by)\s*(\d+)\s*,?\s*(?:with (?:a |the )?remainders?|r)\s*\??$", re.I)
_REMAINDER_ONLY = re.compile(r"^(?:what is )?the remainder (?:when|of) (\d+) (?:is )?divided by (\d+)\s*\??$", re.I)
_SIMPLEST = re.compile(r"^(?:what is )?(?:the )?simplest form of (\d+)\s*/\s*(\d+)\s*\??$", re.I)


def read_whole_division(text):
    """'17 ÷ 5 with remainder' -> ('qr', 17, 5); 'the remainder when 17 is divided by 5' -> ('r', 17, 5)."""
    if m := _REMAINDER_Q.match(text.strip()):
        return "qr", m[1], m[2]
    if m := _REMAINDER_ONLY.match(text.strip()):
        return "r", m[1], m[2]
    return None


def read_simplest(text):
    m = _SIMPLEST.match(text.strip())
    return (m[1], m[2]) if m else None


def simplest(brain_work_out, top, bottom):
    """Simplest form, the brain's way: find the biggest number that divides both by
    taking the smaller away from the bigger until they match (Euclid), then
    divide both by it. -> (text, common factor, steps)."""
    a, b = int(top), int(bottom)
    if b == 0:
        raise ValueError("a fraction can't have 0 at the bottom")
    x, y, rounds = a, b, 0
    while x and y and x != y and rounds < 500:
        if x > y:
            x = int(brain_work_out(f"{x}-{y}")[0])
        else:
            y = int(brain_work_out(f"{y}-{x}")[0])
        rounds += 1
    g = x or y or 1
    n = int(brain_work_out(f"{a} div {g}")[0])
    d = int(brain_work_out(f"{b} div {g}")[0])
    return (str(n) if d == 1 else f"{n}/{d}"), g, rounds


def compare(brain_work_out, a, b):
    """-> '<', '=' or '>' by working out a - b with the brain's own arithmetic."""
    diff, steps = brain_work_out(compose.normalize(f"({a})-({b})"))
    return ("<" if diff < 0 else ">" if diff > 0 else "="), diff, steps
