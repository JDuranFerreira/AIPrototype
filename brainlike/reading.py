"""Reading (the LANGUAGE region's engine): learning words and the world from scenes, like a young child.

Stage 1-2  WORDS     Hebbian, cross-situational learning: each time the brain sees a scene and
                     hears a sentence, every word heard is linked a little to everything seen.
                     Over many scenes the right link wins ("red" keeps coming with colour:red,
                     not with the ball). Words that come with everything ("the", "look") end up
                     meaning nothing in particular: grammar words.
Stage 3    WORLD     Facts the teacher says ("a dog has four legs", "a puppy is a young dog")
                     go into a small semantic network; answers are passed down the is-a chain,
                     so it knows a puppy has four legs without being told.
Stage 4    ACTIONS   It sees how many things each person has before and after "Tom gives Ana 2
                     apples", and learns what each verb DOES (giver -2, receiver +2).
Stage 5-6  STORIES   It reads a story by acting it out in its head (storyreader.py). What each
                     sentence does is LEARNED: every sentence comes with the scene after it, and
                     each word, in its frame (the people, numbers and things around it), is
                     credited with what the scene shows happened. He/she/his/her are learned the
                     same way. Questions learn from the teacher's answer. Stories told in the
                     chat with an answer teach it too (it looks for the one sentence it misread).

Its state is kept by the language region (brain_state/language/reading.json). It has no neural weights: what it
knows is counts (how often a word came with a feature, a frame with a change).
"""
import math
import re
from collections import defaultdict

from .stories import Storyteller
from .planner import Doubts
from .storyreader import Frames, Lexicon, StoryReader, fmt, learn_from_answer, learn_tale, sentences
from .world import NUMBER_WORDS, PEOPLE, World, plural

NAME = re.compile(r"\b[A-Z][a-z]+\b")


def words_of(sentence):
    return re.findall(r"[a-z]+(?:-[a-z]+)*", sentence.lower())




class WordLearner:
    """Every word heard is linked to everything seen; meaning = the feature it goes with far more than chance.

    Chance is measured within each KIND OF SITUATION (playground scenes, counting lessons), the way a child
    knows where it is: a word heard only on the playground is judged only by playground scenes, so later
    counting lessons (with their own mix of things) can't wash its meaning out."""

    def __init__(self, data=None):
        data = data or {}
        if "contexts" in data:
            raw = data["contexts"]
        else:                                    # an older brain: everything it saw counts as one kind of situation
            raw = {"scene": {k: data.get(k, {} if k != "n" else 0) for k in ("n", "word", "feat", "pair")}}
        self.ctx = {}
        for name, c in raw.items():
            self._context(name, c)
        self.word = defaultdict(int)             # how often each word was heard, anywhere
        for c in self.ctx.values():
            for w, k in c["word"].items():
                self.word[w] += k
        # links(word) is cached between observes: building a Lexicon asks for every word (twice, plus
        # its base form) and observe() is the only place the counts change, so it bumps the revision
        self._links_rev, self._links = 0, {}

    def _context(self, name, c=None):
        if name not in self.ctx:
            c = c or {}
            self.ctx[name] = {"n": c.get("n", 0), "word": defaultdict(int, c.get("word", {})),
                              "feat": defaultdict(int, c.get("feat", {})),
                              "pair": defaultdict(lambda: defaultdict(int),
                                                  {w: defaultdict(int, f) for w, f in c.get("pair", {}).items()})}
        return self.ctx[name]

    @property
    def n(self):
        return sum(c["n"] for c in self.ctx.values())

    @property
    def pair(self):
        out = defaultdict(lambda: defaultdict(int))
        for c in self.ctx.values():
            for w, fs in c["pair"].items():
                for f, k in fs.items():
                    out[w][f] += k
        return out

    def observe(self, seen, heard, context="scene"):
        c = self._context(context)
        c["n"] += 1
        ws, fs = set(words_of(heard)), set(seen)
        for w in ws:
            c["word"][w] += 1
            self.word[w] += 1
            row = c["pair"][w]
            for f in fs:
                row[f] += 1
        for f in fs:
            c["feat"][f] += 1
        self._links_rev += 1                     # the counts changed: every cached link is stale
        self._links.clear()

    def links(self, word):
        """All features for a word, strongest first: (feature, strength). Strength is how much more often
        they come together than chance (log scale), in each kind of situation where the word was heard,
        weighted by how often it was heard there; 0 means no real link. -> fresh list (cached between
        observes: building a Lexicon asks for every word several times)."""
        w = word.lower()
        hit = self._links.get(w)
        if hit is not None and hit[0] == self._links_rev:
            return list(hit[1])
        total = self.word.get(w, 0)
        if total == 0:
            return []
        strength = defaultdict(float)
        for c in self.ctx.values():
            heard = c["word"].get(w, 0)
            if not heard:
                continue
            for f, k in c["pair"][w].items():
                if k < 2:
                    continue
                pmi = math.log((k * c["n"]) / (heard * c["feat"][f]))
                strength[f] += pmi * k / total            # how often the feature is there when the word is heard
        out = sorted(((f, v) for f, v in strength.items() if v > 0), key=lambda x: -x[1])
        if len(self._links) < 50000:              # a guard; the vocabulary is far smaller than this
            self._links[w] = (self._links_rev, out)
        return out

    def meaning(self, word, kind=None):
        """The feature a word means (optionally of one kind, e.g. 'colour'), or None for grammar words."""
        for f, s in self.links(word):
            if s > 0.5 and (kind is None or f.startswith(kind + ":")):
                return f, s
        return None

    def word_for(self, feature):
        """Production: the word that best means this feature."""
        best = None
        for w in self.word:
            m = self.meaning(w)
            if m and m[0] == feature and (best is None or m[1] > best[1]):
                best = (w, m[1])
        return best[0] if best else None

    def vocabulary(self):
        return {w: m[0] for w in self.word if (m := self.meaning(w))}

    def state(self):
        return {"contexts": {name: {"n": c["n"], "word": dict(c["word"]), "feat": dict(c["feat"]),
                                    "pair": {w: dict(f) for w, f in c["pair"].items()}} for name, c in self.ctx.items()}}


