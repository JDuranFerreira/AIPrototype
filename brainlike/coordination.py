"""The coordination region (like the basal ganglia and the premotor cortex of this brain): the TOOLS.

A tool is one worked procedure for DOING something — count up in groups, work out a percent,
find the greatest common factor. The language region reads the story, the arithmetic region
knows its facts; when a story needs work done, the tools live here, and here is decided
where each one may be used. Nothing else in the brain keeps a procedure of its own.

What the region holds:
  tools     the procedures themselves (group_steps, percent_steps, gcd_steps, lcm_steps,
            unitary_steps): what it CAN do, taught or not
  rules     the tools the teacher taught it to trust ("groups of" -> & % ^), each kept with
            the worked examples that earned that trust (Reading.learn_rule / learn_op)
  CUES      where a tool may be used: the words that license it ("percent" -> !); tools
            with no gate (the whole-group ones) may be used wherever it was taught
  stats     how well each tool has paid off: tried / right / steps, from the teacher's ✓/✗
  strategy  the strategy chooser (guess or work it out) — which WAY to answer at all

The reading engine asks this region which tools a clause may use (Frames.ops_for), credits
its lessons back into it, and exam/lesson outcomes can add a reward.

The brain LEARNS where a tool applies: on top of the hand cue list, `cues_for` takes the
words the tool was TAUGHT with ('area of a square' -> square), so a story that says
'square' gets the square tool even where nobody wrote that word into a list.
"""
import re
from fractions import Fraction

from .compose import fmt
from .request import asks_matches, not_about_matches, what_is_asked
from .strategy import Strategy

_WORD = re.compile(r"[a-z]+")
# Words too generic to license a tool on their own: a taught phrase is mostly grammar.
_STOP = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "has", "have", "all", "any", "its",
         "into", "your", "when", "then", "than", "what", "find", "first", "many", "some", "more", "will", "them",
         "they", "she", "him", "his", "her", "our", "who", "why", "how"}

# The words that license a gated tool. Ops with no entry here (the whole-group tools
# &, %, ^) may be used wherever they were taught.
CUES = {"u": {"cost", "costs", "do", "does", "make", "makes", "hours", "days", "take", "takes", "use", "uses",
               "need", "needs"},
        "q": {"area"}, "!": {"percent"}, "#": {"greatest", "largest", "biggest", "most", "common"},
        "$": {"again", "least", "smallest", "both", "same"}}

# Every tool the region has, with what it does (taught or not).
TOOLS = {"&": "full groups", "%": "left over", "^": "groups needed", "!": "percent of",
         "q": "area of a square", "#": "greatest common factor", "$": "least common multiple",
         "u": "unitary method"}

# The tools for arithmetic and for the first algorithms: taught with worked examples before they are
# used, checked against the teacher's numbers with the brain's own procedure (the P5-P6 pattern).
ARITH_TOOLS = {"%": "what is left over", "^": "the power of a number", "c": "which number is bigger",
               "s": "put numbers in order", "n": "count on by ones"}


# ---- the tools themselves (moved here from storyreader: they are the region's abilities) ----------

def group_steps(a, b):
    """How it finds whole groups, step by step, the way it was taught: count up in b's while that is short, or long
    division digit by digit for big numbers. -> (full groups, left over, the working in words)"""
    a, b = int(a), int(b)
    q, r = divmod(a, b)
    if q <= 12:
        counts = ", ".join(str(b * k) for k in range(1, q + 1)) or "0"
        work = f"count in {b}s: {counts}; {b * (q + 1)} is more than {a}"
    else:
        parts, rest, digits = [], 0, str(a)
        for d in digits:
            rest = rest * 10 + int(d)
            if rest >= b or parts:
                parts.append(f"{rest}\u00f7{b} = {rest // b} r {rest % b}")
            rest %= b
        work = "long division: " + ", ".join(parts)
    return q, r, f"{work}; {q} full groups, {a} \u2212 {b * q} = {r} left over"


def factors(n):
    return [k for k in range(1, n + 1) if n % k == 0]
