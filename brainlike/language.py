"""The language region: works out what the teacher MEANS, and says it in the
brain's own language (7*8, n/n = 1, capital of spain = Madrid).

It never calculates; it only translates. Answers always come from the
arithmetic region (math) or the knowledge region (facts).

How it understands a sentence, in order:
  1. phrases it has learned from the teacher ("seven times eight" -> 7*8)
  2. phrase patterns with numbers in them, learned from those phrases
     ("what is 3 plus 5" teaches "what is {0} plus {1}" -> {0}+{1})
  3. its own READER (reader.py): a small classifier, trained on worked
     examples, that recognises the kind of word problem (schema) and which
     numbers go where. No language model; it runs on the CPU in a millisecond.
  4. only if one is configured: a local language model (Ollama) as a helper.
     It is OFF by default (model None): the brain then relies on 1-3 alone.
"""
import json
import re
import urllib.request

from . import compose, rules

COMMANDS = {"sleep", "exam", "stats", "rules", "find patterns"}

PROMPT = """You are the language area of a small learning brain. Translate the teacher's message into what they MEAN, as JSON. NEVER calculate or answer anything yourself.

Reply with exactly one JSON object, one of:
{"intent": "calculate", "expression": "<math using numbers + - * / ( ) div rem divup>"}     one step
    whole-number division words: "a div b" = how many WHOLE times b fits in a (full boxes, full teams),
    "a rem b" = what is left over, "a divup b" = how many are NEEDED so that nothing is left (boxes needed, trips needed)
    div, rem and divup are ONLY for counting whole groups of things. Money stays in dollars as decimals
    ($4.35 is 4.35); never change dollars into cents unless the question asks for cents.
{"intent": "plan", "steps": [{"name": "<word>", "expression": "<math>"}, ..., {"expression": "<math, the final answer>"}]}
                                         several steps: later steps may use the names of earlier ones
{"intent": "teach_rule", "rule": "<left> = <right>"}           letters stand for any number, e.g. n/n = 1, a*1 = a, a*b = b*a
{"intent": "teach_fact", "question": "<short question, lower case>", "answer": "<the teacher's answer>"}
{"intent": "ask_fact", "question": "<short question, lower case>"}
{"intent": "practice", "problems": ["<math>", "<math>", "<math>"]}   when the teacher wants it to try some problems; invent 3 to 5 that fit
{"intent": "command", "command": "sleep" | "exam" | "stats" | "rules" | "find patterns"}
{"intent": "need_fact", "question": "<the fact it would need, lower case, e.g. cents in a dollar>"}
{"intent": "unknown"}

Facts the brain knows are listed with each message ("known facts"). A calculation may only use numbers that
are written in the message or listed as known facts. If it needs a fact that is NOT listed (how many cents
are in a dollar, minutes in an hour, centimetres in a metre ...), do not use your own knowledge: reply
{"intent": "need_fact", "question": "..."} instead. If a known fact IS the answer, reply ask_fact with that
fact's question (never teach_fact: the teacher is asking, not teaching).

Examples:
"any number divided by the same number is 1" -> {"intent": "teach_rule", "rule": "n/n = 1"}
"rules n*(-1) = -n" -> {"intent": "teach_rule", "rule": "n*(-1) = -n"}
"multiplying is adding the same number again and again" -> {"intent": "teach_rule", "rule": "a*b = a*(b-1)+a"}
"what is seven times eight" -> {"intent": "calculate", "expression": "7*8"}
"I have 3 apples and buy 5 more. How many apples do I have?" -> {"intent": "calculate", "expression": "3+5"}
"a box has 12 eggs, how many eggs in 4 boxes" -> {"intent": "calculate", "expression": "12*4"}
"I have 3 bags of 4 apples, I eat 2 and share the rest between 5 friends. How many does each get?" -> {"intent": "plan", "steps": [{"name": "apples", "expression": "3*4"}, {"name": "left", "expression": "apples-2"}, {"expression": "left/5"}]}
"now add 5 to that" (working memory: last = 2) -> {"intent": "calculate", "expression": "last+5"}
"double the apples" (working memory: apples = 12) -> {"intent": "calculate", "expression": "apples*2"}
"try some divisions with the same numbers" -> {"intent": "practice", "problems": ["6/6", "25/25", "144/144", "9/9"]}
"the capital of Spain is Madrid" -> {"intent": "teach_fact", "question": "capital of spain", "answer": "Madrid"}
"what's the capital of Spain?" -> {"intent": "ask_fact", "question": "capital of spain"}
"time to sleep" -> {"intent": "command", "command": "sleep"}
"look for patterns" -> {"intent": "command", "command": "find patterns"}
"A farmer packs 245 eggs into boxes of 12. How many boxes can he fill completely?" -> {"intent": "calculate", "expression": "245 div 12"}
"Each box holds 24 books. How many boxes are needed for 1000 books?" -> {"intent": "calculate", "expression": "1000 divup 24"}
"29 sweets are shared equally by 4 children. How many sweets are left over?" -> {"intent": "calculate", "expression": "29 rem 4"}
"A cap costs $4.35. Ali pays with a $10 note. How much change does he get?" -> {"intent": "calculate", "expression": "10-4.35"}
"A film starts at 2:40 and ends at 4:10. How long is the film in minutes?" (known facts: minutes in an hour = 60) -> {"intent": "calculate", "expression": "(4*60+10)-(2*60+40)"}
"Lunch break lasts half an hour. How many minutes is that?" (known facts: minutes in half an hour = 30) -> {"intent": "ask_fact", "question": "minutes in half an hour"}
"What is the area of a rectangle 6 cm long and 4 cm wide?" (known facts: none) -> {"intent": "need_fact", "question": "area of a rectangle"}
"What is the area of a rectangle 6 cm long and 4 cm wide?" (known facts: area of a rectangle = length times width) -> {"intent": "calculate", "expression": "6*4"}
"Tom has 2 dollars and 30 cents. How many cents is that?" (known facts: none) -> {"intent": "need_fact", "question": "cents in a dollar"}
"Tom has 2 dollars and 30 cents. How many cents is that?" (known facts: cents in a dollar = 100) -> {"intent": "calculate", "expression": "2*100+30"}

The brain's working memory is sometimes given with a message. Use its names ("last" is the previous answer) ONLY when the teacher clearly refers back to an earlier result ("that", "it", "the answer", "now add ..."). A message that tells a new story with its own numbers is a new problem: ignore working memory, even if a word like "apples" matches. Never put working-memory numbers into a calculation yourself."""

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
# words that refer back to an earlier result; without them a sentence is a new problem
_REFERS_BACK = re.compile(r"\b(that|it|this|those|them|the answer|the result|last|previous|again|now|then|also|more of|less of|double|half|triple)\b", re.I)