class WorldKnowledge:
    """A small semantic network from the teacher's sentences, with inheritance along is-a."""

    def __init__(self, words, data=None):
        self.words = words
        data = data or {}
        self.isa = data.get("isa", {})               # puppy -> dog
        self.props = data.get("props", {})           # dog -> {"legs": 4, "says": "woof", "can": ["run"]}
        self.young = data.get("young", {})

    def number(self, word):
        m = self.words.meaning(word, "count")        # "four" means count:4, learned from scenes
        return int(m[0].split(":")[1]) if m else None

    def hear(self, sentence):
        s = sentence.lower().strip(" .")
        if m := re.fullmatch(r"an? (\w+) is an? young (\w+)", s):
            self.isa[m[1]] = m[2]
            self.young[m[1]] = m[2]
        elif m := re.fullmatch(r"an? (\w+) is an? (\w+)", s):
            self.isa[m[1]] = m[2]
        elif m := re.fullmatch(r"an? (\w+) has (\w+) legs", s):
            n = self.number(m[2])
            if n is not None:
                self.props.setdefault(m[1], {})["legs"] = n
            else:
                self.props.setdefault(m[1], {})["legs?"] = m[2]   # heard a number word it doesn't know yet
        elif m := re.fullmatch(r"an? (\w+) says (\w+)", s):
            self.props.setdefault(m[1], {})["says"] = m[2]
        elif m := re.fullmatch(r"an? (\w+) can (\w+)", s):
            self.props.setdefault(m[1], {}).setdefault("can", []).append(m[2])
        else:
            return False
        return True

    def lookup(self, thing, prop):
        """The property, passed down the is-a chain. -> (value, how) or (None, why)."""
        chain, x = [], thing
        while x and x not in chain:
            chain.append(x)
            if prop in self.props.get(x, {}):
                return self.props[x][prop], ("told" if x == thing else f"{thing} is a {' -> '.join(chain[1:])}, so")
            x = self.isa.get(x)
        return None, "doesn't know"

    def is_a(self, thing, category):
        x, seen = thing, []
        while x and x not in seen:
            if x == category:
                return True
            seen.append(x)
            x = self.isa.get(x)
        return False

    def ask(self, question):
        q = question.lower().strip(" ?")
        if m := re.fullmatch(r"how many legs (?:does|do) (?:an? )?(\w+) have", q):
            v, how = self.lookup(m[1], "legs")
            return v, how
        if m := re.fullmatch(r"how many legs (?:do|does) (\w+) (\w+) have", q):        # "do three dogs have"
            k = self.number(m[1])
            thing = m[2][:-1] if m[2].endswith("s") else m[2]
            v, how = self.lookup(thing, "legs")
            return (v * k if v is not None and k is not None else None), how
        if m := re.fullmatch(r"what does an? (\w+) say", q):
            return self.lookup(m[1], "says")
        if m := re.fullmatch(r"is an? (\w+) an? (\w+)", q):
            return ("yes" if self.is_a(m[1], m[2]) else "no"), "is-a chain"
        if m := re.fullmatch(r"can an? (\w+) (\w+)", q):
            v, how = self.lookup(m[1], "can")
            return (None, how) if v is None else ("yes" if m[2] in v else "not that I know"), how
        return None, "doesn't understand the question"

    def state(self):
        return {"isa": self.isa, "props": self.props, "young": self.young}


