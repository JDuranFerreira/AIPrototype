"""The English region: grammar and vocabulary, learned the way children do.

Word forms ("words and rules", as in the brain-science theory of the same name)
  The brain REMEMBERS words it was taught (child -> children, go -> went) and
  notices RULES from them (box -> boxes, baby -> babies, stop -> stopped). For
  a word it has never seen it uses the most specific rule that fits; that is
  why it can pass the "wug test" (one wug, two wugs) and why, like a child,
  it says "goed" until it is taught "went".

  A rule changes the end of a word (or, for "a/an", looks at the start):
      plural  ends in y after a consonant: drop 1 letter, add "ies"   (baby -> babies)
  It is noticed from remembered examples and kept only if far more examples
  fit it than break it; the ones that break it stay as exceptions in memory.

Vocabulary relations
  synonym / antonym (both ways round: if big = large then large = big) and
  is-a, which chains (a dog is a mammal, a mammal is an animal, so a dog is an
  animal).

Grammar in sentences
  "She (go) to school every day" -> "goes". It learns which words point to
  which time (yesterday -> past, every day -> present, now -> continuous) and
  which subjects take the -s form (he, she, it, a name), from the sentences it
  is taught, by counting what went with what.
"""
import re
from collections import Counter

VOWELS = set("aeiou")
FORMS = ["plural", "past", "ing", "third", "comparative", "superlative", "article", "adverb", "negative"]
FORM_HELP = {"plural": "one cat, two …", "past": "yesterday I …", "ing": "I am …-ing", "third": "he/she …",
             "comparative": "bigger", "superlative": "the biggest", "article": "a or an",
             "adverb": "quickly", "negative": "unhappy"}
RELATIONS = {"synonym": True, "antonym": True, "is-a": False}       # True = works both ways round
MIN_FITS = 3                  # examples needed before it trusts a rule it noticed
TIMES = ["present", "past", "continuous", "past continuous", "future"]


def _cls(ch):
    return "V" if ch in VOWELS else "C"


def _shape(word, n):
    """The last n letters as a pattern, e.g. 'baby' -> 'Cy' (consonant then y)."""
    tail = word[-n:]
    return "".join(_cls(c) if i < n - 1 else c for i, c in enumerate(tail)) if n > 1 else tail


def _syllables(word):
    return len(re.findall(r"[aeiouy]+", word.rstrip("e")) or [word])


def _cvc(word):
    """One-syllable word ending consonant-vowel-consonant (stop, big): the last letter doubles."""
    return len(word) >= 3 and _cls(word[-3]) == "C" and _cls(word[-2]) == "V" and _cls(word[-1]) == "C" \
        and word[-1] not in "wxy" and _syllables(word) == 1


def _long(word):
    """Long adjectives take more/most: three syllables or more, or two that don't end in -y, -le, -er, -ow."""
    n = _syllables(word)
    return n >= 3 or (n == 2 and not word.endswith(("y", "le", "er", "ow")))


def _ends(word, shape):
    """shape '=ch' means the word ends in the letters ch; 'Cy' means a consonant then y; '' is any word."""
    if not shape:
        return True                      # (word[-0:] would be the whole word, not the empty end)
    if shape.startswith("="):
        return word.endswith(shape[1:])
    n = len(shape)
    return len(word) >= n and _shape(word, n) == shape


