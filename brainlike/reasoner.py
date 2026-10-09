"""The reasoner: understands a word problem step by step, with no language model.

A good pupil doesn't guess one formula for the whole story. They look at the
quantities they know, combine the two that belong together, write the result
down, and repeat until the question is answered:

    "Natalia sold clips to 48 friends in April, and half as many in May.
     How many clips did she sell altogether?"
       quantities: 48 (friends, April) · 2 (from "half")
       step 1: 48 / 2 = 24
       step 2: 48 + 24 = 72      -> stop: that answers "altogether"

What it learns (an averaged perceptron, plain NumPy) is which step looks right:
it scores every operation on every pair of quantities from the words around
each number ("5 apples", "more than", "each"), the question's words, and
number sense (which is bigger). It is trained on worked solutions written by
people (GSM8K's step-by-step solutions, MAWPS/ASDiv equations, and the school's
bar models): the same way pupils learn from worked examples in a textbook.

The plan it finds is handed to the arithmetic region, which works it out exactly.
"""
import json
import re
from fractions import Fraction
from pathlib import Path

import numpy as np

from . import compose

OPS = ["+", "-", "*", "/"]
CONSTANTS = [Fraction(v) for v in ("1", "2", "3", "4", "7", "10", "12", "60", "100", "1/2")]
MAX_STEPS = 8
N_FEATURES = 2 ** 20
STOP_WORDS = {"the", "a", "an", "of", "to", "and", "in", "on", "at", "is", "was", "for", "his", "her", "he", "she",
              "they", "it", "with", "has", "had", "have", "there", "are", "were", "by", "that", "this", "then", "if",
              "be", "as", "so", "i", "you", "we", "my", "their", "its", "will", "would", "can", "do", "does", "did"}
_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_TOKEN = re.compile(r"\$?\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+)?%?|[a-z]+(?:-[a-z]+)?|[.?!]", re.I)


def _word_number(words, i):
    """'twenty five' / 'twenty-five' / 'seven' at words[i] -> (value, words used) or None."""
    w = words[i].lower()
    parts = w.split("-")
    if len(parts) == 2 and parts[0] in _TENS and parts[1] in _UNITS:
        return _TENS[parts[0]] + _UNITS[parts[1]], 1
    if w in _TENS:
        if i + 1 < len(words) and words[i + 1].lower() in _UNITS and _UNITS[words[i + 1].lower()] < 10:
            return _TENS[w] + _UNITS[words[i + 1].lower()], 2
        return _TENS[w], 1
    if w in _UNITS and w != "one":            # "one" is too often not a number ("one day", "one of")
        return _UNITS[w], 1
    return None


class Quantity:
    __slots__ = ("value", "kind", "pos", "feats", "text")

    def __init__(self, value, kind, pos, feats, text):
        self.value, self.kind, self.pos, self.feats, self.text = value, kind, pos, feats, text


def perceive(text):
    """Tokens, the story's numbers (as Quantities) and the question's words."""
    raw = _TOKEN.findall(text)
    words, nums = [], []
    i = 0
    while i < len(raw):
        tok = raw[i]
        if tok[0].isdigit() or tok[0] == "$":
            t = tok.replace("$", "").replace(",", "").rstrip("%")
            try:
                v = Fraction(t)
            except (ValueError, ZeroDivisionError):
                i += 1
                continue
            nums.append((len(words), v, tok))
            words.append("<num>")
            if tok.endswith("%"):
                words.append("percent")
            i += 1
            continue
        wn = _word_number(raw, i) if tok.isalpha() or "-" in tok else None
        if wn:
            nums.append((len(words), Fraction(wn[0]), " ".join(raw[i:i + wn[1]])))
            words.append("<num>")
            i += wn[1]
            continue
        words.append(tok.lower())
        i += 1
    # the question is the last sentence
    ends = [k for k, w in enumerate(words) if w in ".?!"]
    q_start = 0
    if ends:
        last_end = ends[-1] if words[-1] in ".?!" else len(words)
        before = [k for k in ends if k < last_end - 0]
        q_start = (before[-2] + 1) if words[-1] in ".?!" and len(before) >= 2 else (before[-1] + 1 if before else 0)
    question = [w for w in words[q_start:] if w.isalpha() and w not in STOP_WORDS]
    quantities = []
    for rank, (pos, v, tok) in enumerate(nums):
        f = [f"prev:{_near(words, pos, -1)}", f"next:{_near(words, pos, 1)}", f"next2:{_near(words, pos, 2)}",
             f"rank:{min(rank, 5)}", f"inq:{pos >= q_start}", f"small:{v < 10}", f"frac:{v.denominator != 1}"]
        for d in range(-5, 6):
            if d and 0 <= pos + d < len(words) and words[pos + d].isalpha() and words[pos + d] not in STOP_WORDS:
                f.append(f"w:{words[pos + d]}")
        if tok.startswith("$"):
            f.append("money")
        if tok.endswith("%"):
            f.append("percent")
        quantities.append(Quantity(v, "story", pos, f, tok))
    return words, quantities, question