def key(text):
    return " ".join(text.lower().strip().rstrip("?.!").split())


class LanguageError(Exception):
    pass


class Language:
    def __init__(self, phrases=None, patterns=None, model=None, url="http://127.0.0.1:11434", timeout=120, reader=None):
        self.phrases = phrases or {}      # "seven times eight" -> [{"say": "7*8"}]
        self.patterns = patterns or {}    # "what is {0} plus {1}" -> [{"say": "{0}+{1}"}]
        self.model = model if model and str(model).lower() not in ("none", "off", "") else None
        self.url, self.timeout = url.rstrip("/"), timeout
        self.reader = reader              # its own word-problem reader (reader.Reader), or None

    # ---- what it has learned -------------------------------------------------
    def recall(self, text):
        k = key(text)
        if k in self.phrases:
            return self.phrases[k]
        for pattern, meaning in self.patterns.items():
            regex = re.escape(pattern)
            for i in range(10):
                regex = regex.replace(re.escape("{%d}" % i), r"(\d+(?:\.\d+)?)")
            m = re.fullmatch(regex, k)
            if m:
                return [{**line, "say": line["say"].format(*m.groups())} for line in meaning]
        return None

    def learn(self, text, meaning):
        """The teacher confirmed (or corrected) what a sentence means."""
        k = key(text)
        self.phrases[k] = meaning
        numbers = list(dict.fromkeys(_NUMBER.findall(k)))
        if not numbers:
            return
        pattern, said = k, [dict(line) for line in meaning]
        for i, n in enumerate(numbers):
            pattern = re.sub(rf"(?<![\d.]){re.escape(n)}(?![\d.])", "{%d}" % i, pattern)
            for line in said:
                line["say"] = re.sub(rf"(?<![\d.]){re.escape(n)}(?![\d.])", "{%d}" % i, line["say"])
        # every number comes from the sentence (ignoring the {0} {1} placeholders themselves)
        if all(not _NUMBER.search(re.sub(r"\{\d\}", "", line["say"])) for line in said):
            self.patterns[pattern] = said

    # ---- the helper model ----------------------------------------------------
    def translate(self, text, context="", facts=""):
        """What does the sentence mean? Read it once; read it again a little differently; if the two
        readings disagree, read it a third time and go with the majority (like a pupil re-reading a
        question). -> meaning lines, or None."""
        first = self._read(text, context, facts, 0.0)
        second = self._read(text, context, facts, 0.6)
        if first == second:
            return first
        third = self._read(text, context, facts, 0.6)
        if third in (first, second):
            return third
        return first                      # no majority: keep the most careful reading

    def _read(self, text, context, facts, temperature):
        """One reading by the local model -> meaning lines, or None.
        `facts` are the knowledge region's facts: the only outside numbers it may use."""
        # only offer working memory when the sentence refers back, so a new story never reuses old numbers
        message = f"{text}\n\n(working memory: {context or 'empty'})" if context and _REFERS_BACK.search(text) else text
        message += f"\n(known facts: {facts or 'none'})"
        body = {"model": self.model, "stream": False, "format": "json", "think": False,
                "options": {"temperature": temperature},
                "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": message}]}
        req = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                content = json.loads(r.read())["message"]["content"]
            intent = json.loads(content)
        except (OSError, ValueError, KeyError) as e:
            raise LanguageError(f"the language region's helper model ({self.model}) isn't available: {e}")
        return to_meaning(intent)

    def understand(self, text, context="", facts="", known=None):
        """-> {"meaning": [...], "how": "learned" | "measure" | "reader" | "model"} or None.
        `known` is the knowledge region's facts as a dict (for unit conversions)."""
        learned = self.recall(text)
        if learned:
            return {"meaning": learned, "how": "learned"}
        from . import measure
        conv = measure.read(text, known or {})
        if conv:
            if "need" in conv:
                return {"meaning": [{"say": conv["need"], "literal": True, "need_fact": True}], "how": "measure"}
            return {"meaning": [{"say": compose.normalize(conv["say"])}], "how": "measure"}
        if self.reader is not None and self.reader.W is not None and re.search(r"\d", text):
            from .reader import number_sense
            r = self.reader.read(text, number_sense)
            if r and (r[1] >= 0.2 or self.model is None):
                return {"meaning": [{"say": compose.normalize(r[0])}], "how": "reader", "sure": r[1], "schema": r[2]}
        if self.model is None:
            return None                   # no helper model: it doesn't understand this sentence yet
        meaning = self.translate(text, context, facts)
        return {"meaning": meaning, "how": "model"} if meaning else None

    def summary(self):
        return {"phrases": len(self.phrases), "patterns": len(self.patterns), "helper_model": self.model or "none",
                "reader_schemas": len(self.reader.templates) if self.reader else 0,
                "reader_weights": self.reader.n_weights if self.reader else 0}


