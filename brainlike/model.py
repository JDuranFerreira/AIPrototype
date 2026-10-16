"""The core numeric type used across the brain: c + sum(k_i * x_i)."""

from fractions import Fraction


class Lin:
    """c + sum(k_i * x_i): a number, or a number with unknowns in it."""
    __slots__ = ("c", "k")

    def __init__(self, c=0, k=None):
        self.c = Fraction(c)
        self.k = {v: x for v, x in (k or {}).items() if x}

    def __add__(self, o):
        k = dict(self.k)
        for v, x in o.k.items():
            k[v] = k.get(v, 0) + x
        return Lin(self.c + o.c, k)

    def __neg__(self):
        return Lin(-self.c, {v: -x for v, x in self.k.items()})

    def __sub__(self, o):
        return self + (-o)

    def scale(self, f):
        return Lin(self.c * f, {v: x * f for v, x in self.k.items()})

    def times(self, o):
        if self.k and o.k:
            return None
        return o.scale(self.c) if not self.k else self.scale(o.c)

    def over(self, o):
        if o.k or o.c == 0:
            return None
        return self.scale(1 / o.c)

    def bind(self, bound):
        if not any(v in bound for v in self.k):
            return self
        out = Lin(self.c)
        for v, x in self.k.items():
            out = out + (Lin(bound[v] * x) if v in bound else Lin(0, {v: x}))
        return out

    @property
    def known(self):
        return not self.k

    def __repr__(self):
        return str(self.c) if not self.k else f"{self.c}+{self.k}"


def fmt(v):
    if isinstance(v, Lin):
        if not v.known:
            return "?"
        v = v.c
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