def _near(words, pos, d):
    k = pos + d
    while 0 <= k < len(words) and (words[k] in STOP_WORDS):
        k += 1 if d > 0 else -1
    return words[k] if 0 <= k < len(words) else "<edge>"


def _h(s):
    h = 2166136261
    for ch in s.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h % N_FEATURES


_FID = {}                                    # memoized _h: the same feature strings come back every step


def _fid(s):
    """The bucket _h(s) would give, without re-hashing a string we have already seen (~10x faster)."""
    v = _FID.get(s)
    if v is None:
        v = _FID[s] = _h(s)
    return v


class Reasoner:
    def __init__(self, W=None):
        self.W = W if W is not None else np.zeros(N_FEATURES, dtype=np.float32)

    @property
    def n_weights(self):
        return int(np.count_nonzero(self.W))

    # ---- the candidate steps and their features ------------------------------------------------
    def _setup(self, text):
        words, story, question = perceive(text)
        textwords = sorted({w for w in words if w.isalpha() and w not in STOP_WORDS})
        consts = [Quantity(c, "const", -1, [f"c:{c}"] + [f"c:{c}|t:{w}" for w in textwords], str(c)) for c in CONSTANTS]
        qfeats = [f"q:{w}" for w in question] + [f"qb:{a}_{b}" for a, b in zip(question, question[1:])]
        return story, consts, qfeats

    def _cands(self, pool, used, qfeats, step):
        """Every (op, i, j) on the pool, with its feature hashes, and STOP."""
        out = []
        for op in OPS:
            for i, a in enumerate(pool):
                for j, b in enumerate(pool):
                    if i == j or (a.kind == "const" and b.kind == "const"):
                        continue
                    if op in "+*" and j < i and not (a.kind == "const" or b.kind == "const"):
                        continue                       # a+b and b+a are the same step
                    if (op == "/" and b.value == 0) or (op == "-" and a.value - b.value < 0):
                        continue                       # number sense: no negatives, no dividing by 0
                    feats = [f"{op}|L|{f}" for f in a.feats] + [f"{op}|R|{f}" for f in b.feats]
                    feats += [f"{op}|{f}" for f in qfeats]
                    feats += [f"{op}|kinds:{a.kind}{b.kind}", f"{op}|big:{a.value > b.value}",
                              f"{op}|usedL:{i in used}", f"{op}|usedR:{j in used}", f"{op}|step:{min(step, 4)}",
                              f"{op}|whole:{(op != '/') or (b.value != 0 and (a.value / b.value).denominator == 1)}"]
                    out.append(((op, i, j), feats))
        unused = sum(1 for k, q in enumerate(pool) if q.kind == "story" and k not in used)
        stop = [f"STOP|{f}" for f in qfeats] + [f"STOP|step:{min(step, 6)}", f"STOP|unused:{min(unused, 4)}",
                                                "STOP|bias"]
        if step > 0:
            out.append(("STOP", stop))
        return out

    def _score(self, feats):
        return float(self.W[[_fid(f) for f in feats]].sum())

    def _gold(self, pool, op, ra, rb, n_story):
        """The gold step in the form _cands actually offers: for +/* the earlier-appearing quantity
        comes first (a+b == b+a, but _cands only generates one of the two orders). Without this,
        33% of the worked solutions named a step the candidate space said didn't exist."""
        i, j = self._index(pool, ra, n_story), self._index(pool, rb, n_story)
        if op in "+*" and j < i and pool[i].kind != "const" and pool[j].kind != "const":
            i, j = j, i
        return (op, i, j)

    def _gold_path(self, text, steps):
        """One entry per step of the worked solution: (indptr, data, gold_row, is_stop) where data/indptr
        hold every candidate's feature ids as CSR rows.  The gold path depends only on the text, so
        train() builds it once per example (~250 KB) and reuses it for every epoch instead of
        rebuilding and re-hashing the same feature strings each time."""
        story, consts, qfeats = self._setup(text)
        pool, used, path = story + consts, set(), []
        for s in range(len(steps) + 1):
            if s < len(steps):
                op, ra, rb = steps[s]
                gold = self._gold(pool, op, ra, rb, len(story))
            else:
                gold = "STOP"
            cands = self._cands(pool, used, qfeats, s)
            gold_row = next((r for r, (c, _) in enumerate(cands) if c == gold), None)
            lens = [len(feats) for _, feats in cands]
            ids = [_fid(f) for _, feats in cands for f in feats]
            indptr = np.zeros(len(lens) + 1, dtype=np.int32)
            indptr[1:] = np.cumsum(lens, dtype=np.int32)
            path.append((indptr, np.asarray(ids, dtype=np.int32), gold_row, gold == "STOP"))
            if gold_row is None:
                break                          # the worked solution does something the reasoner can't
            if gold == "STOP":
                break
            op, i, j = gold
            used.update((i, j))
            pool = pool + [self._apply(pool, op, i, j, s)]
        return path

    @staticmethod
    def _apply(pool, op, i, j, step):
        a, b = pool[i], pool[j]
        v = a.value + b.value if op == "+" else a.value - b.value if op == "-" else a.value * b.value if op == "*" \
            else a.value / b.value
        feats = [f"res_op:{op}", f"res_age:{step}", "res"] + [f"from:{f}" for f in a.feats[:3]]
        return Quantity(v, "result", -1, feats, f"r{step}")

    # ---- learning from worked solutions ----------------------------------------------------------
    def train(self, examples, epochs=6, seed=0, log=None, cache=True):
        """examples: (text, steps) with steps = [(op, ref_a, ref_b)], refs ('N', k) | ('R', k) | ('C', value).

        cache=True keeps every example's gold path in RAM for all epochs (fast, needs ~4 GiB on the
        full training set); cache=False rebuilds it each epoch (slow, ~0.1 GiB) — same weights either
        way, since only *when* the ids are computed changes."""
        rng = np.random.default_rng(seed)
        order = np.arange(len(examples))
        paths = {}                              # example -> gold path: built once, reused every epoch
        count = 0                               # applied steps already inside the average
        drift = np.zeros(self.W.shape, dtype=np.float64)   # sum of update * (steps since it landed)
        for epoch in range(epochs):
            rng.shuffle(order)
            mistakes = 0
            for n in order:
                text, steps = examples[n]
                path = paths.get(n)
                if path is None:
                    path = self._gold_path(text, steps)
                    if cache:
                        paths[n] = path
                for indptr, data, gold_row, is_stop in path:
                    if gold_row is None:
                        break                  # the worked solution does something the reasoner can't
                    scores = np.add.reduceat(self.W[data], indptr[:-1])   # every candidate at once
                    best_row = int(np.argmax(scores))                     # first best, as the old loop did
                    if best_row != gold_row:
                        mistakes += 1
                        gold_ids = data[indptr[gold_row]:indptr[gold_row + 1]]
                        best_ids = data[indptr[best_row]:indptr[best_row + 1]]
                        np.add.at(self.W, gold_ids, 1.0)
                        np.add.at(self.W, best_ids, -1.0)
                        np.add.at(drift, gold_ids, count)
                        np.add.at(drift, best_ids, -count)
                    if is_stop:
                        break
                    count += 1
            if log:
                log(f"  epoch {epoch + 1}: {mistakes} wrong steps")
        # averaged perceptron without summing W after every step: the old `total += self.W` running sum
        # equals count * W - drift exactly (whole numbers throughout), so the average is the same
        total = (count * self.W.astype(np.float64) - drift).astype(np.float32)
        self.W = (total / max(count, 1)).astype(np.float32)                # steadier than the last W
        return self

    @staticmethod
    def _index(pool, ref, n_story):
        kind, k = ref
        if kind == "N":
            return k
        if kind == "C":
            return n_story + CONSTANTS.index(k)
        return n_story + len(CONSTANTS) + k

    # ---- reading a new problem -----------------------------------------------------------------
    def read(self, text, whole=None):
        """-> (plan text for the arithmetic region, steps as text) or None."""
        story, consts, qfeats = self._setup(text)
        if not story:
            return None
        whole = bool(re.search(r"\bhow many\b", text, re.I)) if whole is None else whole
        pool, used, shown = story + consts, set(), []
        for s in range(MAX_STEPS + 1):
            cands = sorted(self._cands(pool, used, qfeats, s), key=lambda cf: -self._score(cf[1]))
            if not cands:
                return None
            choice = cands[0][0]
            if choice == "STOP" or s == MAX_STEPS:
                break
            op, i, j = choice
            used.update((i, j))
            shown.append((op, pool[i], pool[j]))
            pool = pool + [self._apply(pool, op, i, j, s)]
        if not shown:
            return None
        answer = pool[-1].value
        if answer <= 0 or (whole and answer.denominator != 1):
            return None                                # number sense: that can't be the answer
        names = {}
        lines = []
        for k, (op, a, b) in enumerate(shown):
            ta = names.get(id(a), compose.fmt(a.value) if a.value >= 0 else f"({compose.fmt(a.value)})")
            tb = names.get(id(b), compose.fmt(b.value) if b.value >= 0 else f"({compose.fmt(b.value)})")
            name = f"r{k}"
            lines.append(f"{name} = {ta}{op}{tb}" if k < len(shown) - 1 else f"{ta}{op}{tb}")
        # results are referred to by name so the arithmetic region works each step out itself
        results = [q for q in pool if q.kind == "result"]
        lines, names = [], {}
        for k, (op, a, b) in enumerate(shown):
            ta = names.get(id(a), compose.fmt(a.value))
            tb = names.get(id(b), compose.fmt(b.value))
            expr = f"{ta}{op}{tb}"
            if k < len(shown) - 1:
                lines.append(f"r{k} = {expr}")
                names[id(results[k])] = f"r{k}"
            else:
                lines.append(expr)
        return "plan: " + "; ".join(lines)

    def save(self, folder):
        Path(folder).mkdir(parents=True, exist_ok=True)
        idx = np.nonzero(self.W)[0].astype(np.int32)
        np.savez_compressed(Path(folder) / "reasoner.npz", idx=idx, val=self.W[idx])

    @classmethod
    def load(cls, folder):
        p = Path(folder) / "reasoner.npz"
        if not p.exists():
            return None
        data = np.load(p)
        W = np.zeros(N_FEATURES, dtype=np.float32)
        W[data["idx"]] = data["val"]
        return cls(W)


