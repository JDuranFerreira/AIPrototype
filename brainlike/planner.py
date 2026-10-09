"""The prefrontal region: a planner and a working memory.

Planner
  A problem with several steps ("I have 3 bags of 4 apples, eat 2, and share
  the rest between 5 friends") becomes a plan, written in the brain's own
  language, one step per line:

      plan: apples = 3*4; left = apples-2; left/5

  The language region writes the plan from your sentence (or you type one).
  The planner runs it step by step, sending each step to the arithmetic
  region, and keeps the results in working memory so later steps can use them.

Working memory
  A small short-term store: the last answer ("last", "that", "it") and the
  names from the last plan, so you can follow up with "now add 5 to that".
  It forgets: only the latest few values are kept.
"""
import re
from fractions import Fraction

from . import compose

PREFIX = re.compile(r"^\s*plan\s*:\s*", re.I)
_NAME = re.compile(r"(?<![\w.])([a-z_][a-z_0-9]*)(?![\w(])", re.I)
CAPACITY = 7               # how many named values working memory holds (people manage about 7)
_PRONOUNS = {"that": "last", "it": "last", "this": "last", "result": "last", "answer": "last"}
RESERVED = {"x"}          # x means times in this brain, so it can't be a name in a plan
_IF = re.compile(r"^\s*if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$", re.I)
_FOR = re.compile(r"^\s*for\s+([a-z_][a-z_0-9]*)\s+from\s+(-?\d+)\s+to\s+(-?\d+)\s+do\s+(.+)$", re.I)
_CMP = re.compile(r"^\s*(-?[\d.]+(?:/\d+)?)\s*(<=|>=|<|>|=)\s*(-?[\d.]+(?:/\d+)?)\s*$")


def is_plan(text):
    return bool(PREFIX.match(text))


class WorkingMemory:
    def __init__(self, data=None):
        data = data or {}
        self.values = dict(data.get("values", {}))     # "apples" -> "12", "last" -> "2"
        self.order = list(data.get("order", []))       # oldest first, for forgetting

    def put(self, name, value):
        name = name.lower()
        self.values[name] = compose.fmt(value)
        if name in self.order:
            self.order.remove(name)
        self.order.append(name)
        while len(self.order) > CAPACITY:
            old = self.order.pop(0)
            if old != "last":
                self.values.pop(old, None)

    def describe(self):
        return ", ".join(f"{k} = {v}" for k, v in self.values.items()) or "empty"

    def state(self):
        return {"values": self.values, "order": self.order}

    def clear(self):
        self.values.clear()
        self.order.clear()


class Doubts:
    """The prefrontal region's doubt and checking (the part that asks "are you sure?" before saying so).
    It remembers what made it doubtful (which words led a story to a wrong answer), the teacher clears
    those words when the answer turns out right, and every check it makes is counted."""
    KEEP = 12                      # how many recent doubts it keeps
    AT_LEAST = 6                   # how often a word must have led it wrong before it is doubted
    MAX_WORD = 8                   # a counter stops here: doubt is doubt, 485 is no more doubt than 8
    MAX_WORDS = 500                # the memory keeps the words with the most evidence, nothing more

    def __init__(self, data=None):
        d = data or {}
        self.words = dict(d.get("words", {}))     # word -> how often an answer that used it came out wrong
        self.last = list(d.get("last", []))       # the latest doubts, newest first
        self.checks = dict(d.get("checks", {}))   # kind -> {"checked": n, "passed": n}
        self._bound()

    def _bound(self):
        """The memory is finite: a counter cannot run away past MAX_WORD, and only the words with the
        most evidence are kept (a word that led it wrong 6 times since it last led it right)."""
        for w in list(self.words):
            if self.words[w] > self.MAX_WORD:
                self.words[w] = self.MAX_WORD
        if len(self.words) > self.MAX_WORDS:
            keep = sorted(self.words, key=lambda w: (-self.words[w], w))[:self.MAX_WORDS]
            self.words = {w: self.words[w] for w in keep}

    def doubt(self, kind, text, words=()):
        for w in words:
            self.words[w] = min(self.words.get(w, 0) + 1, self.MAX_WORD)
        self._bound()
        self.last.insert(0, {"kind": kind, "text": text})
        del self.last[self.KEEP:]
        c = self.checks.setdefault(kind, {"checked": 0, "passed": 0})
        c["checked"] += 1

    def confirmed(self, words=()):
        """The teacher agrees with the answer: those words were not the problem."""
        for w in words:
            self.words.pop(w, None)

    def doubted(self, word, at_least=None):
        return self.words.get(word, 0) >= (self.AT_LEAST if at_least is None else at_least)

    def passed(self, kind, n=1):
        self.checks.setdefault(kind, {"checked": 0, "passed": 0})["passed"] += n

    def state(self):
        return {"words": self.words, "last": self.last, "checks": self.checks}

    def clear(self):
        self.words.clear()
        self.last.clear()
        self.checks.clear()

    def summary(self):
        return {"words": len(self.words), "doubts": sum(self.words.values()),
                "checks": sum(c["checked"] for c in self.checks.values()),
                "last": self.last[:5]}