class ActionLearner:
    """What a verb does to how many things people have, learned from before -> after."""

    def __init__(self, data=None):
        self.effects = defaultdict(lambda: defaultdict(int), {v: defaultdict(int, e) for v, e in (data or {}).items()})

    @staticmethod
    def _parse(heard):
        names = NAME.findall(heard)
        nums = [int(x) for x in re.findall(r"\b\d+\b", heard)]
        if not names or not nums:
            return None
        sub = names[0]
        after_name = heard.split(sub, 1)[1].split()
        verb = after_name[0].lower() if after_name else None
        other = names[1] if len(names) > 1 else None
        return sub, verb, other, nums[0]

    @staticmethod
    def _sym(d, n):
        return "+n" if d == n else "-n" if d == -n else "0" if d == 0 else "?"

    def observe(self, before, heard, after):
        p = self._parse(heard)
        if not p:
            return
        sub, verb, other, n = p
        effect = (self._sym(after[sub] - before[sub], n), self._sym(after[other] - before[other], n) if other else "-")
        self.effects[verb][f"{effect[0]}|{effect[1]}"] += 1

    def meaning(self, verb):
        e = self.effects.get(verb.lower())
        if not e:
            return None
        best, count = max(e.items(), key=lambda kv: kv[1])
        return tuple(best.split("|")) if count >= 2 and count / sum(e.values()) >= 0.8 else None

    def state(self):
        return {v: dict(e) for v, e in self.effects.items()}


def _cells(scene):
    return [[o, t, sorted(d), str(v)] for (o, t, d), v in scene.items()]


class _Relived:
    """A remembered story, as the storyteller told it."""

    def __init__(self, ep):
        from fractions import Fraction
        cells = lambda xs: {(o, t, frozenset(d)): Fraction(v) for o, t, d, v in xs}
        self.lines = [(s, cells(t), cells(f)) for s, t, f in ep["lines"]]
        self.question, self.answer = ep["q"], Fraction(ep["a"])