# ---- turning worked solutions into steps ----------------------------------------------------------
def steps_from_expression(text, expression):
    """A worked expression (e.g. '(5*3)+2') -> steps over the story's quantities, or None."""
    _, story, _ = perceive(text)
    values = [q.value for q in story]
    try:
        tree = compose.parse(expression)
    except ValueError:
        return None
    steps, results = [], []

    def ref(v, used_story):
        for k, x in enumerate(values):
            if x == v and k not in used_story:
                used_story.add(k)
                return ("N", k)
        for k, x in enumerate(values):
            if x == v:
                return ("N", k)
        if v in CONSTANTS:
            return ("C", v)
        return None

    used = set()

    def walk(t):
        if isinstance(t, Fraction):
            return ("val", t)
        if t[0] == "neg" or t[0] not in OPS:
            raise ValueError
        a, b = walk(t[1]), walk(t[2])
        ra = a[1] if a[0] == "res" else ref(a[1], used)
        rb = b[1] if b[0] == "res" else ref(b[1], used)
        if ra is None or rb is None:
            raise ValueError
        steps.append((t[0], ra, rb))
        results.append(None)
        return ("res", ("R", len(steps) - 1))
    try:
        top = walk(tree)
    except (ValueError, IndexError):
        return None
    return steps if top[0] == "res" else None