class English:
    def __init__(self, data=None):
        data = data or {}
        self.forms = data.get("forms", {})          # "plural" -> {"child": "children"}
        self.rules = data.get("rules", {})          # "plural" -> [rule dicts]
        self.relations = data.get("relations", {})  # "synonym" -> [["big", "large"]]
        self.classes = data.get("classes", {})      # "happy" -> "adjective"
        self.time_cues = data.get("time_cues", {})  # "yesterday" -> {"past": 3}
        self.third = data.get("third", {})          # "she" -> {"yes": 4}  (does this subject take -s?)
        self.mistakes = data.get("mistakes", [])    # what it said before being corrected (goed, childs)

    def state(self):
        return {"forms": self.forms, "rules": self.rules, "relations": self.relations, "classes": self.classes,
                "time_cues": self.time_cues, "third": self.third, "mistakes": self.mistakes[-200:]}

    # ---- word forms ----------------------------------------------------------
    @staticmethod
    def _context(word, rule):
        if rule["where"] == "prefix":
            return True
        if rule["where"] == "start":
            if rule["shape"] == "LONG":
                return _long(word)
            return _cls(word[0]) == rule["shape"] if rule["shape"] in ("C", "V") else word.startswith(rule["shape"])
        if rule["shape"] == "CVC":
            return _cvc(word)
        return _ends(word, rule["shape"])

    @staticmethod
    def _apply(word, rule):
        if rule["where"] == "start":
            return f"{rule['add']} {word}"
        if rule["where"] == "prefix":
            return rule["add"] + word
        if rule["shape"] == "CVC":
            return word + word[-1] + rule["add"]
        return (word[:-rule["drop"]] if rule["drop"] else word) + rule["add"]

    def form(self, form, word):
        """-> (answer, how): 'memory', 'rule: …', or 'guess' (left unchanged)."""
        word = word.lower().strip()
        if word in self.forms.get(form, {}):
            return self.forms[form][word], "memory"
        best = None
        for rule in self.rules.get(form, []):
            if not rule.get("rejected") and self._context(word, rule):
                if best is None or rule["specific"] > best["specific"]:
                    best = rule
        if best:
            return self._apply(word, best), f"rule: {best['name']}"
        return (f"a {word}" if form == "article" else word), "guess"

    def teach_form(self, form, word, answer):
        """The teacher gives the right form. -> what it would have said, and whether that was right."""
        word, answer = word.lower().strip(), answer.lower().strip()
        own, how = self.form(form, word)
        self.forms.setdefault(form, {})[word] = answer
        if own != answer:
            self.mistakes.append({"form": form, "word": word, "said": own, "right": answer, "how": how})
        return own, how, own == answer

    # noticing rules (induction) ----------------------------------------------
    @staticmethod
    def _candidates(form, word, answer):
        """Rules this one example could come from."""
        out = []
        if form == "article":
            art = answer.split(" ", 1)[0]
            out.append({"where": "start", "shape": _cls(word[0]), "drop": 0, "add": art})
            return out
        if answer.startswith(("more ", "most ")) and answer.endswith(" " + word):
            if _long(word):
                out.append({"where": "start", "shape": "LONG", "drop": 0, "add": answer.split(" ", 1)[0]})
            return out                                   # a short word with more/most is an exception
        if answer.endswith(word) and len(answer) > len(word) and form == "negative":
            out.append({"where": "prefix", "shape": "", "drop": 0, "add": answer[:-len(word)]})
            return out
        if _cvc(word) and answer.startswith(word + word[-1]):
            out.append({"where": "end", "shape": "CVC", "drop": 0, "add": answer[len(word) + 1:]})
        k = 0
        while k < min(len(word), len(answer)) and word[k] == answer[k]:
            k += 1
        drop, add = len(word) - k, answer[k:]
        if drop > 2 or not add:
            return out                                   # not a suffix change (go -> went): an exception
        for n in (1, 2, 3):
            if len(word) > n and n >= drop:
                out.append({"where": "end", "shape": "=" + word[-n:], "drop": drop, "add": add})   # the letters (ch, y)
                if n > 1:
                    out.append({"where": "end", "shape": _shape(word, n), "drop": drop, "add": add})  # a pattern (Cy)
        if drop == 0:
            out.append({"where": "end", "shape": "", "drop": 0, "add": add})      # the general rule: add -s
        return out

    @staticmethod
    def _name(form, r):
        if r["where"] == "start" and r["shape"] == "LONG":
            return f"{form}: long word (3+ syllables, or 2 not ending in -y/-le/-er/-ow): put '{r['add']}' before it"
        if r["where"] == "start":
            return f"{form}: '{r['add']}' before a word starting with a {'vowel' if r['shape'] == 'V' else 'consonant'}"
        if r["where"] == "prefix":
            return f"{form}: put {r['add']}- in front"
        if r["shape"] == "CVC":
            return f"{form}: short consonant-vowel-consonant word: double the last letter, add -{r['add']}"
        shape = r["shape"]
        where = ("any word" if not shape else f"ends in -{shape[1:]}" if shape.startswith("=")
                 else "ends in " + shape.replace("C", "[consonant]").replace("V", "[vowel]"))
        change = f"drop {r['drop']}, " if r["drop"] else ""
        return f"{form}: {where}: {change}add -{r['add']}"

    def _evidence(self, form, rule, specific=0):
        """Remembered words the rule gets right / wrong. Words that a more
        specific rule already handles don't count against a general one
        (babies don't argue against 'add -s')."""
        fits, breaks = [], []
        stronger = [r for r in self.rules.get(form, []) if not r.get("rejected") and r["specific"] > specific]
        for word, answer in self.forms.get(form, {}).items():
            if not self._context(word, rule) or any(self._context(word, r) for r in stronger):
                continue
            (fits if self._apply(word, rule) == answer else breaks).append(word)
        return fits, breaks

    def notice(self, form=None):
        """Look through remembered words for a rule worth trusting. -> new rule or None."""
        known = {(f, r["name"]) for f, rs in self.rules.items() for r in rs}
        best = None
        for f in ([form] if form else FORMS):
            covered = {}                                   # words each trusted rule already explains
            for r in self.rules.get(f, []):
                if not r.get("rejected"):
                    covered[r["name"]] = {w for w, a in self.forms.get(f, {}).items()
                                          if self._context(w, r) and self._apply(w, r) == a}
            for word, answer in self.forms.get(f, {}).items():
                for c in self._candidates(f, word, answer):
                    c["name"] = self._name(f, c)
                    if (f, c["name"]) in known:
                        continue
                    s = c["shape"]
                    c["specific"] = ((3 if s in ("CVC", "LONG") else len(s) - 0.75 if s.startswith("=") else len(s))
                                     + (0.5 if c["drop"] else 0))
                    fits, breaks = self._evidence(f, c, c["specific"])
                    # trust it once enough words fit and most of the ones it covers agree;
                    # the ones that disagree stay remembered as exceptions (like children with went/goed)
                    if len(fits) < MIN_FITS or len(fits) <= len(breaks):
                        continue
                    if any(set(fits) <= ws for ws in covered.values()):
                        continue                           # says nothing new: a trusted rule already covers these words
                    score = (len(fits) - 2 * len(breaks), -c["specific"])   # ties: prefer the more general rule
                    if best is None or score > best[2]:
                        best = (f, c, score, fits, breaks)
        if not best:
            return None
        f, c, _, fits, breaks = best
        return {"form": f, "rule": c, "fits": fits[:6], "exceptions": breaks[:6]}

    def accept_rule(self, form, rule, accept=True):
        rule = dict(rule)
        if not accept:
            rule["rejected"] = True
        self.rules.setdefault(form, []).append(rule)

    def learn_rules(self):
        """Notice and accept rules until none are left (the teacher confirms each one)."""
        found = []
        while True:
            idea = self.notice()
            if not idea:
                return found
            self.accept_rule(idea["form"], idea["rule"])
            found.append(idea)

    # ---- vocabulary relations ---------------------------------------------------
    def teach_relation(self, relation, a, b):
        pair = [a.lower().strip(), b.lower().strip()]
        pairs = self.relations.setdefault(relation, [])
        if pair not in pairs:
            pairs.append(pair)

    def related(self, relation, a, b):
        """Is a <relation> b? -> (True/False/None, why)."""
        a, b = a.lower().strip(), b.lower().strip()
        pairs = self.relations.get(relation, [])
        if [a, b] in pairs:
            return True, "memory"
        if RELATIONS.get(relation) and [b, a] in pairs:
            return True, "reasoned: it works both ways round"
        if relation == "is-a":                          # chains: dog -> mammal -> animal
            seen, frontier = {a}, [a]
            while frontier:
                x = frontier.pop()
                for p, q in pairs:
                    if p == x and q not in seen:
                        if q == b:
                            return True, "reasoned: chain of is-a"
                        seen.add(q)
                        frontier.append(q)
        if relation == "synonym" and self.related("antonym", a, b)[0]:
            return False, "reasoned: they are opposites"
        return None, "doesn't know"

    def find(self, relation, a):
        """The word that is <relation> of a (antonym of hot -> cold), or None."""
        a = a.lower().strip()
        for p, q in self.relations.get(relation, []):
            if p == a:
                return q, "memory"
            if RELATIONS.get(relation) and q == a:
                return p, "reasoned: it works both ways round"
        if relation == "antonym":                       # opposite of a synonym: chilly ~ cold, cold <-> hot
            for p, q in self.relations.get("synonym", []):
                other = q if p == a else p if q == a else None
                if other:
                    found = self.find("antonym", other)
                    if found[0]:
                        return found[0], f"reasoned: {a} means {other}, and the opposite of {other} is {found[0]}"
        return None, "doesn't know"

    # ---- word classes --------------------------------------------------------------
    def teach_class(self, word, cls):
        self.classes[word.lower().strip()] = cls

    def word_class(self, word):
        """noun / verb / adjective / adverb: memory, else the ending it shares with known words."""
        word = word.lower().strip()
        if word in self.classes:
            return self.classes[word], "memory"
        for n in (4, 3, 2):
            tally = Counter(c for w, c in self.classes.items() if len(w) > n + 1 and w[-n:] == word[-n:])
            if tally and sum(tally.values()) >= 2:
                cls, count = tally.most_common(1)[0]
                if count >= 2 * (sum(tally.values()) - count):
                    return cls, f"rule: words ending in -{word[-n:]} are usually {cls}s"
        return None, "doesn't know"

    # ---- grammar in sentences ------------------------------------------------------
    _GAP = re.compile(r"^(?P<before>.*?)\((?P<verb>[a-zA-Z]+)\)(?P<after>.*)$")

    @staticmethod
    def _words(text):
        return re.findall(r"[a-zA-Z']+", text.lower())

    def _subject(self, before):
        words = re.findall(r"[A-Za-z']+", before)
        return words[-1] if words else ""

    PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}

    def _subject_key(self, subject, before=""):
        """A pronoun is itself even at the start of a sentence (She); a capitalised word with no 'the/a' in
        front is a name (Tom); other nouns are one or many, judged with its own plural knowledge."""
        low = subject.lower()
        if low in self.PRONOUNS:
            return low
        if subject[:1].isupper() and not re.search(r"\b(the|a|an|my|our|his|her|their|this|these|those)\s+\S+\s*$", before, re.I):
            return "<name>"
        return "<many>" if self.is_plural(low) else "<one>"

    def is_plural(self, word):
        """Is this noun 'many'? Memory first, then: would its own plural rule make it from a shorter word?"""
        plurals = self.forms.get("plural", {})
        if word in plurals.values():
            return True
        if word in plurals:
            return False
        for stem in (word[:-1], word[:-2], word[:-3] + "y"):
            if stem and self.form("plural", stem)[0] == word:
                return True
        return False

    def _be(self, subject_key, past=False):
        if subject_key == "i":
            return "was" if past else "am"
        many = subject_key in ("you", "we", "they", "<many>")
        return ("were" if many else "was") if past else ("are" if many else "is")

    def teach_sentence(self, sentence, answer):
        """Learn from a gap-fill: which time the cues point to, and whether the subject takes -s."""
        m = self._GAP.match(sentence)
        if not m:
            raise ValueError("a gap-fill sentence looks like: She (go) to school every day.")
        verb, ans = m["verb"].lower(), answer.lower().strip()
        own, _ = self.fill(sentence)
        words = ans.split()
        time = ("future" if words[0] == "will" else
                "past continuous" if len(words) > 1 and words[0] in ("was", "were") and words[-1].endswith("ing") else
                "continuous" if len(words) > 1 and words[-1].endswith("ing")
                else "past" if ans != verb and (ans in (self.form("past", verb)[0], self.forms.get("past", {}).get(verb))
                                                or (ans.endswith("ed") and not verb.endswith("ed"))) else "present")
        for w in set(self._words(m["before"] + " " + m["after"])):
            self.time_cues.setdefault(w, {}).setdefault(time, 0)
            self.time_cues[w][time] += 1
        if time == "present":
            subject = self._subject_key(self._subject(m["before"]), m["before"])
            takes_s = ans != verb
            self.third.setdefault(subject, {"yes": 0, "no": 0})["yes" if takes_s else "no"] += 1
            if takes_s:
                self.forms.setdefault("third", {})[verb] = ans
        elif time == "past":
            self.forms.setdefault("past", {})[verb] = ans
        return own

    def _time(self, sentence):
        votes = Counter()
        for w in set(self._words(sentence)):
            cue = self.time_cues.get(w, {})
            total = sum(cue.values())
            if total >= 2:
                best, n = max(cue.items(), key=lambda kv: kv[1])
                if n / total >= 0.8:                     # a word that reliably points to one time
                    votes[best] += n
        return (votes.most_common(1)[0][0], "time cue") if votes else ("present", "no time cue: guessed present")

    def fill(self, sentence):
        """'She (go) to school every day.' -> ('goes', how)."""
        m = self._GAP.match(sentence)
        if not m:
            raise ValueError("a gap-fill sentence looks like: She (go) to school every day.")
        verb = m["verb"].lower()
        time, why = self._time(m["before"] + " " + m["after"])
        subject = self._subject(m["before"])
        key = self._subject_key(subject, m["before"])
        if time == "past":
            word, how = self.form("past", verb)
            return word, f"{why}: past ({how})"
        if time == "future":
            return f"will {verb}", f"{why}: future"
        if time in ("continuous", "past continuous"):
            word, how = self.form("ing", verb)
            return f"{self._be(key, time == 'past continuous')} {word}", f"{why}: {time} ({how})"
        tally = self.third.get(key)
        if tally and tally["yes"] > tally["no"]:
            word, how = self.form("third", verb)
            return word, f"{why}; '{subject}' takes -s ({how})"
        return verb, f"{why}; '{subject}' takes the plain verb" if tally else f"{why}; doesn't know '{subject}' yet"

    # ---- overview --------------------------------------------------------------------
    def summary(self):
        return {"words": {f: len(v) for f, v in self.forms.items()},
                "rules": [r["name"] for rs in self.rules.values() for r in rs if not r.get("rejected")],
                "relations": {k: len(v) for k, v in self.relations.items()},
                "classes": len(self.classes), "time_cues": len(self.time_cues),
                "mistakes": len(self.mistakes)}
