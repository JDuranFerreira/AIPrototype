"""Big problems (10*10, 1+1+1, 12*(3+4), 7/2, -2.5*4), solved the way children
do: break them into single-digit facts the brain knows, using written methods
(column addition with carry, column subtraction with borrow, long
multiplication, long division).

Every single-digit fact comes from the brain (memory or a module's guess), so
the answer is only as good as those facts. Reading digits, carrying,
borrowing, bringing a digit down, moving the decimal point and comparing sizes
are the "procedure": fixed rules like the ones a teacher writes on the board.

Values are exact fractions, so 1/3 stays 1/3 instead of 0.333...
"""
import re
from fractions import Fraction

_WORD_OPS = r"divup(?![a-z])|div(?![a-z])|rem(?![a-z])"       # division with a remainder (see Worker._divmod)
_TOKEN = re.compile(rf"\s*(\d+\.\d*|\.\d+|\d+|[-+*xX×·/÷()%^]|{_WORD_OPS})", re.I)
_TOKEN_VARS = re.compile(rf"\s*(\d+\.\d*|\.\d+|\d+|[-+*xX×·/÷()%^]|{_WORD_OPS}|[a-wyzA-WYZ](?![a-zA-Z]))")   # x means times
REMAINDER_OPS = ("div", "rem", "divup")
SPACED_OPS = REMAINDER_OPS + ("%",)         # written with spaces round them ("17 % 5")
MAX_POWER = 100                             # past this a power is too big to work out step by step
_MUL, _DIV = set("*xX×·"), set("/÷")
_BASIC = re.compile(r"^(\d)([+\-*])(\d)$")


def tokenize(text, variables=False):
    """variables=True also accepts single letters standing for any number (rules like n/n = 1).
    '**' is how Python writes a power; it becomes the one sign '^'."""
    pattern = _TOKEN_VARS if variables else _TOKEN
    tokens, pos, text = [], 0, text.strip().replace("**", "^")
    while pos < len(text):
        m = pattern.match(text, pos)
        if not m:
            raise ValueError(f"I don't understand {text[pos:].strip()!r} as math")
        t = m.group(1)
        t = t.lower() if t.lower() in REMAINDER_OPS else t
        tokens.append("*" if t in _MUL else "/" if t in _DIV else t.lower() if t.isalpha() else t)
        pos = m.end()
    return tokens


def _is_number(t):
    return t is not None and (t[0].isdigit() or t[0] == ".")


def parse(text, variables=False):
    """Text -> tree: a Fraction, or (op, left, right), or ("neg", x), or
    (with variables=True) ("var", "n"). Usual order: brackets, then * and /,
    then + and -."""
    tokens = tokenize(text, variables)
    if not tokens:
        raise ValueError("Type a problem like 3+4 or 10*10")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def number():
        t = peek()
        if t in ("-", "+"):
            take()
            inner = number()
            return ("neg", inner) if t == "-" else inner
        if t == "(":
            take()
            node = expr()
            if peek() != ")":
                raise ValueError("a '(' is never closed")
            take()
            return node
        if t is not None and t.isalpha() and t not in REMAINDER_OPS:
            return ("var", take())
        if not _is_number(t):
            raise ValueError(f"expected a number, got {t or 'nothing'}")
        return Fraction(take())

    def power():
        node = number()
        while peek() == "^":                              # 2^3^2 is 2^(3^2)
            take()
            node = ("^", node, power())
        return node

    def term():
        node = power()
        while peek() in ("*", "/", "div", "rem", "divup", "%"):
            node = (take(), node, power())
        return node

    def expr():
        node = term()
        while peek() in ("+", "-"):
            node = (take(), node, term())
        return node

    tree = expr()
    if pos != len(tokens):
        raise ValueError(f"unexpected {tokens[pos]!r}")
    inner = tree[1] if isinstance(tree, tuple) and tree[0] == "neg" else tree
    if not (isinstance(inner, tuple) and (inner[0] in "+-*/%" or inner[0] in REMAINDER_OPS or inner[0] == "^")):
        raise ValueError("that's just a number; give it something to work out, like 3+4")
    return tree