def steps_from_gsm8k(question, solution):
    """GSM8K's <<48/2=24>> annotations -> steps, mapping each number to a story number, an earlier
    result, or a constant. None if a step can't be explained that way."""
    _, story, _ = perceive(question)
    story_vals = [q.value for q in story]
    steps, result_vals = [], []
    for expr, res in re.findall(r"<<([^=<>]+)=([^<>]+)>>", solution):
        expr = expr.replace(",", "").replace("$", "")
        try:
            tree = compose.parse(expr)
            target = Fraction(res.replace(",", "").replace("$", ""))
        except (ValueError, ZeroDivisionError):
            return None

        def ref(v):
            for k in range(len(result_vals) - 1, -1, -1):
                if result_vals[k] == v:
                    return ("R", k)
            for k, x in enumerate(story_vals):
                if x == v:
                    return ("N", k)
            if v in CONSTANTS:
                return ("C", v)
            return None

        def walk(t):
            if isinstance(t, Fraction):
                r = ref(t)
                if r is None:
                    raise ValueError
                return r, t
            if t[0] == "neg" or t[0] not in OPS:
                raise ValueError
            (ra, va), (rb, vb) = walk(t[1]), walk(t[2])
            v = va + vb if t[0] == "+" else va - vb if t[0] == "-" else va * vb if t[0] == "*" else va / vb
            steps.append((t[0], ra, rb))
            result_vals.append(v)
            return ("R", len(steps) - 1), v
        try:
            if isinstance(tree, Fraction):
                return None
            _, v = walk(tree)
        except (ValueError, ZeroDivisionError):
            return None
        if v != target:
            return None
    final = solution.split("####")[-1].strip().replace(",", "")
    try:
        if not result_vals or result_vals[-1] != Fraction(final):
            return None
    except (ValueError, ZeroDivisionError):
        return None
    return steps