def gcd_steps(a, b):
    """The greatest common factor the way it was taught: list the factors of both (small numbers), or keep taking the
    smaller from the bigger's remainder (Euclid) for big ones."""
    a, b = int(a), int(b)
    if max(a, b) <= 100:
        fa, fb = factors(a), factors(b)
        both = [k for k in fa if k in fb]
        return both[-1], (f"factors of {a}: {', '.join(map(str, fa))}; of {b}: {', '.join(map(str, fb))}; "
                          f"in both: {', '.join(map(str, both))}; the greatest is {both[-1]}")
    x, y, steps = max(a, b), min(a, b), []
    while y:
        steps.append(f"{x} = {x // y}\u00d7{y} + {x % y}")
        x, y = y, x % y
    return x, "Euclid: " + "; ".join(steps) + f"; the greatest common factor is {x}"


def lcm_steps(a, b):
    """The least common multiple the way it was taught: count up in the bigger one until the smaller fits."""
    a, b = int(a), int(b)
    big, small = max(a, b), min(a, b)
    k, seen = 1, []
    while (big * k) % small:
        seen.append(str(big * k))
        k += 1
    seen.append(str(big * k))
    shown = seen if len(seen) <= 12 else seen[:3] + ["\u2026"] + seen[-2:]
    return big * k, f"multiples of {big}: {', '.join(shown)}; {big * k} is the first that {small} also goes into"


def dec(v):
    """A number as a child writes it: 4.5, not 9/2 (when it ends)."""
    from .storyreader import fmt                     # lazy: storyreader imports this module at load time
    v = Fraction(v)
    for places in range(0, 4):
        if (v * 10 ** places).denominator == 1:
            return f"{float(v):.{places}f}" if places else str(v.numerator)
    return fmt(v)


def percent_steps(p, b):
    v = Fraction(b) * Fraction(p) / 100
    return v, f"{dec(p)}% of {dec(b)}: {dec(b)} \u00f7 100 = {dec(Fraction(b) / 100)}, \u00d7 {dec(p)} = {dec(v)}"


def unitary_steps(total, count, many):
    one = Fraction(total) / Fraction(count)
    return one * Fraction(many), (f"first one: {dec(total)} \u00f7 {dec(count)} = {dec(one)}; then {dec(many)}: "
                                  f"{dec(one)} \u00d7 {dec(many)} = {dec(one * Fraction(many))}")


def rem_steps(a, b):
    """What is left over after sharing a into groups of b, the way it was taught: take b away again and
    again while it fits. -> (left over, the working in words)"""
    a, b = int(a), int(b)
    if b <= 0:
        raise ValueError("you can't share into groups of nothing")
    left, counts = a, []
    while left >= b:
        counts.append(str(left))
        left -= b
    work = f"count in {b}s: {', '.join(counts) or '0'}; {left} is less than {b}"
    return left, f"{work}; {a} \u2212 {b}\u00d7{a // b} = {left} left over"


def power_steps(a, b):
    """The power of a number, the way it was taught: multiply by the number again, once for every time.
    -> (the value, the working in words)"""
    a, b = int(a), int(b)
    if b < 0:
        raise ValueError("I only know powers that many times, like 2 to the 10")
    if b > 100:
        raise ValueError("that's too big a power for me")
    v, steps = 1, []
    for i in range(b):
        v *= a
        steps.append(f"{a} \u00d7 {a} = {a * a}" if i == 0 else f"{v // a} \u00d7 {a} = {v}")
    shown = steps[:6] + (["\u2026"] if len(steps) > 8 else []) + steps[-2:] if len(steps) > 6 else steps
    return v, f"multiply by {a} again and again: {', '.join(shown)}; {a} to the power {b} = {v}"


def count_steps(a, b, step=1):
    """Count on from a to b, the way it was taught: say the number after the last one, over and over,
    until b. -> (the numbers said, the working in words)"""
    a, b, step = int(a), int(b), max(1, int(step))
    if b < a or b - a > 60:
        raise ValueError("that's too long for me to count on")
    out = [str(v) for v in range(a, b + 1, step)]
    return ", ".join(out), f"count on from {a} in {step}s: {', '.join(out)}; that ends at {out[-1]}"


def compare_steps(a, b):
    """Which number is bigger, the way it was taught: take the smaller away from the bigger and see what
    is left. -> ('<' '=' or '>', the working in words)"""
    a, b = Fraction(a), Fraction(b)
    if a == b:
        return "=", f"{fmt(a)} and {fmt(b)}: take one from the other and 0 is left, so they are the same number"
    big, small = (a, b) if a > b else (b, a)
    return (">" if a > b else "<"), (f"{fmt(a)} and {fmt(b)}: {fmt(big)} \u2212 {fmt(small)} = "
                                    f"{fmt(big - small)} is left, so {fmt(big)} is the bigger")