def parse_side(text):
    """The right side of a rule: may be just a number or a letter ("1", "n", "2*n")."""
    try:
        return parse(text, variables=True)
    except ValueError:
        t = tokenize(text, variables=True)
        if len(t) == 1:
            return ("var", t[0]) if t[0].isalpha() else Fraction(t[0])
        if len(t) == 2 and t[0] == "-":
            return ("neg", ("var", t[1])) if t[1].isalpha() else -Fraction(t[1])
        raise


def normalize(text, variables=False):
    parse(text, variables)
    return "".join(f" {t} " if t in SPACED_OPS else t for t in tokenize(text, variables)).replace("  ", " ").strip()


def variables_in(tree):
    if isinstance(tree, Fraction):
        return set()
    if tree[0] == "var":
        return {tree[1]}
    return set().union(*(variables_in(t) for t in tree[1:]))


_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "div": 2, "rem": 2, "divup": 2, "%": 2, "^": 3}


def to_text(tree):
    """Tree -> text, with brackets only where needed."""
    if isinstance(tree, Fraction):
        return fmt(tree) if tree >= 0 else f"({fmt(tree)})"
    if tree[0] == "var":
        return tree[1]
    if tree[0] == "neg":
        inner = to_text(tree[1])
        return f"-{inner}" if isinstance(tree[1], Fraction) or tree[1][0] == "var" else f"-({inner})"
    op, left, right = tree

    def side(t, is_right):
        s = to_text(t)
        if isinstance(t, tuple) and t[0] in _PREC and (
                _PREC[t[0]] < _PREC[op] or (is_right and _PREC[t[0]] == _PREC[op] and op in ("-", "/", *SPACED_OPS))):
            return f"({s})"
        return s
    joiner = f" {op} " if op in SPACED_OPS else op
    return f"{side(left, False)}{joiner}{side(right, True)}"


def evaluate(tree, env=None):
    """Exact value of a tree (the math checker's arithmetic, not the brain's)."""
    env = env or {}
    if isinstance(tree, Fraction):
        return tree
    if tree[0] == "var":
        return evaluate(env[tree[1]])
    if tree[0] == "neg":
        return -evaluate(tree[1], env)
    a, b = evaluate(tree[1], env), evaluate(tree[2], env)
    if tree[0] in ("/", "%", *REMAINDER_OPS) and b == 0:
        raise ValueError("you can't divide by zero")
    if tree[0] == "/":
        return a / b
    if tree[0] in ("rem", "%"):
        _whole_numbers(a, b, "rem")
        return Fraction(divmod(int(a), int(b))[1])
    if tree[0] in REMAINDER_OPS:
        _whole_numbers(a, b, tree[0])
        q, r = divmod(int(a), int(b))
        return Fraction(q if tree[0] == "div" else q + (1 if r else 0))
    if tree[0] == "^":
        if b.denominator != 1 or abs(b) > MAX_POWER:
            raise ValueError("the power has to be a whole number, like 2^10")
        if a.denominator != 1:
            raise ValueError("only whole numbers to a power, like 2^10")
        if a == 0 and b <= 0:
            raise ValueError("you can't raise zero to nothing")
        return a ** int(b)
    return a + b if tree[0] == "+" else a - b if tree[0] == "-" else a * b


def _whole_numbers(a, b, op):
    if a.denominator != 1 or b.denominator != 1 or a < 0 or b <= 0:
        raise ValueError(f"'{op}' works with whole numbers, like 17 {op} 5")


def is_basic(text):
    """Single digit op single digit: what the modules learn directly."""
    return bool(_BASIC.match(normalize(text)))


def true_value(text):
    return evaluate(parse(text))


def to_value(answer):
    """'12', '3.5', '-7/2' or 12 -> exact Fraction."""
    try:
        return Fraction(str(answer).strip())
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"{answer!r} isn't a number (examples: 12, -4, 3.5, 7/2)")


def match(pattern, tree, bound=None):
    """Does `tree` fit `pattern` (n/n fits 7/7 and (2+3)/(2+3))? -> {var: subtree} or None."""
    bound = {} if bound is None else bound
    if isinstance(pattern, tuple) and pattern[0] == "var":
        if pattern[1] in bound:
            return bound if bound[pattern[1]] == tree else None
        bound[pattern[1]] = tree
        return bound
    if isinstance(pattern, Fraction) or isinstance(tree, Fraction):
        return bound if isinstance(pattern, Fraction) and isinstance(tree, Fraction) and pattern == tree else None
    if pattern[0] != tree[0] or len(pattern) != len(tree):
        return None
    for p, t in zip(pattern[1:], tree[1:]):
        if match(p, t, bound) is None:
            return None
    return bound


