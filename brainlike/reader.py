"""The reader: the language region's own way to understand a word problem,
with no language model.

Children learn that word problems come in a few kinds (schemas, in
cognitive science: combine, change, compare, equal groups, sharing...). The
reader learns those schemas from worked examples:

  1. perception  find the numbers in the story and call them N0, N1, N2 (in order)
  2. learned     which schema is this? A small classifier reads the words
                 ("each", "altogether", "left", "how many more", "shared") and
                 picks a schema seen in training, e.g.  N0*N1,  N0-N1,  (N0+N1)/N2
  3. number sense if the best schema gives an impossible answer (negative, or
                 3.7 children for "how many"), take the next best one
  4. arithmetic  the arithmetic region works the answer out, exactly

Training data: worked examples with their equations (the benchmark's
MAWPS + ASDiv-A problems, and the teacher's bar models from school).
"""
import json
import re
from fractions import Fraction
from pathlib import Path

import numpy as np

from . import compose

N_FEATURES = 2 ** 12               # words are hashed into this many slots
_NUM = re.compile(r"(?<![\w.])(\d+(?:,\d{3})*(?:\.\d+)?)(?![\w.]*\d)")
_WORD = re.compile(r"[a-z]+")
STOP = {"the", "a", "an", "of", "to", "and", "in", "on", "at", "is", "was", "for", "his", "her", "he", "she",
        "they", "it", "with", "has", "had", "have", "there", "are", "were", "by", "that", "this", "then"}


def numbers(text):
    """Perception: the numbers in a story, in order (commas in 1,000 are ignored)."""
    return [m.replace(",", "") for m in _NUM.findall(text)]


def mask(text):
    """'Tom has 5 apples' -> 'Tom has N0 apples' (and the numbers)."""
    found, i = [], [0]

    def swap(m):
        found.append(m.group(1).replace(",", ""))
        i[0] += 1
        return f" N{i[0] - 1} "
    return _NUM.sub(swap, text), found


def _hash(s):
    h = 2166136261
    for ch in s.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h % N_FEATURES


def features(masked, nums):
    """Which words appear, which words come right after a number, and the question's own words."""
    text = masked.lower()
    sentences = [s for s in re.split(r"[.?!]", text) if s.strip()]
    question = sentences[-1] if sentences else text
    words = [w for w in _WORD.findall(text) if w not in STOP]
    feats = [f"w:{w}" for w in words]
    feats += [f"b:{a}_{b}" for a, b in zip(words, words[1:])]
    feats += [f"q:{w}" for w in _WORD.findall(question) if w not in STOP]
    q = _WORD.findall(question)
    feats += [f"qb:{a}_{b}" for a, b in zip(q, q[1:])]
    for k, m in enumerate(re.finditer(r"\bn(\d)\b\s+([a-z]+)", text)):
        feats.append(f"after{m.group(1)}:{m.group(2)}")          # what each number counts ("5 apples")
    feats.append(f"count:{len(nums)}")
    vals = [float(x) for x in nums]
    for a in range(len(vals)):
        for b in range(a + 1, len(vals)):
            feats.append(f"bigger:{a}{b}:{vals[a] > vals[b]}")   # number sense: which is bigger
    x = np.zeros(N_FEATURES, dtype=np.float32)
    for f in feats:
        x[_hash(f)] = 1.0
    return x


def prefix_to_template(prefix):
    """'- number0 number1' -> '(N0-N1)'; the training sets write equations in prefix form."""
    tokens = prefix.split()

    def walk(i):
        t = tokens[i]
        if t in "+-*/":
            left, i = walk(i + 1)
            right, i = walk(i)
            return f"({left}{t}{right})", i
        if t.startswith("number"):
            return f"N{t[6:]}", i + 1
        return compose.fmt(Fraction(t)), i + 1
    text, end = walk(0)
    if end != len(tokens):
        raise ValueError(f"bad equation {prefix!r}")
    return text


def fill(template, nums):
    expr = re.sub(r"N(\d+)", lambda m: f"({nums[int(m.group(1))]})", template)
    return re.sub(r"\b(divup|div|rem)\b", r" \1 ", expr)