def sort_steps(numbers):
    """Put numbers in order, the way it was taught: find the smallest one that is left, say it, cross it
    out, and do it again. -> (the numbers in order, the working in words)"""
    left = [Fraction(n) for n in numbers]
    out, steps = [], []
    while left:
        small = min(left)
        out.append(fmt(small))
        steps.append(f"smallest left is {fmt(small)}")
        left.remove(small)
    return ", ".join(out), f"{'; '.join(steps)}; in order: {', '.join(out)}"


ARITH_STEPS = {"%": rem_steps, "^": power_steps, "c": compare_steps, "s": sort_steps, "n": count_steps}


def _same_plan(a, b):
    """Same plan up to spacing (a child is not fussy about '42 - 2' vs '42-2')."""
    return re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b)


def _matches(v, told):
    """Does what the tool found match the teacher's answer? (numbers exactly, anything else as text)"""
    try:
        return Fraction(v) == Fraction(told)
    except (ValueError, TypeError):
        return str(v).strip().replace(" ", "") == str(told).strip().replace(" ", "")


def _check(op, args, v):
    """Undo what the tool did, a different way round: -> (ok?, the check in words)."""
    if op == "%":
        a, b, left = Fraction(args[0]), Fraction(args[1]), Fraction(v)
        q = (a - left) // b
        ok = left + b * q == a
        return ok, f"check: {fmt(left)} + {fmt(b)} \u00d7 {fmt(q)} = {fmt(left + b * q)} " + ("\u2713" if ok else "\u2717")
    if op == "^":
        a, back = Fraction(args[0]), Fraction(v)
        for _ in range(int(args[1])):
            back = back // a
        ok = back == 1
        return ok, (f"check: take {fmt(a)} away {fmt(args[1])} times and you land on {fmt(back)} "
                    + ("\u2713" if ok else "\u2717"))
    if op == "c":
        a, b = Fraction(args[0]), Fraction(args[1])
        if a == b:
            return True, f"check: {fmt(a)} \u2212 {fmt(b)} = 0, nothing left, so they are the same \u2713"
        big, small = (a, b) if a > b else (b, a)
        ok = big - small == big - small and (big - (big - small)) == small
        return ok, f"check: {fmt(big)} \u2212 {fmt(big - small)} = {fmt(small)} the other way round \u2713"
    if op == "s":
        got = [Fraction(x.strip()) for x in str(v).split(",")]
        nums = [Fraction(n) for n in args[0]]
        ok = sorted(got) == sorted(nums) and all(got[i] <= got[i + 1] for i in range(len(got) - 1))
        return ok, (f"check: in order and all {len(nums)} numbers still there: {', '.join(fmt(x) for x in got)} "
                    + ("\u2713" if ok else "\u2717"))
    if op == "n":
        last = str(v).split(",")[-1].strip()
        ok = int(last) == int(args[1])
        return ok, f"check: it ends at {last}, and that is {int(args[1])} " + ("\u2713" if ok else "\u2717")
    return True, ""


_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?")


def _number_for_word(sentence, word):
    """The number that counts this word: "14 boxes" -> 14 for "boxes", "gives away 9 pencils" -> 9 for
    "gives away", "Kim eats 7 apples" -> 7 for "eats". A role may name several words for the same step
    ("{away|eats|breaks}"), because the teacher knows the step, not the verb that will be used."""
    s = sentence.lower()
    words = [re.escape(w.strip()) for w in word.split("|") if w.strip()]
    if not words:
        return None
    any_of = "(?:" + "|".join(words) + ")"
    m = re.search(r"(-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?)\s+" + any_of + r"\b", s)   # "14 boxes"
    if m:
        return m.group(1).replace(" ", "")
    m = re.search(any_of + r"\b[^.;?]{0,30}?(-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?)", s)  # "gives away 10 pens"
    return m.group(1).replace(" ", "") if m else None


def _fill(plan, sentence):
    """Put the sentence's numbers into the plan's holes: {n1} {n2} … take them in the order they appear,
    {boxes} / {away|eats} take the number that counts that word, which is what makes a recipe about
    meaning rather than about order."""
    numbers = [n.replace(" ", "") for n in _NUMBER.findall(sentence)]

    def put(m):                                        # one pass, so {n2} before {n1} still means the 2nd number
        i = int(m.group(1)) - 1
        return numbers[i] if i < len(numbers) else m.group(0)

    def put_word(m):                                   # a named role: which number is this one?
        return _number_for_word(sentence, m.group(1)) or m.group(0)

    plan = re.sub(r"\{n(\d+)\}", put, plan)
    plan = re.sub(r"\{([a-z][a-z_| ]*)\}", put_word, plan)
    return None if "{" in plan else plan