def to_meaning(intent):
    """Check the model's answer and turn it into lines the brain understands."""
    kind = intent.get("intent")
    try:
        if kind == "calculate":
            expression = str(intent["expression"])
            if re.search(r"[a-wyz]", re.sub(r"\b(divup|div|rem)\b", "", expression), re.I):   # uses working memory: a one-step plan
                return [{"say": f"plan: {expression}"}]
            return [{"say": compose.normalize(expression)}]
        if kind == "plan":
            steps = []
            for s in intent["steps"]:
                expression = str(s["expression"]).strip()
                steps.append(f"{str(s['name']).strip().lower()} = {expression}" if s.get("name") else expression)
            if not steps:
                return None
            return [{"say": "plan: " + "; ".join(steps)}]
        if kind == "teach_rule":
            lhs, rhs = str(intent["rule"]).split("=", 1)
            _, _, name = rules.parse_rule(lhs, rhs)
            return [{"say": name}]
        if kind == "teach_fact":
            return [{"say": f"{key(intent['question'])} = {str(intent['answer']).strip()}", "literal": True}]
        if kind == "ask_fact":
            return [{"say": key(intent["question"]), "literal": True}]
        if kind == "practice":
            return [{"say": compose.normalize(str(p))} for p in intent["problems"][:6]] or None
        if kind == "command" and intent.get("command") in COMMANDS:
            return [{"say": intent["command"]}]
        if kind == "need_fact":
            return [{"say": key(intent["question"]), "literal": True, "need_fact": True}]
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    return None