class Reader:
    def __init__(self, templates=None, W=None, b=None):
        self.templates = templates or []
        self.W = W                       # N_FEATURES x templates
        self.b = b

    @property
    def n_weights(self):
        return 0 if self.W is None else self.W.size + self.b.size

    def train(self, examples, epochs=30, lr=0.5, l2=1e-4, min_count=1, seed=0):
        """examples: (masked text, numbers, template). Softmax classifier, plain NumPy."""
        counts = {}
        for _, _, t in examples:
            counts[t] = counts.get(t, 0) + 1
        self.templates = sorted(t for t, n in counts.items() if n >= min_count)
        index = {t: i for i, t in enumerate(self.templates)}
        data = [(features(m, n), index[t]) for m, n, t in examples if t in index]
        X = np.stack([d[0] for d in data])
        y = np.array([d[1] for d in data])
        k = len(self.templates)
        rng = np.random.default_rng(seed)
        self.W = np.zeros((N_FEATURES, k), dtype=np.float32)
        self.b = np.zeros(k, dtype=np.float32)
        for _ in range(epochs):
            for batch in np.array_split(rng.permutation(len(X)), max(1, len(X) // 64)):
                z = X[batch] @ self.W + self.b
                z -= z.max(1, keepdims=True)
                p = np.exp(z)
                p /= p.sum(1, keepdims=True)
                p[np.arange(len(batch)), y[batch]] -= 1
                self.W -= lr * (X[batch].T @ p / len(batch) + l2 * self.W)
                self.b -= lr * p.mean(0)
        return self

    def rank(self, text):
        """-> list of (template, probability, numbers), best first."""
        masked, nums = mask(text)
        z = features(masked, nums) @ self.W + self.b
        p = np.exp(z - z.max())
        p /= p.sum()
        out = []
        for i in np.argsort(-p):
            t = self.templates[i]
            needed = {int(n) for n in re.findall(r"N(\d+)", t)}
            if needed and max(needed) < len(nums):
                out.append((t, float(p[i]), nums))
        return out

    def read(self, text, sensible=None, top=8):
        """The best schema whose answer makes sense. `sensible(expr)` is the brain's number sense:
        -> True/False. Returns (expression, probability, how) or None."""
        whole = bool(re.search(r"\bhow many\b", text, re.I))
        for template, prob, nums in self.rank(text)[:top]:
            expr = fill(template, nums)
            if sensible is None or sensible(expr, whole):
                return expr, prob, template
        return None

    # persistence -------------------------------------------------------------
    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / "reader.npz", W=self.W, b=self.b)
        (folder / "reader_templates.json").write_text(json.dumps(self.templates), encoding="utf-8")

    @classmethod
    def load(cls, folder):
        folder = Path(folder)
        if not (folder / "reader.npz").exists():
            return cls()
        data = np.load(folder / "reader.npz")
        return cls(json.loads((folder / "reader_templates.json").read_text(encoding="utf-8")), data["W"], data["b"])


def school_examples(curriculum):
    """The teacher's bar models from school as training examples: '3 km 250 m in metres' -> (N0*1000+N1).
    Numbers that are in the story become N0, N1 ...; others (1000, 60) are facts and stay as they are."""
    from .planner import is_plan, parse as parse_plan
    out = []
    for level in curriculum.values():
        for part in level.values():
            for item in part["lessons"]:
                if item[0] != "word":
                    continue
                text, model = item[1], item[2]
                if is_plan(model):                       # plan: cost = 8+5; 20-cost  ->  20-(8+5)
                    steps, expr = parse_plan(model), ""
                    for name, e in steps:
                        expr = e if not expr else re.sub(rf"\b{re.escape(prev)}\b", f"({expr})", e)
                        prev = name or "last"
                    model = expr
                masked, nums = mask(text)
                used = []

                def slot(m):
                    v = Fraction(m.group(0))
                    for i, n in enumerate(nums):
                        if i not in used and Fraction(n) == v:
                            used.append(i)
                            return f"N{i}"
                    return m.group(0)
                template = re.sub(r"\d+(?:\.\d+)?", slot, model.replace(" ", ""))
                out.append((masked, nums, template))
    return out


def number_sense(expr, whole):
    """Would a pupil accept this answer? Positive, and a whole number when the question asks 'how many'.
    (Exact arithmetic here only judges the sign and wholeness; the arithmetic region gives the answer.)"""
    try:
        v = compose.true_value(compose.normalize(expr))
    except (ValueError, ZeroDivisionError):
        return False
    return v > 0 and (not whole or v.denominator == 1)