def parse(text):
    """A plan is a list of steps:
    'plan: a = 3*4; if a > 6 then a-1 else a+1; for i from 1 to 3 do a+1'
    -> [("=", "a", "3*4"), ("if", "a > 6", "a-1", "a+1"), ("for", "i", "1", "3", "a+1")]."""
    body = PREFIX.sub("", text)
    steps = []
    for part in re.split(r"[;\n]", body):
        part = part.strip()
        if not part:
            continue
        m = _IF.match(part)
        if m:
            steps.append(("if", m.group(1).strip(), m.group(2).strip(),
                          m.group(3).strip() if m.group(3) else None))
            continue
        m = _FOR.match(part)
        if m:
            steps.append(("for", m.group(1).lower(), m.group(2), m.group(3), m.group(4).strip()))
            continue
        m = re.match(r"^([a-z_][a-z_0-9]*)\s*=\s*(.+)$", part, re.I)
        if not m:
            steps.append(("=", None, part))
            continue
        name = m.group(1).lower()
        if name in RESERVED:      # x is the times sign here: say so plainly instead of breaking further on
            raise ValueError(f"'{name}' means times in this brain, so give the plan another name, "
                             f"like: plan: total = 3*4; total-2")
        steps.append(("=", name, m.group(2).strip()))
    if not steps:
        raise ValueError("a plan needs at least one step, like: plan: a = 3*4; a-2")
    return steps


def fill(expression, values):
    """Put the values of names into a step: 'apples-2' with apples = 12 -> '12-2'."""
    def swap(m):
        word = m.group(1).lower()
        if word == "x" or word in compose.SPACED_OPS:   # x means times; div / rem / divup are operations
            return m.group(1)
        word = _PRONOUNS.get(word, word)
        if word not in values:
            raise ValueError(f"I don't know what '{m.group(1)}' is in this plan")
        v = compose.to_value(values[word])
        return compose.fmt(v) if v >= 0 and v.denominator == 1 else f"({compose.fmt(v)})"
    return _NAME.sub(swap, expression)


def run(text, memory, solve, compare=None, count=None):
    """Run a plan. `solve(problem)` asks the arithmetic region and returns its reply
    (answer, steps, source, ...). `compare(a, b, sign)` is the taught compare tool (an `if` needs it),
    `count()` says it may count on (a `for` needs it). -> (final answer, list of plan steps)."""
    values = dict(memory.values)
    done = []

    def take(expression, name=None, kind="step"):
        filled = fill(expression, values)
        try:
            problem = compose.normalize(filled)
        except ValueError:
            value = compose.to_value(filled)          # a plain number: it is told, not worked out
            values["last"] = compose.fmt(value)
            if name:
                values[name] = compose.fmt(value)
            done.append({"name": name, "expression": expression, "problem": filled,
                         "answer": compose.fmt(value), "how": {"source": "told"}, "kind": kind})
            return value
        reply = solve(problem)
        answer = Fraction(compose.to_value(reply["answer"]))
        values["last"] = compose.fmt(answer)
        if name:
            values[name] = compose.fmt(answer)
        done.append({"name": name, "expression": expression, "problem": problem,
                     "answer": compose.fmt(answer), "how": reply, "kind": kind})
        return answer

    def execute(steps, depth=0):
        """Run a list of steps; a branch or a loop body is itself a list of steps (nested plans)."""
        if depth > 4:
            raise ValueError("that's nested too deep for me (four levels at the most)")
        for step in steps:
            if step[0] == "if":
                ask = fill(step[1], values)
                m = _CMP.match(ask)
                if not m:
                    raise ValueError(f"an if can only test a comparison, like 'if {step[1]} > 3 then ...'")
                if compare is None:
                    raise ValueError("I haven't been taught how to compare numbers yet: show me a worked example")
                yes, check = compare(compose.to_value(m.group(1)), compose.to_value(m.group(3)), m.group(2))
                done.append({"name": None, "expression": step[1], "problem": ask, "answer": "yes" if yes else "no",
                             "how": {"source": "compare"}, "kind": "condition", "checked": check})
                execute(parse(step[2] if yes else (step[3] or step[2])), depth + 1)
            elif step[0] == "for":
                var, first, last, body = step[1], int(step[2]), int(step[3]), step[4]
                if count is None:
                    raise ValueError("I haven't been taught to count on yet: show me a worked example")
                if last - first > 50:
                    raise ValueError("that's too many times round the loop for me (50 at the most)")
                for i in range(first, last + 1):
                    values[var] = str(i)
                    done.append({"name": var, "expression": f"{var} = {i}", "problem": str(i), "answer": str(i),
                                 "how": {"source": "loop"}, "kind": "loop"})
                    execute(parse(body), depth + 1)
            else:
                take(step[2], step[1])

    execute(parse(text))
    for step in done:
        if step["name"]:
            memory.put(step["name"], step["answer"])
    answered = [s for s in done if s["kind"] not in ("condition", "loop")] or done
    memory.put("last", answered[-1]["answer"])
    return answered[-1]["answer"], done