class Coordination:
    def __init__(self, data=None, strategy=None):
        d = data or {}
        self.rules = dict(d.get("rules") or {})      # op -> {rule, phrase, examples}: the taught tools
        self.stats = dict(d.get("stats") or {})      # op -> {tries, right, steps}: how each tool pays off
        self.arithmetic = dict(d.get("arithmetic") or {})  # taught arithmetic tools: "%"/"^" -> {rule, examples}
        self.procedures = dict(d.get("procedures") or {})  # named recipes: word pattern -> the plan to write
        self.strategy = strategy if strategy is not None else Strategy(d.get("strategy") or None)
        self._cues = {}                         # op -> (phrase, words) memoised from the taught rule

    # ---- procedures: a sentence in words -> the plan it should run -------------------------

    def teach_procedure(self, name, said, pattern, plan, examples, asks=None, not_about=None):
        """The teacher shows (a sentence, the plan it should write) pairs; the brain fills its own
        pattern and keeps the recipe only if it writes the teacher's plan every time.
        `asks` is what the recipe answers ("needed", "each", "all"), so a recipe never answers a question
        it was not taught to answer; `not_about` is what it does not count ("boxes", "red"), so it knows
        that "how many boxes are there?" is not its question.
        examples: [(sentence, plan)] -> (kept?, what it wrote for each example)."""
        self.procedures[name] = {"said": said or name, "pattern": pattern, "plan": plan, "examples": 0}
        if asks:
            self.procedures[name]["asks"] = asks
        if not_about:
            self.procedures[name]["not_about"] = not_about
        ok, work = True, []
        for sentence, told in examples:
            found = self.run_procedure(name, sentence)
            got = found[1] if found else None
            same = got is not None and _same_plan(got, told)
            work.append({"sentence": sentence, "its_plan": got or "it didn't match", "your_plan": told,
                         "matched": same})
            ok = ok and same
        if ok:
            self.procedures[name]["examples"] = len(examples)
        else:
            self.procedures.pop(name, None)
        s = self.stats.setdefault(f"procedure {name}", {"tries": 0, "right": 0, "steps": 0})
        s["tries"] += len(examples)
        s["right"] += sum(w["matched"] for w in work)
        s["steps"] += len(examples)
        return ok, work

    def run_procedure(self, name, sentence):
        """The plan this recipe writes for a sentence, or None when it doesn't match. -> (name, plan)"""
        p = self.procedures.get(name)
        if not p or not re.search(p["pattern"], sentence, re.I):
            return None
        asked = what_is_asked(sentence)
        if not asks_matches(p, asked)[0] or not not_about_matches(p, asked)[0]:
            return None
        plan = _fill(p["plan"], sentence)
        return (name, plan) if plan else None

    def why_not(self, name, sentence):
        """Why a taught recipe stayed quiet on this sentence (empty when it does fit) -> the reason in words."""
        p = self.procedures.get(name)
        if not p:
            return "it has not been taught"
        if not re.search(p["pattern"], sentence, re.I):
            return ""
        asked = what_is_asked(sentence)
        ok, why = asks_matches(p, asked)
        return "" if ok else why

    def what_is_asked(self, sentence):
        """The request this sentence makes, in plain words (the reading region's answer, or unknown)."""
        return what_is_asked(sentence)

    def plans_for(self, sentence):
        """Every taught recipe that fits this sentence -> [(name, plan)], most numbers first."""
        out = [self.run_procedure(n, sentence) for n in self.procedures]
        out = [p for p in out if p]
        return sorted(out, key=lambda p: (-_NUMBER.findall(p[1]).__len__(), p[0]))

    # ---- the arithmetic tools (taught before use, like the P5-P6 ones) -----------------

    def arith_taught(self, op):
        """Has the teacher shown it how to use this arithmetic tool?"""
        return op in self.arithmetic

    def teach_arithmetic(self, op, examples, said=None):
        """The teacher shows worked examples ('17 % 5 = 2'); the brain works each one out with its own
        procedure and keeps the tool only if it finds the teacher's number every time.
        examples: [(args..., told)] -> (kept?, its working for each example)."""
        work, ok = [], True
        for told_pair in examples:
            args, told = told_pair
            try:
                v, mine = ARITH_STEPS[op](*args)
            except (ValueError, ZeroDivisionError) as e:
                work.append(f"I couldn't work that one out: {e}")
                self.reward(op, False)
                return False, work
            work.append(mine)
            ok = ok and _matches(v, told)
        if ok:
            self.arithmetic[op] = {"rule": said or ARITH_TOOLS[op], "examples": len(examples)}
        self.reward(op, ok, steps=len(examples))
        return ok, work

    def arith_work(self, op, args):
        """-> (value, working, check by undoing it) from the tool's own procedure."""
        v, work = ARITH_STEPS[op](*args)
        _, check = _check(op, args, v)
        return v, work, check

    def check_story(self, op, a, b, got):
        """Work a story explanation out again with the tool's own procedure, a different way round than
        the explanation itself. -> (ok?, the check in words) or None if this tool has no second route."""
        a, b = Fraction(a), Fraction(b)
        try:
            if op == "%":
                v, _ = rem_steps(a, b)
            elif op == "&":
                v, left = 0, a
                while left >= b:
                    left -= b
                    v += 1
            elif op == "^":
                v = (a + b - 1) // b if a.denominator == b.denominator == 1 and b > 0 else None
            elif op == "!":
                v = a * b / 100
            elif op in "#$":
                big, small = max(a, b), min(a, b)
                x, y = big, small
                while y:
                    x, y = y, x % y
                v = x if op == "#" else (a // x * b if x else None)
            else:
                return None
        except (ValueError, ZeroDivisionError):
            return None
        if v is None:
            return None
        ok = Fraction(v) == Fraction(got)
        return ok, f"the {TOOLS.get(op, op)} tool says {fmt(v)} " + ("\u2713" if ok else "\u2717")

    def allowed(self, words):
        """Which tools this clause may use: taught tools with no word gate anywhere the story asks;
        gated tools where their cue words are — the hand list plus what the tool was taught with."""
        out = []
        for op in self.rules:
            gate = CUES.get(op)
            if gate is None or (gate | self.cues_for(op)) & words:
                out.append(op)
        return "".join(out)

    def cues_for(self, op):
        """The cue words a tool earned from the phrase it was taught with ('area of a square' ->
        {area, square}), so a story that says 'square' gets the square tool even where the
        hand list is thin. -> frozenset (memoised per phrase)."""
        said = self.rules.get(op, {}).get("phrase") or ""
        got = self._cues.get(op)
        if got is None or got[0] != said:
            got = (said, frozenset(w for w in _WORD.findall(said.lower()) if len(w) >= 3 and w not in _STOP))
            self._cues[op] = got
        return got[1]

    def learned_cues(self):
        """What the teaching added over the hand cue list: {op: [words]} for gated tools only."""
        return {op: sorted(self.cues_for(op) - CUES[op]) for op in self.rules
                if op in CUES and self.cues_for(op) - CUES[op]}

    def reward(self, op, correct, steps=1):
        """The teacher's \u2713/\u2717 on work done with this tool: the region learns which tools pay off.
        The arithmetic tools keep their own tally ('arith %'), so they never mix with the story tools."""
        op = f"arith {op}" if op in ARITH_STEPS else op
        s = self.stats.setdefault(op, {"tries": 0, "right": 0, "steps": 0})
        s["tries"] += 1
        s["right"] += int(bool(correct))
        s["steps"] += steps

    def summary(self):
        """Per-tool rewards for the report (regions())."""
        return [{"tool": op, "name": (ARITH_TOOLS if op.startswith("arith ") else TOOLS).get(
                     op.split()[-1], op), "taught": op.split()[-1] in (self.arithmetic if op.startswith("arith ")
                                                                          else self.rules),
                 "tries": s["tries"], "right": s["right"],
                 "avg_steps": round(s["steps"] / s["tries"], 1) if s["tries"] else 0}
                for op, s in sorted(self.stats.items())]

    def take_over(self, other):
        """Another store's taught tools and rewards end up here (the incoming engine's win: Frames.bind)."""
        self.rules.update(other.rules)
        self.stats.update(other.stats)
        if other.strategy.stats and not self.strategy.stats:
            self.strategy = other.strategy

    def state(self):
        return {"rules": self.rules, "stats": self.stats, "arithmetic": self.arithmetic,
                "procedures": self.procedures, "strategy": self.strategy.stats}


