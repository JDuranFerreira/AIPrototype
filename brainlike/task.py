"""The world the brain lives in: single-digit arithmetic, plus a checker that
only says right or wrong (it never reveals the answer)."""
import re

import numpy as np

OPS = "+-*"
N_DIGITS = 10
MIN_RESULT, MAX_RESULT = -9, 81          # 0-9 = -9 ... 9*9 = 81
N_ANSWERS = MAX_RESULT - MIN_RESULT + 1  # every answer the brain can say
INPUT_SIZE = 2 * N_DIGITS + len(OPS)

_PATTERN = re.compile(r"^\s*(\d)\s*([+\-*])\s*(\d)\s*$")


def parse(problem):
    m = _PATTERN.match(problem)
    if not m:
        raise ValueError(f"expected 'a op b' with single digits and one of {OPS}, got {problem!r}")
    return int(m.group(1)), m.group(2), int(m.group(3))


def normalize(problem):
    a, op, b = parse(problem)
    return f"{a}{op}{b}"


def all_problems():
    return [f"{a}{op}{b}" for op in OPS for a in range(N_DIGITS) for b in range(N_DIGITS)]


def check(problem, answer):
    """The teacher: says yes or no, like a parent correcting a child."""
    if not _PATTERN.match(problem):
        from .compose import to_value, true_value      # big problems like 10*10 or 7/2
        return to_value(answer) == true_value(problem)
    a, op, b = parse(problem)
    truth = a + b if op == "+" else a - b if op == "-" else a * b
    return answer == truth


def encode(problem):
    """Turn '3+4' into numbers the brain can perceive.

    Each digit is a 'thermometer' (3 -> 1110000000): the brain perceives how
    MANY, not a symbol. Giving it the symbol too (a one-hot) made it memorise
    facts instead of learning rules (15% vs 68% on unseen problems).
    The operator is one-hot.
    """
    a, op, b = parse(problem)
    x = np.zeros(INPUT_SIZE)
    x[:a] = 1
    x[N_DIGITS:N_DIGITS + b] = 1
    x[2 * N_DIGITS + OPS.index(op)] = 1
    return x


def to_answer(index):
    return index + MIN_RESULT


def to_index(answer):
    return answer - MIN_RESULT