def substitute(tree, bound):
    if isinstance(tree, Fraction):
        return tree
    if tree[0] == "var":
        return bound[tree[1]]
    return (tree[0], *(substitute(t, bound) for t in tree[1:]))


def _decimal_places(x):
    """How many digits after the point x needs, or None if it never ends (1/3)."""
    d, k = x.denominator, 0
    while d % 10 == 0:
        d //= 10
        k += 1
    twos = fives = 0
    while d % 2 == 0:
        d //= 2
        twos += 1
    while d % 5 == 0:
        d //= 5
        fives += 1
    return None if d != 1 else k + max(twos, fives)


def fmt(x):
    """Exact Fraction -> '12', '3.5' or '1/3'."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    k = _decimal_places(x)
    if k is None:
        return f"{x.numerator}/{x.denominator}"
    scaled = abs(x.numerator) * (10 ** k // x.denominator)
    whole, frac = divmod(scaled, 10 ** k)
    return f"{'-' if x < 0 else ''}{whole}.{str(frac).zfill(k).rstrip('0')}"


def _digits(n):
    return [int(d) for d in reversed(str(abs(n)))]      # little-endian: units first; a bad guess can go negative


def _clamp(d):
    return min(max(int(d), 0), 9)


def _bottom(d):
    """A wrong fact can turn a bottom number into 0. Keep going with 1 so the
    brain still gives an (incorrect) answer the teacher can correct."""
    return d or 1


def ops_in(tree):
    if isinstance(tree, Fraction) or tree[0] == "var":
        return set()
    own = {tree[0]} if tree[0] in "+-*/" else set()
    return own.union(*(ops_in(t) for t in tree[1:]))


def explains(lhs, rhs):
    """A rule whose other side is a calculation (a*b = a*(b-1)+a, n*2 = n+n)
    explains how to work a fact out; one whose other side is just a number or
    a letter (n*0 = 0) is a one-step shortcut."""
    return isinstance(lhs, tuple) and isinstance(rhs, tuple) and rhs[0] in "+-*/"


MAX_DEPTH = 60          # how deep one chain of reasoning may go before it gives up and guesses


class Worker:
    """Works out one big problem.

    fact("7+8")   -> (answer, info): memory, a rule, or a module's guess
    recall("7+8") -> (answer, info) or None: only what it KNOWS (memory, rules)

    With `recall`, a single-digit fact it doesn't know can be worked out from
    a rule that explains it (a*b = a*(b-1)+a) before falling back to a guess.
    """

    def __init__(self, fact, rules=(), recall=None):
        self._fact = fact
        self._recall = recall
        rules = list(rules)                              # (lhs tree, rhs tree, "n/n = 1")
        self._rules = [r for r in rules if not explains(r[0], r[1])]          # shortcuts
        # understanding: rules that say how to work a fact out, in terms of itself (a*b = a*(b-1)+a)
        # or of other operations (n*2 = n+n)
        self._explaining = [r for r in rules if explains(r[0], r[1])]
        self._rules_on = True
        self._deriving = []                              # facts being worked out right now
        self.steps = {}                                  # problem -> step, in order of use

    def run(self, text):
        return self._eval(parse(text))

    def f(self, a, op, b):
        a, b = _clamp(a), _clamp(b)                      # a bad earlier guess can't break the method
        problem = f"{a}{op}{b}"
        if problem not in self.steps:
            known = self._recall(problem) if self._recall else None
            derived = None if known else self._derive(problem, (op, Fraction(a), Fraction(b)))
            if known:
                self.steps[problem] = {"problem": problem, "answer": known[0], **known[1]}
            elif derived is not None:
                self.steps[problem] = derived
            else:
                answer, info = self._fact(problem)
                self.steps[problem] = {"problem": problem, "answer": answer, **info}
        return int(self.steps[problem]["answer"])

    def _derive(self, problem, tree):
        """Work out a fact it doesn't know from a rule that explains it."""
        if problem in self._deriving or len(self._deriving) >= MAX_DEPTH:
            return None
        for lhs, rhs, name in self._explaining:
            bound = match(lhs, tree)
            if bound is None:
                continue
            before = set(self.steps)
            self._deriving.append(problem)
            try:
                value = self._eval(substitute(rhs, bound))
            finally:
                self._deriving.pop()
            new = [k for k in self.steps if k not in before]
            if value.denominator != 1 or any(self.steps[k]["source"] == "module" for k in new):
                for k in new:                    # reasoning that rests on a guess is no better than a guess:
                    del self.steps[k]            # forget it and try the next rule
                continue
            return {"problem": problem, "answer": int(value), "source": "derived", "rule": name}
        return None

    # ---- values: exact fractions ---------------------------------------------
    def _eval(self, t):
        if isinstance(t, Fraction):
            return t
        if t[0] == "neg":
            return -self._eval(t[1])                     # flipping the sign is reading, not arithmetic
        shortcut = self._apply_rule(t)
        if shortcut is not None:
            return shortcut
        a, b = self._eval(t[1]), self._eval(t[2])
        if t[0] in REMAINDER_OPS:
            if b == 0:
                raise ValueError("you can't divide by zero")
            _whole_numbers(a, b, t[0])
            q, r = self._divmod(int(a), int(b))
            if t[0] == "div":
                return Fraction(q)
            if t[0] == "rem":
                return Fraction(r)
            return Fraction(self._add_signed(q, 1) if r else q)        # boxes needed: one more for the rest
        if t[0] in ("rem", "%"):
            if b == 0:
                raise ValueError("you can't divide by zero")
            _whole_numbers(a, b, "rem")
            return Fraction(self._divmod(int(a), int(b))[1])             # what is left over
        if t[0] == "^":
            if b.denominator != 1 or abs(b) > MAX_POWER:
                raise ValueError("the power has to be a whole number, like 2^10")
            if a.denominator != 1:
                raise ValueError("only whole numbers to a power, like 2^10")
            if a == 0 and b <= 0:
                raise ValueError("you can't raise zero to nothing")
            v = 1
            for _ in range(int(abs(b))):                # multiply it by itself again and again
                v = self._times(v, int(a))
            return Fraction(v if b >= 0 else Fraction(1, v))
        if t[0] == "/":
            return self._divide(a, b)
        if t[0] == "*":
            return self._times(a, b)
        return self._plus(a, b if t[0] == "+" else -b)

    def _apply_rule(self, t):
        """A known rule (n/n = 1) answers this part in one step, no digit work."""
        if not self._rules_on:
            return None
        for lhs, rhs, name in self._rules:
            bound = match(lhs, t)
            if bound is None:
                continue
            if t[0] == "/" and self._eval(t[2]) == 0:
                raise ValueError("you can't divide by zero")
            self._rules_on = False                       # work the right side out plainly: a rule
            try:                                         # like a+b = b+a must not loop forever
                value = self._eval(substitute(rhs, bound))
            finally:
                self._rules_on = True
            text = to_text(t)
            self.steps.setdefault(text, {"problem": text, "answer": fmt(value), "source": "rule", "rule": name})
            return value
        return None

    def _plus(self, a, b):
        ka, kb = _decimal_places(a), _decimal_places(b)
        if ka is not None and kb is not None:            # whole numbers and decimals: line up the points
            k = max(ka, kb)
            return Fraction(self._add_signed(int(a * 10 ** k), int(b * 10 ** k)), 10 ** k)
        # fractions: a/b + c/d = (a*d + c*b) / (b*d)
        num = self._add_signed(self._times_int(a.numerator, b.denominator),
                               self._times_int(b.numerator, a.denominator))
        return Fraction(num, _bottom(self._times_int(a.denominator, b.denominator)))

    def _times(self, a, b):
        ka, kb = _decimal_places(a), _decimal_places(b)
        if ka is not None and kb is not None:            # multiply as whole numbers, then place the point
            return Fraction(self._times_int(int(a * 10 ** ka), int(b * 10 ** kb)), 10 ** (ka + kb))
        return Fraction(self._times_int(a.numerator, b.numerator),
                        _bottom(self._times_int(a.denominator, b.denominator)))

    def _divide(self, a, b):
        if b == 0:
            raise ValueError("you can't divide by zero")
        # a/b = (a.num * b.den) / (a.den * b.num), then long division
        top = self._times_int(a.numerator, b.denominator)
        bottom = _bottom(self._times_int(a.denominator, b.numerator))
        sign = -1 if (top < 0) != (bottom < 0) else 1
        return sign * self._long_division(abs(top), abs(bottom))

    def _times_int(self, a, b):
        if a == 1 or b == 1:                             # times one changes nothing
            return a * b
        sign = -1 if (a < 0) != (b < 0) else 1
        return sign * self._mul(abs(a), abs(b))

    # ---- written methods on whole numbers ------------------------------------
    def _add_signed(self, a, b):
        if a >= 0 and b >= 0:
            return self._add(a, b)
        if a < 0 and b < 0:
            return -self._add(-a, -b)
        pos, neg = (a, -b) if a >= 0 else (b, -a)
        if pos < 10 and neg < 10:
            return self.f(pos, "-", neg)                 # the modules know 3-7 = -4
        return self._sub(pos, neg) if pos >= neg else -self._sub(neg, pos)

    def _add(self, a, b):
        """Column addition with carry."""
        if a < 10 and b < 10:
            return self.f(a, "+", b)
        da, db = _digits(a), _digits(b)
        out, carry = [], 0
        for i in range(max(len(da), len(db))):
            x = da[i] if i < len(da) else 0
            y = db[i] if i < len(db) else 0
            s = x if y == 0 else y if x == 0 else self.f(x, "+", y)
            tens, units = divmod(s, 10)
            if carry:
                tens2, units = divmod(self.f(units, "+", 1), 10)
                tens += tens2
            out.append(units)
            carry = tens
        return sum(d * 10 ** i for i, d in enumerate(out)) + carry * 10 ** len(out)

    def _sub(self, a, b):
        """Column subtraction with borrow, for a >= b >= 0."""
        da, db = _digits(a), _digits(b)
        out, borrow = [], 0
        for i, x in enumerate(da):
            y = db[i] if i < len(db) else 0
            d = self.f(x, "-", y) if y else x
            new_borrow = 0
            if borrow:
                if d >= 1:
                    d = self.f(d, "-", 1)
                else:                                    # 10 + d - 1
                    d, new_borrow = self.f(9, "-", -d), 1
            elif d < 0:                                  # 10 + d
                d, new_borrow = self.f(self.f(9, "-", -d), "+", 1), 1
            out.append(d)
            borrow = new_borrow
        return sum(d * 10 ** i for i, d in enumerate(out))

    def _mul(self, a, b):
        """Long multiplication: digit products, shifted by place, added up."""
        if a < 10 and b < 10:
            return self.f(a, "*", b)
        total = 0
        for i, x in enumerate(_digits(a)):
            for j, y in enumerate(_digits(b)):
                if x and y:
                    partial = self.f(x, "*", y) * 10 ** (i + j)
                    total = self._add(total, partial) if total else partial
        return total

    def _divmod(self, top, bottom):
        """Long division that stops at the remainder: 17 div 5 = 3, 17 rem 5 = 2."""
        if bottom == 1:
            return top, 0
        return self._long_division(top, bottom, whole=True)

    def _long_division(self, top, bottom, whole=False):
        """Long division of whole numbers: bring a digit down, find how many
        times `bottom` fits (from its times table), subtract, repeat. Carries
        on after the point while the answer is a decimal that ends."""
        if bottom == 1:
            return (top, 0) if whole else Fraction(top)
        table = {}

        def times(q):                                    # bottom's times table, built from facts
            if q not in table:
                table[q] = bottom * q if q < 2 else self._times_int(q, bottom)
            return table[q]

        def step(current):
            q = 0
            while q < 9 and times(q + 1) <= current:     # comparing sizes is reading, not arithmetic
                q += 1
            return q, (self._add_signed(current, -times(q)) if q else current)

        quotient, rest = 0, 0
        for d in reversed(_digits(top)):
            q, rest = step(rest * 10 + d)                # "bring down" the next digit
            quotient = quotient * 10 + q
        if whole:
            return quotient, rest
        places, ends = 0, _decimal_places(Fraction(1, bottom))
        while rest and ends is not None and places < ends:
            q, rest = step(rest * 10)                    # bring down a 0 after the point
            quotient = quotient * 10 + q
            places += 1
        # anything left over stays an exact fraction (1/3 is 1/3, not 0.333...)
        return Fraction(quotient, 10 ** places) + Fraction(rest, bottom * 10 ** places)