class Reading:
    """Reading: words from scenes, facts about the world, what verbs do, and stories
    read by acting them out with learned sentence frames.   -> the language region"""
    LESSONS = {"words": 2000, "facts": 1, "actions": 300, "stories": 3000}

    def __init__(self, data=None, coordination=None, doubts=None):
        d = data or {}
        self.words = WordLearner(d.get("words"))
        self.know = WorldKnowledge(self.words, d.get("knowledge"))
        self.actions = ActionLearner(d.get("actions"))
        self.frames = Frames(d.get("frames"), coordination)
        self.doubts = doubts if doubts is not None else Doubts()
        self.lessons = {"scenes": 0, "facts": 0, "events": 0, "stories": 0, "taught_stories": 0, **d.get("lessons", {})}
        self.exam = d.get("exam")
        self.episodes = d.get("episodes", {})      # memories of stories it lived through, per stage (see remember)
        self.meanings = d.get("meanings", {})      # word -> what the teacher said it means (saved, checked first)
        self.seen_episodes = d.get("seen_episodes", {})
        self._lex = None

    def state(self):
        return {"words": self.words.state(), "knowledge": self.know.state(), "actions": self.actions.state(),
                "frames": self.frames.state(), "lessons": self.lessons, "exam": self.exam,
                "episodes": self.episodes, "seen_episodes": self.seen_episodes, "meanings": self.meanings}

    # ---- memories and sleep ------------------------------------------------------------------------------
    MEMORY = 300                                   # stories it keeps per stage (a sample of all it lived through)

    def remember(self, stage, tale=None, real=None):
        """Keep a fair sample of what it lived through at each stage (reservoir sampling): a world story with its
        scenes, or a real story with the teacher's answer."""
        import random
        ep = {"real": list(real)} if real else {
            "lines": [[s, _cells(t), _cells(f)] for s, t, f in tale.lines], "q": tale.question, "a": str(tale.answer)}
        if real:
            ep["real"][1] = str(ep["real"][1])
        box = self.episodes.setdefault(stage, [])
        k = self.seen_episodes.get(stage, 0) + 1
        self.seen_episodes[stage] = k
        if len(box) < self.MEMORY:
            box.append(ep)
        else:
            j = random.Random(k * 7919 + len(stage)).randrange(k)
            if j < self.MEMORY:
                box[j] = ep

    def sleep(self, n=600):
        """Sleep: replay the same number of remembered stories from every stage, so the newest lessons can't
        slowly take over what it learned before. World stories are relived with their scenes; real stories
        with the teacher's answer."""
        import random
        from fractions import Fraction
        stages = [s for s, box in self.episodes.items() if box]
        if not stages:
            return {"replayed": 0}
        r = random.Random(sum(self.seen_episodes.values()))
        lex = self.lexicon()
        done = {}
        for i in range(n):
            stage = stages[i % len(stages)]
            ep = r.choice(self.episodes[stage])
            self.frames.situation = stage                 # relived where it happened
            if "real" in ep:
                learn_from_answer(ep["real"][0], Fraction(ep["real"][1]), StoryReader(lex, self.frames, self.doubts), self.frames,
                                  weight=1)
            else:
                learn_tale(_Relived(ep), lex, self.frames)
            done[stage] = done.get(stage, 0) + 1
        self._lex = None
        self.frames.situation = "chat"
        self.lessons["slept"] = self.lessons.get("slept", 0) + n
        return {"replayed": n, "by_stage": done}

    def lexicon(self):
        if self._lex is None:
            self._lex = Lexicon(self.words, self.frames, self.meanings)
        return self._lex

    # ---- meanings the teacher gives --------------------------------------------------------------------
    KINDS_SAID = {"colour": "colour", "color": "colour", "size": "size", "day": "day", "time of day": "time",
                  "thing": "thing", "animal": "thing", "toy": "thing", "fruit": "thing", "food": "thing",
                  "boy's name": "person:boy", "girl's name": "person:girl", "name of a boy": "person:boy",
                  "name of a girl": "person:girl", "boy": "person:boy", "girl": "person:girl"}

    @staticmethod
    def reads_as_meaning(text):
        low = text.strip().lower().rstrip(".!")
        return bool(re.fullmatch(r"(?:the words? )?'?[a-z][a-z'-]*(?: [a-z][a-z'-]*){0,3}'? means .+", low) or
                    re.fullmatch(r"[a-z][a-z'-]* is (?:a|an) (?:colour|color|size|day|time of day|thing|animal|toy|fruit|"
                                 r"food|boy's name|girl's name|name of a boy|name of a girl|boy|girl)", low))

    def teach_meaning(self, text):
        """'migrating means flying away', 'red is a colour', 'Mia is a girl's name', 'dozen means 12'. -> reply."""
        from .storyreader import singular, tokens
        low = text.strip().lower().rstrip(".!")
        if m := re.fullmatch(r"(?:the words? )?'?([a-z][a-z'-]*(?: [a-z][a-z'-]*){0,3}?)'? means (.+)", low):
            word, said = m[1], m[2].strip()
            if re.fullmatch(r"\d+", said):
                meaning = {"feature": f"count:{said}"}
            else:
                same = [t for t in tokens(said) if t not in (".", ",", "to") or len(tokens(said)) == 1]
                meaning = {"same": same}
        elif m := re.fullmatch(r"([a-z][a-z'-]*) is (?:a|an) (.+)", low):
            word, kind = m[1], self.KINDS_SAID.get(m[2])
            if not kind:
                return None
            if ":" in kind:
                meaning = {"feature": kind}
            elif kind == "thing":
                meaning = {"feature": f"thing:{singular(word)}"}
            else:
                meaning = {"feature": f"{kind}:{word}"}
        else:
            return None
        own = self.meaning_of(word)
        self.meanings[word] = {**meaning, "said": text.strip()}
        self._lex = None
        lex = self.lexicon()
        new = [t for t in meaning.get("same", []) if t.isalpha() and not lex.familiar(t)]   # words it doesn't know either
        return {"problem": text, "source": "language", "kind": "meaning", "region": "language",
                "learned": text.strip(), "word": word, "own_answer": own, "tries": 1, "agrees_with_math": None,
                "words": new}

    def unknown_words(self, trace):
        """Words in the story it never really met (not names, not new things after the/a): what it would ask."""
        out = []
        for t in trace:
            for w in t.get("unknown", []):
                if w not in out:
                    out.append(w)
        return out

    # ---- rules the teacher teaches, with the process (P3: whole groups) ----------------------------------
    def learn_rule(self, said, phrase, examples):
        """The teacher says a rule and shows worked examples: 'groups of 5 from 17: ... 2 left over'. It works every
        example out with its own process (group_steps), finds which of its own numbers the teacher's number is, and
        keeps the rule only if that is the same one in EVERY example. -> (kept?, what it found)"""
        from .coordination import group_steps
        fits, mine = None, []
        for a, b, told in examples:
            q, r, work = group_steps(a, b)
            have = {"&": q, "%": r, "^": q + (r > 0)}
            ok = {op for op, v in have.items() if v == told}
            fits = ok if fits is None else fits & ok
            mine.append(f"{a} in groups of {b}: {work}")
        if fits is None or len(fits) != 1:
            return False, mine
        op = fits.pop()
        self.frames.rules[op] = {"rule": said, "phrase": phrase, "examples": len(examples)}
        self.frames.coord.reward(op, True, steps=len(examples))   # it checked every worked example itself
        self._lex = None
        return True, mine

    def learn_op(self, op, said, phrase, examples):
        """A P5-P6 rule ('20% of 50', 'the greatest common factor'): the teacher shows worked examples (args -> answer);
        it works each out with its own process and keeps the rule only if it gets the teacher's answer every time."""
        from fractions import Fraction
        from .coordination import gcd_steps, lcm_steps, percent_steps, unitary_steps
        own = {"!": lambda p, b: percent_steps(p, b), "#": gcd_steps, "$": lcm_steps, "u": unitary_steps,
               "q": lambda a: (Fraction(a) * Fraction(a), f"{a} \u00d7 {a} = {Fraction(a) * Fraction(a)}")}[op]
        mine, ok = [], True
        for args, told in examples:
            v, work = own(*args)
            mine.append(work)
            ok = ok and Fraction(v) == Fraction(told)
        if ok:
            self.frames.rules[op] = {"rule": said, "phrase": phrase, "examples": len(examples)}
            self._lex = None
        self.frames.coord.reward(op, ok, steps=len(examples))     # the teacher's worked examples, checked by the tool
        return ok, mine

    def learn_fact(self, fact):
        """A unit fact the teacher tells ('1 kg is 1000 g'): kept, and used whenever a story turns one into the other."""
        if not any(u["said"] == fact["said"] for u in self.frames.units):
            self.frames.units.append(fact)
        return True

    # ---- which unknown words are worth asking about -------------------------------------------------------
    _COUNTS = {"many", "much", "some", "more", "few", "several", "all", "both", "each", "every", "another", "other"}
    _PARTICLES = {"up", "out", "off", "away", "down", "back", "over", "in"}
    _CLAUSE = {"if", "when", "and", "but", "then", "so", "after", "while", "than", "before", "because", "where"}

    def _thing_spot(self, toks, i, lex):
        """A child accepts a new word as the NAME OF A THING from where it stands: right after a number, 'how many',
        the/a/his... (perhaps with describing words between), or right before a thing it knows ('stray cats').
        Not a word that sounds like something done ('6 dressed up', '5 wilted')."""
        from .storyreader import _BETWEEN, _DET
        w, nxt = toks[i], (toks[i + 1] if i + 1 < len(toks) else "")
        if w.endswith("ed") or nxt in self._PARTICLES:
            return False
        k = i - 1
        while k >= 0 and k >= i - 3 and toks[k].isalpha() and not lex.person(toks[k]) and (
                lex.thing(toks[k]) or lex.colour(toks[k]) or lex.size(toks[k]) or toks[k] in _BETWEEN or
                toks[k] in ("total", "whole", "different") or
                not lex.familiar(toks[k]) and not toks[k].endswith(("s", "ed"))):
            k -= 1                                     # describing words: '11 candy bars', '86 consecutive ...'
        if k >= 0 and (toks[k][0].isdigit() or lex.number(toks[k]) is not None or toks[k] in _DET or
                       toks[k] in self._COUNTS or toks[k] == "of"):
            return True
        return bool(nxt) and bool(lex.thing(nxt))

    def _name_spot(self, text, w, toks, spots, reader, before, lex):
        """A new word is a NAME if it is written with a capital where no sentence starts, or someone's ('Albert's'),
        or it stands where a person stands (starting a clause, not after a person: that's a verb) and the story reads
        better with a name it knows in its place."""
        if re.search(rf"[^.?!\s]\s+{w[0].upper()}{re.escape(w[1:])}\b", text) or \
                re.search(rf"(?i)\b{re.escape(w)}\s*['\u2019]\s*s\b", text):
            return True
        subject = [i for i in spots if (i == 0 or toks[i - 1] in ".?!," or toks[i - 1] in self._CLAUSE) and
                   not (i > 0 and (lex.person(toks[i - 1]) or lex.pronoun(toks[i - 1])))]
        if not subject:
            return False
        nxt = [toks[i + 1] for i in subject if i + 1 < len(toks)]
        if w.endswith(("ed", "ing", "ly")):
            return False
        if re.search(rf"(?:^|[.?!]\s+){w[0].upper()}{re.escape(w[1:])}\b", text) and \
                any(not (lex.person(x) or lex.pronoun(x)) and x.isalpha() for x in nxt):
            return True                                # 'Daniel comes to help': a capital where a person would start
        from .storyreader import _DET
        if any(lex.familiar(x) and x.isalpha() and not lex.thing(x) and x not in _DET and lex.number(x) is None and
               not lex.person(x) and not lex.pronoun(x) for x in nxt):
            return True                                # 'debby had 12 pounds': a word it knows comes next, as after a name
        for name in ("Kim", "Leo"):
            swapped = re.sub(rf"(?i)\b{re.escape(w)}\b", name, text)
            _, _, trace = reader.solve(swapped)
            if self._reads(trace) > before:
                return True
        return False

    @staticmethod
    def _reads(trace):
        """How many clauses it can follow: it did something with them and met no unknown word."""
        return sum(bool(t["did"]) and not t.get("unknown") for t in trace)

    def words_to_teach(self, stories, top=20):
        """The words it met in these stories but doesn't know, minus the ones a child would just accept: names
        (a known name fits there) and things (a word after a number or the/a). The rest is what HAPPENED (verbs)
        or how (not, over, per): those it needs a teacher for. -> {"ask": [{word, n, example}], "accepted": {...}}"""
        from .storyreader import tokens
        lex, reader = self.lexicon(), self.reader()
        ask, names, things = {}, {}, {}
        for text in stories:
            _, _, trace = reader.solve(text)
            unknown = [w for w in self.unknown_words(trace) if len(w) > 1 and w not in self.meanings and
                       w not in ("ca", "wo", "sha")]          # "ca n't", "wo n't": halves of a word it knows
            if not unknown:
                continue
            toks = tokens(text)
            sure = self._reads(trace)
            for w in unknown:
                spots = [i for i, t in enumerate(toks) if t == w]
                after_someone = any(i > 0 and (lex.person(toks[i - 1]) or lex.pronoun(toks[i - 1])) for i in spots)
                if any(self._thing_spot(toks, i, lex) for i in spots) and not after_someone:
                    box = things
                elif self._name_spot(text, w, toks, spots, reader, sure, lex):
                    box = names
                else:
                    box = ask
                e = box.setdefault(w, {"word": w, "n": 0, "example": text.strip()})
                e["n"] += 1
        for w in list(ask):                     # a word that was a name or a thing in another story stays accepted
            if w in names or w in things:
                del ask[w]
        rank = lambda box: sorted(box.values(), key=lambda e: (-e["n"], e["word"]))
        return {"ask": rank(ask)[:top], "more": max(0, len(ask) - top),
                "accepted": {"names": [e["word"] for e in rank(names)], "things": [e["word"] for e in rank(things)]}}

    def reader(self):
        return StoryReader(self.lexicon(), self.frames, self.doubts)

    # ---- lessons from the simulated world ---------------------------------------------------------------
    def teach(self, what="all", n=None):
        """Lessons from the world, each with new scenes (the seed moves on with every lesson)."""
        order = ["words", "facts", "actions", "stories"] if what == "all" else [what]
        done = {}
        for lesson in order:
            if lesson not in self.LESSONS:
                raise ValueError(f"reading lessons: {', '.join(self.LESSONS)}, all")
            k = n if n and what != "all" else self.LESSONS[lesson]
            if lesson == "words":
                world = World(seed=1000 + self.lessons["scenes"])
                for _ in range(k):
                    self.words.observe(*world.scene())
                self.lessons["scenes"] += k
                self._lex = None
            elif lesson == "facts":
                facts = World(seed=0).facts()
                done["facts_understood"] = sum(self.know.hear(f) for f in facts)
                self.lessons["facts"] += len(facts)
                k = len(facts)
            elif lesson == "actions":
                world = World(seed=2000 + self.lessons["events"])
                for _ in range(k):
                    before, heard, after, _ = world.event()
                    self.actions.observe(before, heard, after)
                self.lessons["events"] += k
            else:
                teller = Storyteller(seed=3000 + self.lessons["stories"])
                lex = self.lexicon()
                self.frames.situation = "kindergarten"
                for i in range(k):
                    tale = teller.tale()
                    learn_tale(tale, lex, self.frames)
                    self.remember("kindergarten", tale)
                    if i % 500 == 499:
                        self._lex = lex = Lexicon(self.words, self.frames)   # new pronouns and words
                self.lessons["stories"] += k
                self._lex = None
            done[lesson] = k
        return done

    def take_exam(self, n=40, seed=99):
        """New stories it has never heard (another seed), by kind; it only reads them, it learns nothing."""
        teller, reader = Storyteller(seed=seed), self.reader()
        by_kind = {}
        for kind in Storyteller.KINDS:
            ok = 0
            for _ in range(n):
                t = teller.tale(kind)
                got, _, _ = reader.solve(t.text())
                ok += got == t.answer
            by_kind[kind] = {"right": ok, "of": n}
        world, ok = World(seed=seed), 0
        for _ in range(n):
            story, answer = world.story()
            ok += reader.solve(story)[0] == answer
        by_kind["stage 5 stories"] = {"right": ok, "of": n}
        right = sum(v["right"] for v in by_kind.values())
        total = sum(v["of"] for v in by_kind.values())
        self.exam = {"right": right, "of": total, "by_kind": by_kind}
        return self.exam

    # ---- talking to it ----------------------------------------------------------------------------------
    @staticmethod
    def is_story(text):
        low = text.lower()
        numbers = r"\d|\bsome\b|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|" \
                  r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b"
        asks = r"\bhow (many|much)\b|\bwhat(?:'s| is) the (difference|total)\b|\bat what\b|\bwhat fraction\b"
        return bool(re.search(asks, low)) and bool(re.search(numbers, low))

    def read_story(self, text, check=True):
        got, how, trace = self.reader().solve(text)
        unknown = self.unknown_words(trace)
        if check and unknown:                       # not sure: check with the teacher instead of guessing
            return {"problem": text, "source": "language", "kind": "word_question", "region": "language",
                    "words": unknown, "guess": fmt(got) if got is not None else None, "trace": trace}
        return {"problem": text, "source": "language", "kind": "story", "region": "language",
                "answer": fmt(got) if got is not None else None, "how": how, "trace": trace, "words": unknown}

    def learn_story(self, text, answer, weight=3, taught_words=True):
        unknown = self.unknown_words(self.reader().solve(text)[2]) if taught_words else []
        r = learn_from_answer(text, answer, self.reader(), self.frames, weight=weight)
        if taught_words and r.get("learned") and r["learned"] != "what it did was right" or (taught_words and r.get("agreed")):
            for w in unknown:                        # the teacher showed what these words do: saved, no need to ask
                self.meanings.setdefault(w, {"said": f"{w}: shown by example ({text.strip()} = {answer})"})
            self._lex = None
        for toks in sentences(text):                  # it heard these words too
            self.frames.hear(toks)
        self.lessons["taught_stories"] += 1
        lesson = r.pop("learned")
        return {"problem": text, "source": "language", "kind": "story", "region": "language",
                "learned": str(answer), "lesson": lesson, "tries": 1, "agrees_with_math": None, **r}

    def meaning_of(self, word):
        w = word.lower()
        if w in self.meanings:
            return f"you taught me: {self.meanings[w]['said']}"
        m = self.words.meaning(w)
        if m:
            kind, value = m[0].split(":", 1)
            what = {"colour": "a colour", "thing": "a thing", "count": "a number", "size": "a size", "shape": "a shape",
                    "face": "a feeling", "sky": "the weather", "doing": "something you do", "rel": "where something is",
                    "person": f"a {value}'s name", "day": "a day", "time": "a time of day"}.get(kind, kind)
            seen = self.words.word.get(w, 0)
            return f"{w} is {what} ({m[0]}): I heard it {seen} times, and it came with {m[0]} far more than chance"
        if w in self.know.young:
            return f"a {w} is a young {self.know.young[w]}"
        if w in self.know.isa:
            return f"a {w} is a {self.know.isa[w]}"
        if self.frames.pronoun(w):
            return f"'{w}' means the {self.frames.pronoun(w)} the story is about"
        heard = self.words.word.get(w, 0) + self.frames.heard.get(w, 0)
        if heard:
            meaningful, _ = self.frames.summary()
            does = [f"{k.split('|')[1]}: {p}" for k, p in meaningful.items() if k.split("|")[0] == w]
            if does:
                return f"'{w}' does something in stories: " + "; ".join(does[:3])
            return f"'{w}' is a grammar word: I heard it {heard} times, but it doesn't mean one thing on its own"
        return None

    def chat(self, text):
        """A question for the kindergarten region -> reply, or None if it isn't one."""
        t = text.strip()
        if self.is_story(t):
            return self.read_story(t)
        low = t.lower().strip(" ?.!")
        v, how = self.know.ask(low)
        m = re.fullmatch(r"is an? (\w+) an? (\w+)", low)
        if m and m[1] not in self.know.isa:
            return None                               # it never heard of it: let the English region say what it knows
        if how != "doesn't understand the question":
            return {"problem": t, "source": "language", "kind": "knowledge", "region": "language",
                    "answer": None if v is None else str(v), "how": how}
        if m := re.fullmatch(r"what (?:is|does|means?) (?:an? |the )?([a-z]+)(?: mean)?", low):
            said = self.meaning_of(m[1])
            if said:
                return {"problem": t, "source": "language", "kind": "word", "region": "language",
                        "answer": said, "how": "words from scenes"}
        return None

    def hear_fact(self, text):
        """'a zebra has four legs', 'a lamb says baa', 'a foal is a young horse' -> True if understood."""
        return self.know.hear(text)

    def summary(self):
        vocab = self.words.vocabulary()
        kinds = defaultdict(int)
        for f in vocab.values():
            kinds[f.split(":")[0]] += 1
        grammar = sorted((w for w, c in self.words.word.items() if c >= 20 and w not in vocab),
                         key=lambda w: -self.words.word[w])[:12]
        verbs = {v: f"{m[0]} / {m[1]}" for v in self.actions.effects if (m := self.actions.meaning(v))}
        meaningful, pronouns = self.frames.summary()
        frames = defaultdict(list)
        for k, p in meaningful.items():
            frames[k.split("|")[0]].append(p)
        examples = {w: ps[0] for w, ps in sorted(frames.items(), key=lambda kv: -len(kv[1]))
                    if w not in ("*",) and w.isalpha()}
        return {"vocabulary": len(vocab), "word_kinds": dict(kinds), "grammar_words": grammar,
                "facts": len(self.know.isa) + sum(len(p) for p in self.know.props.values()),
                "verbs": verbs, "pronouns": pronouns, "frames": len(meaningful),
                "frame_words": dict(list(examples.items())[:14]), "lessons": self.lessons, "exam": self.exam,
                "taught_meanings": {w: m["said"] for w, m in self.meanings.items()},
                "weights": 0, "counts": sum(len(r) for r in self.words.pair.values())}
