"""Reading a story by acting it out, with sentence frames LEARNED from examples.

The old reader had three fixed patterns ("X has N things", "how many ... does X have", he/she = the
person the story starts with). Here nothing about what a sentence does is written in:

  perception (fixed, like eyes for text)
      cuts the text into sentences and clauses, and sees what each word IS from what the brain
      already learned: a number, a person (a name it knows, a pronoun it learned, or a new word
      where a subject goes), a thing (a noun after a number, with its colour words), a day or a
      time of day. Everything else is just a word. "some" is a number it doesn't know yet.
  frames (learned)
      Each sentence comes with the scene after it. The brain tries every small explanation it can
      build from the numbers and the cells it already holds (Tom's apples = Tom's apples - 2, Ana's
      apples = Tom's apples + 3, Tom's apples = Tom's bags * 4 ...) and keeps the ones the scene
      makes true. Each word is credited with them, keyed by its FRAME: the word plus the order of
      the people, numbers, things and days around it ("gives|P_NTP": a person, gives, a number,
      a thing, a person). Over many stories, a word whose frame always comes with the same change
      has learned a meaning; words that come with everything (the, to, than) learn none. The frame
      shape on its own ("*|PNT") learns the default, which is how "X has N things" is learned.
      Questions are learned the same way, from the teacher's answer.
  pronouns (learned)
      he/she/his/her/him: a word that always comes with a boy (or a girl) being involved, and not
      with the other, refers back to the last boy (or girl).
  mental model
      cells (owner, thing, describing words) -> how many, each with its first value. A cell may
      hold an unknown ("some"); a later sentence that gives the total finds it.
"""
import re
from collections import defaultdict
from fractions import Fraction

from .coordination import Coordination, dec, factors, gcd_steps, group_steps, lcm_steps, percent_steps, unitary_steps
from .planner import Doubts
from .request import what_is_asked
from . import wordvec

# ---- numbers that may still hold an unknown -------------------------------------------------------


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


# ---- the mental model -------------------------------------------------------------------------------


class Situation:
    def __init__(self):
        self.units = []            # unit facts it was taught: {"big": [words], "small": [words], "k": n, "said"}
        self.cells = {}            # (owner, thing, frozenset(desc)) -> [first, now] (Lin)
        self.bound = {}            # unknown -> value, once a later sentence tells it
        self.unknowns = 0
        self.people = []           # names, most recently mentioned last
        self.met = []              # names, in the order the story met them
        self.gender = {}           # name -> "boy" / "girl" / None
        self.subject = None        # who the story is about right now (for "he", "are left", ...)
        self.thing = None          # what it is about right now (for "he ate 3 more")
        self.pending = {}          # known name not yet made a person -> the nouns its clause counted
                                   # (its own cells land ownerless; when the name later becomes a person
                                   #  those cells are claimed back, 'Connie has 323. Juan has 175 more')
        self.events = {}           # _CHANGE_EVENT: cell key -> the total that went OUT of / INTO it when
                                   # the cell was CREATED by a change statement with no balance told
                                   # ('a clown gave away 11' starts an event cell, not a balance)

    def unknown(self):
        self.unknowns += 1
        return Lin(0, {self.unknowns: 1})

    def read(self, owner, thing, desc, first=False):
        vals = [c[0 if first else 1] for (o, t, d), c in self.cells.items() if o == owner and t == thing and desc <= d]
        if not vals:                                   # 'each pack has 2 pears': the packs were '5 packs of pears'
            vals = [c[0 if first else 1] for (o, t, d), c in self.cells.items()
                    if o == owner and t.startswith(thing + " of ") and desc <= d]
        if not vals:
            return None
        total = Lin(0)
        for v in vals:
            total = total + v
        return total.bind(self.bound)

    def write(self, owner, thing, desc, new):
        new = new.bind(self.bound)
        old = self.read(owner, thing, desc)
        if old is not None and len(old.k) == 1 and new.known:          # now it can find the unknown
            (v, x), = old.k.items()
            self.bound[v] = (new.c - old.c) / x
            return
        key = (owner, thing, desc)
        delta = new - (old or Lin(0))
        if key in self.cells:
            self.cells[key][1] = self.cells[key][1] + delta
        else:
            self.cells[key] = [delta, delta]

    def mention(self, name, gender=None):
        if name not in self.met:
            self.met.append(name)
        if name in self.people:
            self.people.remove(name)
        self.people.append(name)
        if gender or name not in self.gender:
            self.gender[name] = gender

    def refer(self, gender):
        """Who a pronoun means: the person of that gender the story is about (the first one met), else
        the last person nobody told it about, else the last person."""
        for want in (gender, None):
            fits = [p for p in self.people if self.gender.get(p) == want]
            if fits:
                return min(fits, key=self.met.index) if want else fits[-1]
        return self.people[-1] if self.people else None

    def write_first(self, owner, thing, desc, v):
        """What it was at the start ('he had 12 apples initially'), told after what happened to it."""
        key, v = (owner, thing, desc), v.bind(self.bound)
        cell = self.cells.get(key)
        if cell is None:
            first = self.read(owner, thing, desc, first=True)
            if first is None:
                self.cells[key] = [v, v]
            elif len(first.k) == 1 and v.known:                 # the start of a total it is still missing a part of
                (x, k), = first.k.items()
                self.bound[x] = (v.c - first.c) / k
            elif (_FIRST_BASE and first.known and v.known and first.c != v.c and not first.k and not v.k):
                # the told start CONTRADICTS the parts' starts ('bought 2 purple and 2 green grapes;
                # he ALREADY HAD 3 grapes' -- the parts say 4 at first, the sentence says 3): the 3
                # is a BASE quantity the coloured parts do not cover, so the plain cell is written
                # and the total now reads base + parts (3 + 2 + 2 = 7).
                self.cells[key] = [v, v]
            return
        first = cell[0].bind(self.bound)
        if len(first.k) == 1 and v.known:
            (x, k), = first.k.items()
            self.bound[x] = (v.c - first.c) / k
        elif first.known and v.known and first.c != v.c:
            cell[1] = cell[1] + (v - first)
            cell[0] = v

    def see(self, truth, firsts=None):
        """Learning: the scene shows exactly who has how many now, and what each thing was at the start."""
        cells = {}
        for k, v in truth.items():
            first = Lin(firsts[k]) if firsts and k in firsts else self.cells[k][0] if k in self.cells else Lin(v)
            cells[k] = [first, Lin(v)]
        changed = [k for k in cells if k not in self.cells or self.cells[k][1].c != cells[k][1].c]
        self.cells = cells
        return changed

    def nouns(self):
        return {t for (_, t, _) in self.cells}


def lower_truth(truth):
    return {((o.lower() if o else None), t, d): v for (o, t, d), v in truth.items()}


# ---- perception ---------------------------------------------------------------------------------------

_TOKEN = re.compile(r"\d+(?:\.\d+)?|[a-z]+(?:[-'][a-z]+)*|[.?!,]")
_GLUE = {"the", "a", "an", "if", "then", "now", "and", ",", "so"}
_BREAK = {"and", ",", "then", "while", "but"}


def singular(w):
    irregular = {"sheep": "sheep", "fish": "fish", "children": "child", "men": "man", "feet": "foot", "mice": "mouse",
                 "candies": "candy", "money": "dollar", "people": "person", "cookies": "cookie", "movies": "movie",
                 "brownies": "brownie", "zombies": "zombie", "gives": "give", "takes": "take", "eats": "eat"}
    if w in irregular:
        return irregular[w]
    if w.endswith("ves") and len(w) > 4:
        return w[:-3] + ("f" if w[:-3] not in ("kni", "wi") else "fe")
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "sses", "oes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")) and len(w) > 3:
        return w[:-1]
    return w


def plural_looking(w):
    return singular(w) != w


def tokens(text):
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text.lower())        # 1,093 is one number
    t = re.sub(r"(\d)\s*%", r"\1 percent", t)                    # 20% -> 20 percent
    t = re.sub(r"\$\s*(\d+(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\b(mr|mrs|ms|dr)\.", r"\1", t)
    t = re.sub(r"'s\b", "", t)
    return _TOKEN.findall(t)


def sentences(text):
    """-> list of token lists; the last one may be a question."""
    out, cur = [], []
    for tok in tokens(text):
        if tok in ".?!":
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        out.append(cur)
    return out


def split_question(toks):
    """'if she got a total of 16 pencils how many ...' -> (statement part, question part); None if not a question."""
    for i in range(len(toks) - 1):
        if toks[i] in ("how", "what") and (toks[i] == "what" or toks[i + 1] not in ("is", "are", "was")):
            if toks[i] == "what" and i and toks[i - 1] == "at":
                i -= 1
            cond = [t for t in toks[:i] if t != ","]
            if cond and cond[0] == "if":
                cond = cond[1:]
            return cond, toks[i:]
    return None


class Lexicon:
    """What perception can see in a word, from what the brain has learned so far."""
    CONTEXT = True              # first a look over the whole story: what it uses a two-sense word as
    def __init__(self, words, frames, meanings=None):
        self.feats, self.senses = {}, {}
        for w in words.word:
            links = [(f, s) for f, s in words.links(w)[:3] if s > 0.5]
            fs = [f for f, s in links if s >= 0.7 * links[0][1]] if links else []
            if fs:
                self.feats[w] = fs
        for w in words.word:                              # a word that NAMES a colour and a thing ('orange'):
            base = singular(w)                            # the colour in one scene, the fruit in another
            linked = {f for x in (base, w, base + "s") if x in words.word for f, s in words.links(x)[:4] if s > 0.3}
            if f"colour:{base}" in linked and f"thing:{base}" in linked:
                self.senses[base] = [f"colour:{base}", f"thing:{base}"]
        self.context = set()                              # words this story uses as things (see read_context)
        self.units = {singular(w) for u in getattr(frames, "units", []) for w in u["big"] + u["small"]}   # taught units
        self.words, self.frames = words, frames
        # meanings the teacher gave ('red is a colour', 'migrating means flying away') beat its own statistics
        self.meanings = meanings or {}
        self.same = {w: m["same"] for w, m in self.meanings.items() if m.get("same")}
        for w, m in self.meanings.items():
            if m.get("feature"):
                self.feats[w] = [m["feature"]]
        # tier 2 (pretrained vectors): a word it has never heard may count as understood when the
        # vectors say it is very like a word it does know (`vlike`/`vknown` are computed once per word
        # and never saved, so the counts, the teacher's meanings and every exam stay earned)
        self.vlike, self.vknown = {}, None

    def _vec_known(self):
        """The words it really knows - heard at least 3 times, the same bar `familiar` uses - so a
        word it leans on is never itself a word it has barely met."""
        if self.vknown is None:
            self.vknown = [w for w in self.words.word
                           if self.words.word[w] + self.frames.heard.get(w, 0) >= 3] + list(self.meanings)
        return self.vknown

    def like_known(self, w):
        """Tier 2: an unheard word counts as understood when the pretrained vectors say it is very like
        a word it does know ('brought' ~ 'came', 'backpack' ~ 'bag', 'july' ~ 'april')."""
        if w in self.vlike:
            return self.vlike[w]
        hit = wordvec.nearest(w, self._vec_known())
        ok = hit is not None and hit[1] >= wordvec.MIN_FAMILIAR
        self.vlike[w] = ok
        return ok

    def expand(self, toks, depth=3):
        """Words (or phrases) the teacher explained by other words are read as those words; the longest first,
        and again for words explained by explained words ('migrated' -> 'flew away' -> 'went away')."""
        if not self.same or depth == 0:
            return toks
        new = self._expand_once(toks)
        return new if new == toks else self.expand(new, depth - 1)

    def _expand_once(self, toks):
        phrases = sorted(((k.split(), v) for k, v in self.same.items()), key=lambda kv: -len(kv[0]))
        out, i = [], 0
        while i < len(toks):
            for words, said in phrases:
                if toks[i:i + len(words)] == words:
                    out.extend(said)
                    i += len(words)
                    break
            else:
                out.append(toks[i])
                i += 1
        return out

    def _f(self, w, kind):
        base = singular(w)
        if base in self.senses or w in self.senses:       # a word with two senses: what this story uses it as
            key = w if w in self.senses else base
            as_thing = key in self.context or (w != base and any(f.startswith("thing:") for f in self.feats.get(w, [])))
            want = "thing" if as_thing else "colour"
            if kind in ("thing", "colour"):
                if kind != want:
                    return None
                for f in self.feats.get(w, []) + self.senses[key]:
                    if f.startswith(kind + ":"):
                        return f.split(":", 1)[1]
        for x in (w, base):
            for f in self.feats.get(x, []):
                if f.startswith(kind + ":"):
                    return f.split(":", 1)[1]
        return None

    def read_context(self, sentences_toks):
        """Before reading, a look over the whole story: a word with two senses ('orange') is a THING here if the
        story uses it like one somewhere: plural ('oranges'), or after a number, 'the/a', 'on' or 'of' with no thing
        word after it ('spends $19 on oranges', 'how many oranges'); before a thing ('orange balls') it describes."""
        self.context = set()
        for toks in sentences_toks:
            for i, w in enumerate(toks):
                base = singular(w)
                key = w if w in self.senses else base if base in self.senses else None
                if not key:
                    continue
                nxt = toks[i + 1] if i + 1 < len(toks) else ""
                before_thing = bool(nxt) and nxt.isalpha() and (bool(self._plain(nxt, "thing")) or plural_looking(nxt))
                prev = toks[i - 1] if i else ""
                if (w != base and not before_thing) or (not before_thing and (
                        prev[:1].isdigit() or prev in _DET or prev in ("many", "on", "of", "some", "more"))):
                    self.context.add(key)
        return self.context

    def _plain(self, w, kind):
        for x in (w, singular(w)):
            for f in self.feats.get(x, []):
                if f.startswith(kind + ":"):
                    return f
        return None

    def person(self, w):
        fs = self.feats.get(w)
        return fs[0].split(":")[1] if fs and fs[0].startswith("person:") else None

    def number(self, w):
        f = self._f(w, "count")
        return Fraction(f) if f and self.feats.get(w, [""])[0].startswith("count:") else None

    def thing(self, w):
        if singular(w) in self.units or w in self.units:   # a unit it was taught ('m', 'g', 'weeks') is a thing
            return singular(w)
        return self._f(w, "thing")

    def size(self, w):
        return self._f(w, "size")

    def colour(self, w):
        return self._f(w, "colour")

    def day(self, w):
        fs = self.feats.get(w)
        return w if fs and fs[0].split(":")[0] in ("day", "time") else None

    def known(self, w):
        return w in self.words.word or w in self.frames.heard or w in self.meanings

    def familiar(self, w, times=3):
        if any(w in k.split() for k in self.meanings):     # a word of a phrase the teacher explained
            return True
        if w in self.meanings or self.words.word.get(w, 0) + self.frames.heard.get(w, 0) >= times:
            return True
        return self.like_known(w)                          # tier 2: the vectors say it is like a word it knows

    def pronoun(self, w):
        return self.frames.pronoun(w)


_DET = {"the", "a", "an", "his", "her", "their", "my", "your", "its", "our", "this", "that", "these", "those", "each",
        "every"}
_BETWEEN = {"more", "fewer", "less", "new", "old", "extra", "of", "whole", "equal"}
_SMALL = {"of", "them", "they", "it", "him", "his", "her", "their", "and", "or", "the", "a", "an", "to", "from",
          "than", "is", "are", "was", "were", "with", "for", "at", "in", "on", "each", "every", "more", "fewer", "less"}
_WHERE = {"at", "in", "on", "for", "with", "after", "to", "from", "into", "near", "by", "before", "during"}
_NOT_NOUNS = {"same", "total", "lot", "few", "little", "most", "rest", "other", "next", "first", "last", "start",
              "beginning", "end", "more", "half", "day", "way", "time", "week", "year", "moment", "while"}
_FUNCTION = _DET | _SMALL | _BETWEEN | _NOT_NOUNS | _WHERE | _GLUE | _BREAK   # words with a grammar job, not things

# --- change-family readings (measured 2026-10-08): -----------------------------------
# The verb part is landed: for the change-family verbs a reading that departs from / arrives at an
# ALREADY-KNOWN quantity (`filled` - the 8, `read` - the 11) competes with the plain overwrite. The
# delta-question part is landed too: a question that asks how many CHANGED reads the cell's
# now - first and drops the naive 'it is now' reading of that same cell. The noun part measured
# g1-neutral and g3-negative and stays off.
_CHANGE_FIX = False            # master switch (noun relaxation + verb departure/arrival + delta question)
_CHANGE_FIX_NOUN = False       # the weak-frame nouns part only (measured: g1-neutral, g3-negative -> stays off)
_CHANGE_FIX_VERB = True        # the change-family verb part (landed 2026-10-08: measured +g1 26->29, worlds flat)
_CHANGE_FIX_DELTA = True       # a question that asks how many CHANGED ('how many were added') reads the cell's now - first
_CHANGE_PROMOTE = True         # LANDED 2026-10-09 (measured): the departure the change verb requires is already in
                               #     the frame table but LOSES on sureness to the plain overwrite -- move it ahead.
                               #     ('she read 11 of the pages': 'read|*' P1.T1-N1 0.75 vs 'read|P_NT' N1 0.89).
                               #     Measured with _RELCL_FIX: guards identical, g1 answers 40->41, g3 48->49,
                               #     nodoubt+both 28->29 right of 34 claims (82%->85% true).
_CHANGE_FIX_CELLS = False      # CF REJECTED (2026-10-08): a change clause whose own target cell holds nothing yet
                               #     departs from / arrives at the known cell of the SAME noun. Fixed ASDiv marbles
                               #     (+1 answer) but worlds P1-P6 -2..3pt each and kindergarten -10 (days 40->30):
                               #     the same noun under ANOTHER owner gets hit instead of the clause's own.
_CHANGE_FIX_TOPIC = False      # CF REJECTED together with CELLS: ... else the story's topic cell.
_CHANGE_FIX_OWNERLESS = True   # LANDED 2026-10-09 (measured): a change clause whose own target is an
                               #     owner the story never gave that noun ('2 marbles are taken out OF
                               #     THE BASKET' -> basket's marble, empty) departs from/arrives at the
                               #     LONE ownerless known cell of the same noun. Narrower than the
                               #     rejected CELLS (never another owner's): worlds/real stories/kg
                               #     389 (days 40/40)/recipes identical, g1 always answers 46->47
                               #     (marbles 2->0 right), nodoubt release 32->33 right of 34 (94%->97%).
_CHANGE_EVENT = True            # LANDED 2026-10-09 (measured): a change statement that CREATES a cell with
                               #     no balance told starts a TALLY of what went out, not a balance
                               #     ('a clown gave away 11' -> 11 given, nothing told about now).
                               #     Later OUT on the same cell accumulates (give 3 more -> 14, not
                               #     depart to 8); a stative write ('now he has 3') sets first =
                               #     now + tally so the at-first reading is the total given/sold
                               #     (3+12=15); a reuse of the cell for another quantity drops the
                               #     mark ('spent $2' then 'bought for $7 each'). A clause that also
                               #     states a balance ('spent a TOTAL of', 'initially had') never
                               #     starts a tally. Measured: guards identical (worlds 96.0/91.4/
                               #     89.5/90.2/88.3/83.8, stories 25/11/13/6/9/9, kg 389/400,
                               #     recipes 0/0/200); g1-g4 no right-answer losses and no claim
                               #     changes, +answerok on baker 12->15, Tom 16->18, Roger 9->13,
                               #     clown 3->14, clown-left 6->61, Zoe 50->84, Robyn 27->61,
                               #     chef 2->7; nodoubt release 29->31 right of 34 claims (85%->91%
                               #     true). CF iterations rejected along the way: a question-side
                               #     tally reading that beat rate/rest questions (Jack 3285->9,
                               #     $700 139->700), clause-level verb detection that marked a
                               #     balance write inside a 'before...gave' clause (Simon 27->34).
_FIRST_BASE = True              # LANDED 2026-10-09: a told at-first that CONTRADICTS the parts' starts
                                #     is a base the parts don't cover ('bought 2 purple and 2 green grapes;
                                #     he ALREADY HAD 3 grapes' -> the parts say 4 at first, the sentence
                                #     says 3 -> the 3 is a base, plain cell 3, now reads 3+2+2=7).
                                #     Measured: g1 row diffs ONLY grapes (4->7 right, always answers
                                #     45->46) and Debby (None->3, still wrong, unclaimed either way);
                                #     worlds/real stories/kg 389/400/recipes identical; g2-g6 claims
                                #     identical; nodoubt release 31->32 right of 34 claims (91%->94%),
                                #     grapes claimed right; remaining wrong claims: marbles, pennies.
_WORD_DOUBT_RELEASE = True     # LANDED 2026-10-09 (measured, the doubt release): a word's past mistake
                                #     does NOT block a claim on a DIFFERENT reading of that word. The
                                #     doubt memory marks a word globally ('basket' earned it in the
                                #     marbles row) and then blocks every later story that uses it, even
                                #     when the reading here is a different frame. Only a doubt about the
                                #     reading itself -- two sure readings disagreeing ('two ways of
                                #     reading') or a working that did not check out -- still blocks.
                                #     Measured g1 test: doubt-blocked 23->6, claims 11->28, 28/28 = 100%
                                #     true (the 6 held back are live rival-reading doubts, incl. the one
                                #     wrong row). The blanket release (nodoubt) would claim 33/34 = 97%,
                                #     wrongly claiming the pennies row; this narrow release keeps it out.
                                #     Worlds/real stories/kindergarten/recipes untouched (a doubt is only
                                #     consulted at claim time). Gate (>=29 right, >=80% true) now sits one
                                #     honest right claim away instead of twelve stale-doubt ones.
_RIVAL_TIEBREAK = True          # LANDED 2026-10-09 (measured; THE GATE IS MET): a rival-reading doubt
                                #     fires only when the rival is AT LEAST AS SURE as the reading
                                #     chosen. The answer loop lets any candidate within 0.12 c of the
                                #     best compete, so a merely-close rival is not a genuine second
                                #     opinion -- the surest reading already won. Rivals now carry
                                #     their sureness ((value, c) tuples).
                                #     Measured g1 test: claims 28->32, right 28->31 = 97% true
                                #     (Cody 12, Megan 16, Victor 12 released right; pennies 0
                                #     released wrong; baker 15 / clown 14 stay blocked -- their
                                #     learned rivals are genuinely surer than the fix's injected
                                #     c=0.8). GATE (>=29 right of 97 at >=80% true): 31/32 = 97%.
                                #     Guards: worlds P1-P6 scores identical, real stories gain
                                #     right claims at every level (+1/+3/+5/+7/+1/+1, precision
                                #     ~73-83%), kindergarten 389/400 and recipes 5/5 and chat
                                #     0/0/200 identical; g2-g6 claims 40->43/47->54/16->20/5->6/7->9
                                #     with precision not degraded.
_NAMES_FIX = True              # LANDED 2026-10-08 (measured): a known word where a name goes is tagged
                               #     person so the clause gets its OWN cells and the taught cross-person
                               #     pair 'P1 = N1 + P2' can be offered ('Ellen has 6 more than Marin').
                               #     Rule C: subject/after-'than' of a comparative clause. Rule S: the
                               #     subject of a quantity clause only when the word was ALREADY made a
                               #     person earlier in this story (the comparative's second person,
                               #     coming back in its own statement). Its earlier ownerless counts are
                               #     claimed back when it becomes a person. Measured: worlds P1-P6 and
                               #     kindergarten 389/400 flat, g1 answers 31->33 (Ellen 9->15, Brian
                               #     7->11, doubt-blocked claims), g3 right 4->5 claims 9->8 answers
                               #     46->47, g2/g4-g6/recipes flat. Converting EVERY known subject
                               #     measured g1-negative: it splits the shared ownerless cell that
                               #     two-clause sums/differences read ('Marin has 9 and Donald has 2'
                               #     11->9, Ryan chain 22->None, Adam/Michele difference claim lost).
_NOUN_SHAPE_MAX = 15                       # a word whose Frames rows total this many lessons is not a verb
_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
               "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
               "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
               "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
               "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
               "flew", "added", "gained", "read"}
_OUT_VERBS = {"sold", "gave", "gaveaway", "lost", "ate", "used", "spent", "removed", "deleted",
              "finished", "read", "filled", "threw", "took", "taken", "eaten"}
_IN_VERBS = {"bought", "got", "received", "collected", "picked", "found", "brought"}
# '1 flies away' -- a departure word that is ALSO a plural noun ('two flies sat'). Only after
# 'away' (or 'off') is it unambiguously the doing-verb, so perceive tags it L and the change
# injection can depart from the story's cell ('4 birds ... 1 flies away' -> 3).
_FLY_FIX = True               # LANDED 2026-10-08 (measured): '1 flies away' is a departure, not the
                               #     plural noun. Perceive tags the fly-verb as L only right before
                               #     'away'/'off' (a bare 'two flies sat' stays a noun), chunk() no
                               #     longer swallows it after a number, and the change injection
                               #     departs from the story's cell ('4 birds ... 1 flies away' -> 3).
                               #     Measured: g1 row diff ONLY the birds row (4->3), worlds/kg/
                               #     recipes flat, g1 answers 37->38, nodoubt precision 74%->76%.
_FLY_AWAY = {"flies", "fly", "flew", "flown", "flying"}
# The question asks for the CHANGED amount when it names one of these doing-verbs... but not when it
# asks what is left, what there was before, or a total -- those are other requests over the same cells.
_DELTA_Q = _OUT_VERBS | _IN_VERBS | ((_FLY_AWAY if _FLY_FIX else set()) |
        {"add", "added", "give", "gives", "giving", "given", "eat", "eats",
         "eating", "delete", "deletes", "deleting", "sell", "sells",
         "selling", "spend", "spends", "spending", "take", "takes",
         "taking", "use", "uses", "using", "finish", "finishing", "buy",
         "buys", "buying", "gets", "getting", "collect", "collecting"})
_NO_DELTA_Q = {"left", "remain", "remains", "now", "begin", "beginning", "start", "before", "first",
               "together", "altogether", "total", "each", "again", "more", "need", "needs", "needed",
               "have", "has", "had", "are", "is", "there", "still", "all", "in"}
# The question asks for the AMOUNT BEFORE when it says so ('before', 'to begin with', 'in the
# beginning'): the cell already keeps its at-first value next to the current one, so the answer is
# that first value -- not the quantity as it stands now. A difference or what-is-left request over
# the same cells is a different question and stays out.
_BEFORE_FIX = True             # LANDED 2026-10-08 (measured): a before-question reads the cell's at-first
                               #     value instead of the quantity as it stands now. Measured: worlds
                               #     P1-P6 flat, g1 answers 33->35 (oranges 3->8, chef 4->19), g2 +1,
                               #     g3 +1, kindergarten 389/400 + recipes flat, no right-count losses.
                               #     Rows whose body never made a first!=now cell (owner-split 'picked
                               #     from her tree', departure with no base, unregistered noun) stay
                               #     open: statement-side gaps, not a question-reading gap.
_BEFORE_Q = {"before", "originally", "initially", "begin", "beginning", "first", "start", "started"}
_NO_BEFORE_Q = {"left", "remain", "remains", "difference", "differences", "now", "total", "totals",
                "together", "altogether", "more", "again", "still", "next"}
# 'How many muffins does first grade bake IN ALL': the asked noun lives in several owner cells
# (18 + 20 + 17) and the question is the one place that wants their total -- the clause's own
# slots only reach one of them, so the sum candidate is written straight from the cells.
_LIST_FIX = True              # LANDED 2026-10-08 (measured): a total question ('in all', 'together')
                               #     sums every cell of the asked noun WITH A NAMED OWNER -- at least
                               #     three of them (a genuine list), no value dividing another (a
                               #     part next to its own total), never ownerless cells (those hold
                               #     the context total or another quantity in the same unit). The
                               #     expression grammar takes two terms, so the sum is folded into
                               #     one atom. Measured: g1 row diff ONLY muffins (18->55, +1 right
                               #     answer), g3 row diff EMPTY, worlds/kg/recipes identical,
                               #     nodoubt precision 76%->79%. Rejected variants recorded: sum of
                               #     every cell (worlds -1pt each, kg 389->382 each-kind 40->33),
                               #     >=2 owner cells (g3 farm 60->77, butterflies 4764->29).
_TOTAL_Q = re.compile(r"\b(?:in all|altogether|in total|all together|together)\b")
_RATE_FIX = True              # LANDED 2026-10-08 (measured): a rate statement ('ate 5 apples EVERY
                               #     HOUR') whose own reading failed (a departure from an unknown
                               #     base: -5+unknown) writes a POSITIVE known per-unit cell -- but
                               #     only when the frame put the cell under the unit word, and only
                               #     when the chosen reading was unknown or negative (the teacher's
                               #     own rate rows 'reads 5 books a day' evaluate known+positive and
                               #     keep their learned keys). An end-of-time question ('at the END
                               #     OF 3 hours') answers N1*slot for whichever slot reads a
                               #     TIME-OWNED cell, in front of the learned 'end of' doubling guess.
                               #     Measured: g1 row diff ONLY apples (5->15, +1 right answer),
                               #     g3 diff EMPTY, worlds/kg (days 40/40)/recipes identical,
                               #     nodoubt precision 79%->82% (28 right / 34 claims).
_RATE_Q = re.compile(r"\b(?:end of|after|within)\b")
_RATE_PHRASE = re.compile(r"\b(?:every|each|per|a|an)\s+(day|hour|week|month|year|night|minute|second)s?\b")
_TIME_UNITS = {"day", "hour", "week", "month", "year", "night", "minute", "second"}
_RELCL_FIX = True             # LANDED 2026-10-09 (measured): a known verb right after a RELATIVE pronoun ('a book
                              #     THAT HAS 17 pages') is the verb of the relative clause, not a thing --
                              #     it made 'has' a cell thing (`book's has = 17`) and hid the 17 pages
                              #     from `book's page`, so 'how many left to read' answered 11.
                              #     Only after that/which/who: the first version excluded ANY verb after a
                              #     determiner and broke 'the LEFT' (furniture row 12 -> no answer, g1).
                              #     Measured (with _CHANGE_PROMOTE): worlds P1-P6 + real stories + kg 389/400
                              #     + recipes identical, g1 answers 40->41 (book 11->6), g3 48->49 (Alexa
                              #     58->19), no right-answer losses on g1-g4; nodoubt+both 28->29 right of 34
                              #     claims (82%->85% true).
_RELCL_DET = {"that", "which", "who"}
# A count of things can never be negative. A reading that evaluates below zero is not a possible
# answer to 'how many' -- it currently claims (chairs -9, fair -12) only because nothing else
# worked out; dropping it yields an honest no-answer instead of a nonsense claim.
_NONNEG_FIX = True             # LANDED 2026-10-08 (measured): never claim a negative -- no quantity in
                               #     these stories (nor a difference of quantities) goes below zero.
                               #     A negative reading claimed only because nothing else worked out;
                               #     dropping it exposed the correct difference on two rows (plums
                               #     -3->3, chairs -9->12) and removed nonsense claims (fair -12).
                               #     Measured: worlds P6 83.5->83.8 (rest flat), g1 answers 35->37,
                               #     g2 right 5->6, g3/g4 wrong claims -1 each, kindergarten 389/400
                               #     + recipes flat, nodoubt precision 70%->74%.


def perceive(toks, lex, sit):
    """Tokens -> items: ('P', word, gender, pronoun?) ('N', value or None) ('T', noun, adjs) ('D', word) ('L', word)."""
    toks = lex.expand(toks) if hasattr(lex, "expand") else toks
    out, i = [], 0
    nouns = sit.nouns()

    def nounish(w):
        if w in _SMALL:
            return False
        return bool(lex.thing(w)) or singular(w) in nouns or lex.frames.is_noun(w) or             (not lex.known(w) and w.isalpha() and len(w) > 1 and not lex.pronoun(w))

    def chunk(j, question=False):
        """After a number (or 'how many'): [known words] [colour/new adjectives] noun [of noun] -> new index."""
        lits, adjs, k = [], [], j
        while k < len(toks) and k < j + 5:
            w = toks[k]
            if getattr(lex, "units", None) and singular(w) in lex.units and not adjs and not lits:
                out.append(("T", singular(w), (), True))
                k += 1
                if k + 1 < len(toks) and toks[k] == "of" and nounish(toks[k + 1]) and toks[k + 1] not in ("the", "a"):
                    out[-1] = ("T", f"{singular(w)} of {singular(toks[k + 1])}", (), True)
                    k += 2
                return k
            if w in ".?!," or w[0].isdigit() or lex.person(w) or lex.pronoun(w) or lex.day(w) or w == "some" or \
                    w in ("they", "them", "it", "him", "his", "her", "their"):
                return j
            nxt = toks[k + 1] if k + 1 < len(toks) else ""
            if (lex.colour(w) or (not lex.known(w) and not plural_looking(w))) and nxt and nounish(nxt) and \
                    not (lex.thing(w) and not lex.colour(w)):
                adjs.append(w)
                k += 1
                continue
            if nounish(w):
                if _FLY_FIX and w in _FLY_AWAY and k + 1 < len(toks) and toks[k + 1] in ("away", "off"):
                    return j                  # '1 flies away': the doing-phrase, not a counted noun
                noun = singular(w)
                k += 1
                if k < len(toks) and not plural_looking(w) and plural_looking(toks[k]) and toks[k] not in _SMALL and \
                        not lex.known(toks[k]) and not lex.person(toks[k]):
                    adjs.append(w)                           # 'bird families', 'apple trees': the last word is the thing
                    noun = singular(toks[k])
                    k += 1
                if k + 1 < len(toks) and toks[k] == "of" and nounish(toks[k + 1]) and toks[k + 1] not in ("the", "a"):
                    noun = f"{noun} of {singular(toks[k + 1])}"
                    k += 2
                out.extend(("L", x) for x in lits)
                out.append(("T", noun, tuple(sorted(adjs)), True))
                return k
            if w in _BETWEEN or lex.size(w):
                lits.append(w)
                k += 1
                continue
            return j
        return j

    def subject_slot():
        """A new word where a subject goes: the start of a clause, or after 'than'."""
        prev = [x for x in out[-4:]]
        if prev and prev[-1][0] == "L" and prev[-1][1] == "than":
            return True
        if prev and prev[-1][0] == "L" and prev[-1][1] == "and" and len(prev) > 1 and prev[-2][0] == "P":
            return True
        back = []
        for x in reversed(out):
            if x[0] == "L" and x[1] in _BREAK:
                break
            back.append(x)
        return all(x[0] == "L" and x[1] in _GLUE for x in back)

    def where_phrase(j):
        """'in the box', 'at the park': a place word after a preposition and the/a/his."""
        k = j - 1
        while k >= 0 and lex.colour(toks[k]):
            k -= 1
        return k >= 1 and toks[k] in _DET - {"each", "every"} and toks[k - 1] in _WHERE

    def after_det(j):
        """Right after the/a/his (and maybe colour words): where a thing's name goes."""
        k = j - 1
        while k >= 0 and lex.colour(toks[k]):
            k -= 1
        if not (k >= 0 and toks[k] in _DET and k != j):
            return False
        if toks[k] in ("each", "every"):                     # 'ride in each tent': a thing, as in the other two checks
            return True
        return not (k >= 1 and toks[k - 1] in _WHERE)        # 'at the park', 'for his birthday': where, not what

    def after_relpron(j):
        """Right after that/which/who: the verb of a relative clause ('a book THAT HAS 17 pages'),
        which is doing, not a thing -- 'the LEFT' keeps its noun (determiner 'the' is not one)."""
        k = j - 1
        while k >= 0 and lex.colour(toks[k]):
            k -= 1
        return k >= 0 and toks[k] in _RELCL_DET

    while i < len(toks):
        w = toks[i]
        if w[0].isdigit():
            below = toks[i + 1:i + 4]                       # '10 degrees below zero' is -10 (taught in S1)
            sign = -1 if ("below" in below and "zero" in below[below.index("below"):]) else 1
            out.append(("N", sign * Fraction(w)))
            if i + 1 < len(toks) and toks[i + 1] == "percent":
                out.append(("L", "percent"))
                i += 2
                continue
            i = chunk(i + 1)
            continue
        if w == "some" and i + 1 < len(toks) and toks[i + 1] not in ("of",):
            out.append(("N", None))
            i = chunk(i + 1)
            continue
        if w == "some" and i + 2 < len(toks) and toks[i + 1] == "of" and toks[i + 2] in ("the", "them", "his", "her"):
            out.append(("N", None))                          # 'some of the balls': an amount it isn't told
            i = chunk(i + 3) if toks[i + 2] != "them" else i + 3
            continue
        if lex.number(w) is not None and i + 1 < len(toks) and (w != "one" or nounish(toks[i + 1])):
            n, i = lex.number(w), i + 1
            if i < len(toks) and toks[i] == "hundred":          # 'three hundred and forty-two': counting by hundreds
                n, i = n * 100, i + 1
                if i + 1 < len(toks) and toks[i] == "and" and lex.number(toks[i + 1]) is not None:
                    n, i = n + lex.number(toks[i + 1]), i + 2
            out.append(("N", n))
            i = chunk(i)
            continue
        if (w in ("many", "much") and out and out[-1] == ("L", "how")) or w == "what":
            out.append(("L", w))
            i = chunk(i + 1, question=True)
            continue
        if w in ("they", "them"):                            # fixed: the last two it heard about
            out.append(("P", w, "plural", True))
            i += 1
            continue
        if w in ("mr", "mrs", "ms", "miss", "dr") and i + 1 < len(toks) and toks[i + 1].isalpha():
            i += 1                                           # 'Mrs. Hilt': the title belongs to the name
            continue
        if lex.person(w):
            out.append(("P", w, lex.person(w), False))
        elif w in sit.people and sit.gender.get(w) != "thing":
            out.append(("P", w, sit.gender.get(w), False))  # someone it already met in this story
                                       # (known or not: a name made a person here stays a person --
                                       #  'Juan has 175 more than Connie' then 'does JUAN have?'
        elif w == "it" and lex.pronoun(w) != "thing":         # before it learned 'it', it is just a word
            out.append(("L", w))
        elif lex.pronoun(w) and w in ("his", "her", "their", "its") and i and toks[i - 1] in _WHERE:
            out.append(("L", w))                             # 'in his room': part of where it happened
        elif lex.pronoun(w):
            out.append(("P", w, lex.pronoun(w), True))
        elif lex.day(w) or (lex.colour(w) and not (i + 1 < len(toks) and nounish(toks[i + 1]))):
            out.append(("D", w))                             # a day, or a colour said of them ('22 are red')
        elif (lex.thing(w) or (singular(w) in nouns and singular(w) != w or w in nouns)) and where_phrase(i):
            out.append(("L", w))
        elif _FLY_FIX and w in _FLY_AWAY and i + 1 < len(toks) and toks[i + 1] in ("away", "off"):
            out.append(("L", w))                      # '1 flies away': the doing-verb, not the noun
        elif lex.thing(w) or (singular(w) in nouns and singular(w) != w or w in nouns):
            adjs = []
            while out and out[-1][0] == "L" and lex.colour(out[-1][1]):
                adjs.append(out.pop()[1])
            out.append(("T", singular(w), tuple(sorted(adjs))))
        elif after_det(i) and w.isalpha() and not lex.colour(w) and not lex.number(w) and \
                (i + 1 >= len(toks) or toks[i + 1] != "of") and w not in _NOT_NOUNS and \
                not (_RELCL_FIX and w in _VERB_WORDS and after_relpron(i)):
            adjs = []
            while out and out[-1][0] == "L" and (lex.colour(out[-1][1])):
                adjs.append(out.pop()[1])
            out.append(("T", singular(w), tuple(sorted(adjs))))
        elif not lex.known(w) and w.isalpha() and subject_slot():
            out.append(("P", w, None, False))
        # NOTE (2026-10-07): an earlier version tagged words whose word_property says 'verb' as
        # ('V', w) here. It silently broke the brain: keys() only offers word frames for 'L' items,
        # so tagging a verb ('ate', 'gave') removed every frame keyed on that word, the lesson could
        # no longer teach 'he ate 4 apples -> take away', and the kindergarten exam fell 360/400 ->
        # 258/400 with P1 at 78%. Verbs stay 'L'; keys() positions them by sig instead.
        else:
            out.append(("L", w))
        i += 1
    return out


def _name_slot(lex, w):
    """A known word where a name goes: not grammar, not a verb (checked against the taught frames too,
    so 'went'/'put' after a person stay out even though they are missing from _VERB_WORDS)."""
    if not w.isalpha() or w in _FUNCTION or w in _VERB_WORDS or w in ("there", "here"):
        return False
    return "verb" not in lex.frames.word_property(w)


def clauses(items, lex=None, sit=None):
    """Split 'Tom has 3 apples and 5 pears' / '18 kids on monday 15 kids on tuesday'; fill in what a
    clause leaves out from the clause before ('5 pears' -> 'Tom has 5 pears')."""
    segs = [[]]
    for idx, it in enumerate(items):
        cur = segs[-1]
        has_n = any(x[0] == "N" for x in cur)
        if it[0] == "L" and it[1] in _BREAK and has_n and _number_ahead(items, idx + 1):
            segs.append([("L", "then")] if it[1] == "then" else [])
            continue
        if it[0] == "N" and has_n and cur and cur[-1][0] in ("T", "D"):
            segs.append([it])
            continue
        cur.append(it)
    out = []
    for seg in segs:
        if not seg:
            continue
        if any(x[0] == "P" and (x[2] or x[3]) for x in seg):       # someone it knows is the subject, so a new
            seg = [("L", x[1]) if x[0] == "P" and not x[2] and not x[3] else x for x in seg]   # word isn't a person
        if _NAMES_FIX and lex is not None and any(x[0] == "N" for x in seg) and \
                any(x[0] == "T" for x in seg):
            # 'Ellen has six more balls than Marin': Ellen/Brian/Paul sit in the pretrained word table
            # (known=True), so perceive refuses to tag them as new people, the clause keeps ONE cell
            # (the base person's, or ownerless) and the taught pair 'P1 = N1 + P2' can never be offered.
            comp = any(x[0] == "L" and x[1] in ("more", "fewer", "less") for x in seg) and \
                   any(x[0] == "L" and x[1] == "than" for x in seg)
            spots = []
            if seg[0][0] == "L" and _name_slot(lex, seg[0][1]) and \
                    (comp or (sit is not None and seg[0][1] in sit.people and
                              not any(x[0] == "P" for x in seg))):
                spots.append(0)
            if comp:
                i = next((k for k, x in enumerate(seg) if x[0] == "L" and x[1] == "than"), None)
                if i is not None and i + 1 < len(seg) and seg[i + 1][0] == "L" and \
                        _name_slot(lex, seg[i + 1][1]):
                    spots.append(i + 1)
            for i in spots:
                name = seg[i][1]
                seg[i] = ("P", name, None, False)
                if sit is not None:                     # its earlier ownerless counts are its own after all
                    owed = sit.pending.pop(name, set())
                    for key in [k for k in sit.cells if k[0] is None and k[1] in owed]:
                        sit.cells[(name, key[1], key[2])] = sit.cells.pop(key)
            if sit is not None and not spots and seg[0][0] == "L" and _name_slot(lex, seg[0][1]):
                sit.pending.setdefault(seg[0][1], set()).update(x[1] for x in seg if x[0] == "T")
        lead = [x for x in seg if not (x[0] == "L" and x[1] == "then")]
        if out and lead and lead[0][0] == "N":
            prev = out[-1]
            first_n = next(k for k, x in enumerate(prev) if x[0] == "N")
            seg = [x for x in prev[:first_n] if not (x[0] == "L" and x[1] == "then")] + seg
        out.append(seg)
    return out


def _number_ahead(items, start):
    for x in items[start:]:
        if x[0] == "L" and x[1] in _BREAK:
            return False
        if x[0] == "N":
            return True
    return False


def unfamiliar(clause, lex):
    """Words of the clause it never really met, except new nouns: a new word after the/a/his... (or after
    to/from/with/than) names a thing or a place ('at the park', 'for his birthday'); it can still follow the
    story. A new word anywhere else may be what HAPPENED (a verb), so it can't."""
    out, prev, in_np = [], None, False
    for it in clause.items:
        if it[0] != "L" or not it[1].isalpha():
            prev, in_np = None, False
            continue
        w = it[1]
        if lex.familiar(w):
            in_np = False
        elif in_np or prev in _DET or prev in ("to", "from", "with", "than", "of"):
            in_np = True
        else:
            out.append(w)
        prev = w
    return out


class Clause:
    """One clause, seen as slots: people P1 P2, things T1 T2, days D1 D2, numbers N1 N2."""
    WIDE = True                     # a question about someone keeps everything they have in mind

    def __init__(self, items, sit, learning=False):
        self.items = items
        self.persons, self.things, self.days, self.nums, self.owners = [], [], [], [], []
        self.thing_subject = None
        first_slot = next((it for it in items if it[0] != "L"), None)
        for it in items:
            if it[0] == "P":
                names = sit.people[-2:] if it[2] == "plural" else [sit.refer(it[2]) if it[3] else it[1]]
                for name in names:
                    if not it[3]:
                        sit.mention(name, it[2])
                    elif name:
                        sit.mention(name)
                    if name and name not in self.persons:
                        self.persons.append(name)
            elif it[0] == "T" and (it[1], it[2]) not in self.things:
                self.things.append((it[1], it[2]))
                if len(it) < 4:                              # a thing not counted here can own things
                    self.owners.append(it[1])
                if it is first_slot and len(it) < 4 and \
                        not any(x[0] == "L" and x[1] in ("each", "every", "there") for x in items[:3]):
                    sit.mention(it[1], "thing")              # 'the game starts ...': a thing the story is about
                    self.thing_subject = it[1]
            elif it[0] == "D" and it[1] not in self.days:
                self.days.append(it[1])
            elif it[0] == "N":
                self.nums.append(Lin(it[1]) if it[1] is not None else (None if learning else sit.unknown()))
        # owners: the people in the clause, then the things it names (things can own things: 'a pen costs 3
        # dollars'); with no people, the one the story is about comes last ('each bag has 4 apples' -> Tom's)
        if self.persons:
            self.P = (self.persons[:2] + [n for n in self.owners if n not in self.persons])[:4]
        else:
            self.P = self.owners[:3] + ([sit.subject] if sit.subject not in self.owners else [])
        if None not in self.P and len(self.P) < 4 and \
                any(o is None and t in [n for n, _ in self.things] for o, t, _ in sit.cells):
            self.P = self.P + [None]                   # 'how many days does she need?': and the apples lying there
        holders = [n for n, _ in self.things if n not in self.P and any(o == n for o, _, _ in sit.cells)]
        if holders and len(self.P) < 4:                # 'how many tables?': and what each table holds
            self.P = self.P + holders[:4 - len(self.P)]
        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')
        self.T = self.things[:3]
        if sit.thing and sit.thing[0] not in [n for n, _ in self.T]:
            self.T = self.T + [sit.thing]                    # what the story is about stays in mind
        self.D = self.days[:2]
        self.sig = "".join(it[0] for it in items if it[0] != "L")

    def text(self):
        return " ".join(str(it[1]) if it[0] != "N" else ("some" if it[1] is None else str(it[1])) for it in self.items)

    def setting(self):
        """Positions of where/when phrases ('at the park', 'for his birthday', 'in the garden'): they say where
        it happened, not what happened, so they carry no meaning of their own."""
        out, items = set(), self.items
        for i, it in enumerate(items[:-1]):
            nxt = items[i + 1]
            after = items[i + 2] if i + 2 < len(items) else None
            if it[0] == "L" and it[1] in _WHERE and nxt[0] == "L" and nxt[1] in _DET - {"each", "every"} and \
                    not (after and after[0] == "L" and after[1] in _NOT_NOUNS):
                j = i
                while j < len(items) and items[j][0] == "L":
                    out.add(j)
                    j += 1
        return out

    def keys(self):
        """(rank, key): the word in its frame, the word anywhere, the frame shape, anything."""
        out, slots, seen = [], 0, set()
        skip = self.setting()
        for i, it in enumerate(self.items):
            if it[0] != "L":
                slots += 1
                continue
            w = it[1]
            if w in (",",) or w in seen or i in skip:
                continue
            seen.add(w)
            out += [(3, f"{w}|{self.sig[:slots]}_{self.sig[slots:]}"), (2, f"{w}|*")]
        return out + [(1, f"*|{self.sig}"), (0, "*")]

    def labels(self):
        for i in range(len(self.P)):
            for j in range(len(self.T)):
                for k in [None] + list(range(len(self.D))):
                    yield f"P{i + 1}.T{j + 1}" + (f"@D{k + 1}" if k is not None else "")

    def cell(self, label):
        m = re.fullmatch(r"P(\d)\.T(\d)(?:@D(\d))?", label.replace("F:", ""))
        i, j, k = int(m[1]) - 1, int(m[2]) - 1, m[3]
        if i >= len(self.P) or j >= len(self.T) or (k and int(k) - 1 >= len(self.D)):
            return None
        noun, adjs = self.T[j]
        return self.P[i], noun, frozenset(adjs) | ({self.D[int(k) - 1]} if k else set())

    def atoms(self, sit, question=False, learning=False):
        out = {}
        for k, n in enumerate(self.nums):
            if n is not None:
                out[f"N{k + 1}"] = n
        asked = [n for n, _ in self.things]
        owns_asked = any(o == (self.P[0] if self.P else None) and t in asked for o, t, _ in sit.cells)
        if question and self.WIDE and self.P and self.P[0] is not None and len(self.T) < 4 and not owns_asked:
            owned = [(t, tuple(sorted(d))) for o, t, d in sit.cells if o == self.P[0]]   # 'the greatest number of boxes'

            for t in owned:                                  # a question about someone: all they have is in mind
                if t[0] not in [n for n, _ in self.T] and len(self.T) < 4:
                    self.T = self.T + [t]
        if sit.units:                                        # 'how many grams?' when the story said kg: 1 kg = 1000 g
            here = {it[1] for it in self.items if it[0] in ("L", "T")} | \
                {w for it in self.items if it[0] == "T" for w in it[1].split(" of ")}
            told = {w for _, t, _ in sit.cells for w in t.split(" of ")} | here
            here = {singular(w) for w in here}
            told = {singular(w) for w in told}
            for u in sit.units:
                big, small = {singular(w) for w in u["big"]}, {singular(w) for w in u["small"]}
                if (here & small and told & big) or (here & big and told & small):
                    out["K1"] = Lin(u["k"])
                    self.unit = u["said"]
                    break
        seen = set()
        for label in self.labels():
            key = self.cell(label)
            if key in seen:
                continue
            seen.add(key)
            v = sit.read(*key)
            if v is None:
                if question:
                    # For questions, include asked things as unknown so expressions can reference them
                    out[label] = Lin(0, {label.replace(".", "").replace("@", "D"): 1})
                else:
                    continue
            elif v.known and v.c == 0 and not question:
                continue
            elif learning and not v.known:
                continue
            else:
                out[label] = v
            if question:
                f = sit.read(*key, first=True)
                if f is not None and (f.c != v.c or f.k != v.k) and not (learning and not f.known):
                    out["F:" + label] = f
        return out


# ---- explanations: small expressions over the slots ----------------------------------------------------

_TERM = r"([A-Z][A-Za-z0-9.@:]*)(?:([*/])2)?"
_EXPR = re.compile(rf"^{_TERM}(?:([-+*/~%&^#$!]){_TERM})?$")
# division with a remainder (P3): a%b what is left over, a&b how many full groups, a^b how many groups are needed
_WHOLE = "%&^"
# P5-P6 rules: a!b a percent of b ('@' is taken: it marks days and colours), a#b the greatest common factor, a$b the least common multiple; 'q' (a square:
# side x side) lets a number be multiplied by itself
_RULED = "%&^#$!"
# S1: the unitary method, 'u': (a/b)*c, the value of ONE (a / b), then of c of them; three numbers at once
_UNITARY = re.compile(r"^\(([A-Z][A-Za-z0-9.@:]*)/([A-Z][A-Za-z0-9.@:]*)\)\*([A-Z][A-Za-z0-9.@:]*)$")


def expressions(atoms, ops=""):
    """All small explanations: value -> [expression]. Atoms must be known numbers (learning). ops: the
    whole-group rules it was taught (%, &, ^); it can't explain anything with a rule it doesn't know."""
    base = [(a, v.c) for a, v in atoms.items()]
    terms = list(base) + [(f"{a}*2", v * 2) for a, v in base if not a.startswith(("N", "K"))] + \
        [(f"{a}/2", v / 2) for a, v in base if not a.startswith(("N", "K"))]
    out = defaultdict(list)
    for a, v in terms:
        out[v].append(a)
    root = lambda t: re.split(r"[*/]2$", t)[0]
    if "u" in ops:                                                    # first one (a / b), then c of them
        for a, va in base:
            for b, vb in base:
                if a == b or not vb or va == vb:
                    continue
                one = va / vb
                for c, vc in base:
                    if c in (a, b) or vc == vb or vc == 1:
                        continue
                    out[one * vc].append(f"({a}/{b})*{c}")
    if "q" in ops:                                                    # the square rule: side x side
        for a, va in base:
            if 1 < va <= 1000:
                out[va * va].append(f"{a}*{a}")
    for i, (a, va) in enumerate(terms):
        for j, (b, vb) in enumerate(terms):
            if i == j or root(a) == root(b):
                continue
            plain = a == root(a) and b == root(b)
            if i < j:
                out[va + vb].append(f"{a}+{b}")
                if plain:
                    out[va * vb].append(f"{a}*{b}")
                    out[abs(va - vb)].append(f"{a}~{b}")
            out[va - vb].append(f"{a}-{b}")
            if plain and vb:
                out[va / vb].append(f"{a}/{b}")
            if "!" in ops and plain and 0 < va <= 100 and a[0] in "NQ":       # va percent of vb (a number it is told)
                out[va * vb / 100].append(f"{a}!{b}")
            if plain and i < j and va > 0 and vb > 0 and va.denominator == 1 and vb.denominator == 1 and \
                    ("#" in ops or "$" in ops):
                from math import gcd
                g = gcd(int(va), int(vb))
                if "#" in ops:
                    out[Fraction(g)].append(f"{a}#{b}")
                if "$" in ops:
                    out[Fraction(int(va) * int(vb) // g)].append(f"{a}${b}")
            if ops and plain and vb > 0 and va > 0 and va.denominator == 1 and vb.denominator == 1 and va > vb:
                q, r = divmod(int(va), int(vb))
                if "&" in ops:
                    out[Fraction(q)].append(f"{a}&{b}")
                if "^" in ops:
                    out[Fraction(q + (r > 0))].append(f"{a}^{b}")
                if r and "%" in ops:
                    out[Fraction(r)].append(f"{a}%{b}")
    return out


def show_work(expr, atoms):
    """The working for a whole-groups step, and its check by undoing it ('3\u00d75 + 2 = 17 \u2713')."""
    u = _UNITARY.match(expr)
    if u:
        a, b, c = (atoms.get(x) for x in u.groups())
        if a is None or b is None or c is None or not (a.known and b.known and c.known) or not b.c:
            return None
        v, work = unitary_steps(a.c, b.c, c.c)
        return f"{work}; check {dec(v)} \u00f7 {dec(c.c)} \u00d7 {dec(b.c)} = {dec(v / c.c * b.c)} \u2713"
    m = _EXPR.match(expr)
    if not m or not m[3] or m[1] not in atoms or m[4] not in atoms:
        return None
    a, b = atoms[m[1]], atoms[m[4]]
    if not (a.known and b.known):
        return None
    if m[3] == "*" and m[1] == m[4]:
        return f"a square: side \u00d7 side = {fmt(a.c)} \u00d7 {fmt(a.c)} = {fmt(a.c * a.c)}"
    if m[3] == "!":
        return percent_steps(a.c, b.c)[1]
    if m[3] in "#$" and a.c > 0 and b.c > 0 and a.c.denominator == 1 and b.c.denominator == 1:
        v, work = (gcd_steps if m[3] == "#" else lcm_steps)(a.c, b.c)
        check = (f"check: {int(a.c)} \u00f7 {v} and {int(b.c)} \u00f7 {v} have no remainder \u2713" if m[3] == "#" else
                 f"check: {v} \u00f7 {int(a.c)} = {v // int(a.c)}, {v} \u00f7 {int(b.c)} = {v // int(b.c)} \u2713")
        return f"{work}; {check}"
    if m[3] not in _WHOLE:
        return None
    if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
        return None
    q, r, work = group_steps(a.c, b.c)
    need = f"; {q} + 1 = {q + 1} needed" if m[3] == "^" and r else ""
    ok = "\u2713" if q * int(b.c) + r == a.c else "\u2717"
    return f"{work}{need}; check {q}\u00d7{int(b.c)} + {r} = {q * int(b.c) + r} {ok}"


def evaluate(expr, atoms):
    u = _UNITARY.match(expr)
    if u:                                                  # the unitary method: one, then many
        a, b, c = (atoms.get(x) for x in u.groups())
        if a is None or b is None or c is None or not b.known or b.c == 0:
            return None
        one = a.scale(1 / b.c)
        return one.times(c)
    m = _EXPR.match(expr)
    if not m:
        return None

    def term(name, op):
        if name not in atoms:
            return None
        v = atoms[name]
        return v if not op else (v.scale(2) if op == "*" else v.scale(Fraction(1, 2)))
    a = term(m[1], m[2])
    if a is None or not m[3]:
        return a
    b = term(m[4], m[5])
    if b is None:
        return None
    if m[3] == "~":                                        # the difference: bigger minus smaller
        if not (a.known and b.known):
            return None
        return Lin(abs(a.c - b.c))
    if m[3] == "!":                                        # a percent of b
        if not a.known:
            return None
        return b.scale(a.c / 100)
    if m[3] in "#$":                                       # greatest common factor, least common multiple
        if not (a.known and b.known) or a.c <= 0 or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        from math import gcd
        g = gcd(int(a.c), int(b.c))
        return Lin(g if m[3] == "#" else int(a.c) * int(b.c) // g)
    if m[3] in _WHOLE:                                     # whole groups: only for whole numbers it knows
        if not (a.known and b.known) or b.c <= 0 or a.c.denominator != 1 or b.c.denominator != 1:
            return None
        q, r = divmod(int(a.c), int(b.c))
        return Lin({"%": r, "&": q, "^": q + (r > 0)}[m[3]])
    return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a.times(b), "/": lambda: a.over(b)}[m[3]]()


def write(sit, clause, target, v):
    if target.startswith("F:"):
        sit.write_first(*clause.cell(target[2:]), v)
    else:
        sit.write(*clause.cell(target), v)


def change_cell(sit, key, topic=False):
    """The cell a change clause should really act on when its own frame target holds nothing yet:
    the KNOWN cell of the same noun (its own owner first, then the ownerless one, then a lone
    other), else -- when `topic` -- the story's current topic cell (elliptical clauses: '1 flies
    away' means 1 of what the story is about). -> the cell key, or None."""
    if key is None:
        return None
    known = [k for k, c in sit.cells.items() if k[1] == key[1] and c[1].bind(sit.bound).known]
    for want in (key[0], None):
        same = [k for k in known if k[0] == want]
        if len(same) == 1:
            return same[0]
        if len(same) > 1:
            return None                              # ambiguous: which of them changed?
    if len(known) == 1:
        return known[0]
    if topic and sit.thing and not known:
        by_topic = [k for k, c in sit.cells.items() if k[1] == sit.thing[0]
                    and c[1].bind(sit.bound).known]
        if len(by_topic) == 1:
            return by_topic[0]
    return None


_USES = {}                          # explanation -> the atoms it uses (memoized: see uses())

_TOOL_OPS = "%&^#$!"                # the operators that are tools (unitary and square have their own forms)


def tool_ops(expr):
    """Which tools one explanation used: its operator character, or the two special forms —
    the unitary method '(a/b)*c' and the square 'a*a'. -> tuple of ops (empty if no tool)."""
    if _UNITARY.match(expr):
        return ("u",)
    m = _EXPR.match(expr)
    if not m or not m[3]:
        return ()
    if m[3] == "*" and m[1] == m[4]:
        return ("q",)
    return (m[3],) if m[3] in _TOOL_OPS else ()


def uses(expr):
    """The atoms an explanation uses ('N1+N2' -> ['N1', 'N2']). Memoized: a lesson asks about the same
    few thousand explanations millions of times, and this was the single hottest call in the brain
    (30M calls / 61M regex matches in one P1 lesson). -> tuple (every caller only iterates, indexes
    or counts it)."""
    got = _USES.get(expr)
    if got is None:
        u = _UNITARY.match(expr)
        if u:
            got = tuple(u.groups())
        else:
            m = _EXPR.match(expr)
            got = tuple(x for x in (m[1], m[4]) if x) if m else ()
        if len(_USES) < 100000:      # the pool of explanations is small and closed; a guard all the same
            _USES[expr] = got
    return got


# ---- the frame learner ----------------------------------------------------------------------------------


TRUST = {3: 1.0, 2: 0.97, 1: 0.9, 0: 0.85}     # a word in its frame > the word anywhere > the frame shape > anything


# ---- reading the request: what may answer 'how many X?' -------------------------------------------------

def _term_unit(clause, label):
    """The noun a single term counts ('P1.T1' -> 'pen'); None for numbers and unknowns."""
    if label.startswith("F:"):
        label = label[2:]
    if not label.startswith("P"):
        return None
    cell = clause.cell(label)
    return cell[1] if cell else None


def counts_thing(clause, expr, thing):
    """Could this reading's value be a count of `thing`, the noun the question asks about?
    'How many pens cost 15 dollars?' must not be answered by dollars-per-pen. This looks only at
    what the terms ARE counts of, never at their values; a term that says nothing ('N1', a cell it
    cannot find) may count anything, and so may a whole expression it cannot parse."""
    u = _UNITARY.match(expr)
    if u:
        a, b, c = u.groups()
        unit = _term_unit(clause, c) or _term_unit(clause, a)   # (a/b)*c counts c of them, else of a's kind
        return unit is None or unit == thing
    m = _EXPR.match(expr)
    if not m:
        return True
    t1, op, t2 = m[1], m[3], m[4]
    if not op:
        unit = _term_unit(clause, t1)
        return unit is None or unit == thing
    ua, ub = _term_unit(clause, t1), _term_unit(clause, t2)
    if op == "/":
        return ub is None or ub != thing        # a top counted out of bottoms: counts the top noun
    if op in "&^":                              # full groups / groups needed: a count of the bottom noun
        # '253 people ^ 5 people-per-car' -> 51 cars: the bottom rate lives in a car-owned cell, so
        # the result counts the container's noun, not the content's noun. Checking the bottom term's
        # noun alone (e.g. 'person' in P2.T2) would wrongly reject this needed-total reading.
        ub_owner = _term_owner(clause, t2)
        return ub_owner is None or ub_owner == thing
    if op == "%":
        return ua is None or ua == thing        # what is left over of the top noun
    if op == "!":
        return ub is None or ub == thing        # a percent of the bottom noun
    if ua and ub and ua != ub:                  # a sum or product of two kinds counts neither alone
        return thing not in {ua, ub}
    unit = ua or ub
    return unit is None or unit == thing


def _term_owner(clause, label):
    """The owner a single term lives in ('P2.T2' -> 'car'); None for numbers and unknowns."""
    if label.startswith("F:"):
        label = label[2:]
    if not label.startswith("P"):
        return None
    cell = clause.cell(label)
    return cell[0] if cell else None


def _group_owner(clause, t1, t2):
    """The container a total-divided-by-rate counts ('253 people ^ 5 per car' -> 'car').

    Total (ownerless people) grouped by a per-container rate (car-owned people) counts
    the containers, not the content. -> the owner noun, or None when this is not that
    shape (different contents, neither side owned, ...)."""
    c1 = clause.cell(t1[2:] if t1.startswith("F:") else t1) if t1.startswith(("P", "F:")) else None
    c2 = clause.cell(t2[2:] if t2.startswith("F:") else t2) if t2.startswith(("P", "F:")) else None
    if not c1 or not c2:
        return None
    (o1, n1), (o2, n2) = (c1[0], c1[1]), (c2[0], c2[1])
    if n1 != n2:
        return None
    if o1 is None and o2 is not None:
        return o2
    if o2 is None and o1 is not None:
        return o1
    return None


def scope_owner(clause, thing):
    """The noun the question locates its answer in: 'how many people are in ONE CAR' wants the people
    of one car, not all the people there are. -> the owner noun, or '' when the question does not
    narrow things down that way (the gate must only fire when the words themselves fired it)."""
    items = clause.items
    for i, it in enumerate(items):
        if it[0] != "L" or it[1] not in _WHERE:
            continue                                   # 'in', 'on', 'at', ... -- the question locates it
        for nxt in items[i + 1:i + 4]:                 # 'in one car', 'in the box', 'on each table'
            if nxt[0] == "T":
                owner = singular(nxt[1])
                return "" if not owner or owner == thing or owner in _NOT_NOUNS else owner
            if nxt[0] in ("V", "P", "T"):              # 'cost Tom', 'held are ...': not a location
                break
    return ""


def by_owner(clause, expr, owner):
    """True when every cell this reading touches belongs to `owner` -- and it touches at least one,
    so a pure-number reading ('N1*2') is not mistaken for a scoped one. Terms that are not cells
    (the question's own numbers) say nothing about the owner and are ignored."""
    def cell_of(label):
        label = label.replace("F:", "")
        if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
            return None
        return clause.cell(label)
    cells = [c for c in (cell_of(l) for l in uses(expr)) if c]
    return bool(cells) and all(c[0] == owner for c in cells)


def _self_owned(clause, target):
    """True when the reading writes to a cell where the owner IS the noun ('jar's jar'): a slot
    error, never a meaning -- no jar holds jars. Targets that are not cells pass through."""
    label = target.replace("F:", "")
    if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
        return False
    cell = clause.cell(label)
    return bool(cell) and cell[0] is not None and cell[0] == cell[1]


def _scales_content_total(clause, target, expr):
    """True when the reading infers an ownerless container count by scaling the sentence's own
    number with the CONTENT total ('each car holds 5 people' with 253 people in mind -> 1265 cars).
    The sentence says how many content go in one container; multiplying by all the content gives
    content-squared per container, never a container count (the legitimate direction -- per-container
    times the container count giving all the content, '12 per jar times 72 jars' -- passes through:
    there the multiplier counts the owner, not the content). Targets that are not ownerless cells,
    non-products, and products whose cell multiplier is not this clause's owned content pass through."""
    m = _EXPR.match(expr)
    if not m or m[3] != "*":
        return False
    label = target.replace("F:", "")
    if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
        return False
    cell = clause.cell(label)
    if not cell or cell[0] is not None:
        return False
    owner = cell[1]
    others = [a for a in uses(expr) if not re.fullmatch(r"N\d+", a)]
    if len(others) != 1 or not re.fullmatch(r"(?:F:)?P\d\.T\d(?:@D\d)?", others[0]):
        return False
    acell = clause.cell(others[0].replace("F:", ""))
    if not acell:
        return False
    contents = {c[1] for lb in clause.labels() for c in (clause.cell(lb),)
                if c and c[0] == owner and c[1] != owner}
    return acell[1] in contents


class Frames:
    def __init__(self, data=None, coordination=None):
        d = data or {}
        self.coord = coordination if coordination is not None else Coordination()
        if d.get("rules") and not self.coord.rules:      # old layout / bare engine file: the tools it was taught
            self.coord.rules.update(d["rules"])
        self.table = {"S": d.get("S", {}), "Q": d.get("Q", {})}     # kind -> key -> {"n": .., "m": {pair: count}}
        self.pron = d.get("pron", {})                               # word -> {"n": .., "boy": .., "girl": ..}
        self.heard = d.get("heard", {})                             # words heard in stories
        self.nouns = d.get("nouns", {})                             # words it met as things (after a number)
        # the same tallies kept per KIND OF SITUATION (kindergarten, P1, P2, real P1, ...), as for words: each
        # situation where a meaning could apply has a say in how sure it is, however many lessons it had
        self.by_situation = d.get("by_situation", {})               # situation -> kind -> key -> {n, m, o}
        self.situation = "chat"                                     # where it is now (set by the lessons)
        self.units = d.get("units", [])                             # unit facts the teacher taught (P5)
        # sureness results are cached per (kind, key, meaning); credit() is the only place the tables
        # change, so it bumps the revision and empties the cache (see sureness)
        self._rev, self._sure_cache = 0, {}

    @property
    def rules(self):
        return self.coord.rules                       # the taught tools live in the coordination region

    @property
    def ops(self):
        return "".join(self.rules)

    def bind(self, coordination):
        """Hand the region's coordination to this engine (Mind._bind): the tools, their cue words and
        their rewards belong to the coordination region, not to the frames."""
        if coordination is None or coordination is self.coord:
            return
        coordination.take_over(self.coord)
        self.coord = coordination

    def ops_for(self, clause):
        """The rules it may use in this clause: which tools the coordination region allows here."""
        words = {it[1] for it in clause.items if it[0] in ("L", "T")} if clause is not None else set()
        return self.coord.allowed(words)

    BALANCED = True                                                  # judge meanings per situation (else pooled)
    BLOCKING = False                                                 # a word that already explains it blocks the rest
    APPEARED = True                                                  # a thing that just appeared: changes were wrong
    WORDLESS = True                                                  # a sentence with no number needs a word to act
    LAST = -1                                                        # which changed thing stays in mind (-1: last)
    TRACK = True                                                     # a sentence it can't act out still says what it's about
    SAY = 50                                                         # chances a situation needs for a full say

    def state(self, prune=True):
        table = {}
        for kind, keys in self.table.items():
            table[kind] = {}
            for k, e in keys.items():
                n = e["n"]
                m = {p: c for p, c in e["m"].items() if not prune or n < 10 or _sure(e, p) >= 0.3}
                if m or n >= 3:
                    table[kind][k] = {"n": n, "m": m, "o": {p: o for p, o in e.get("o", {}).items() if p in m}}
        by = {}
        for name, kinds in self.by_situation.items():
            by[name] = {}
            for kind, keys in kinds.items():
                by[name][kind] = {}
                for k, e in keys.items():
                    kept = table[kind].get(k)
                    if kept is None:
                        continue
                    by[name][kind][k] = {"n": e["n"], "m": {p: c for p, c in e["m"].items() if p in kept["m"]},
                                         "o": {p: o for p, o in e["o"].items() if p in kept["m"]}}
        return {**table, "pron": self.pron, "heard": self.heard, "nouns": self.nouns, "by_situation": by,
                "rules": self.rules, "units": self.units}

    # -- pronouns --
    def pronoun(self, w):
        p = self.pron.get(w)
        if not p or p["n"] < 3 or len(p.get("frames", ["", "", ""])) < 3:   # a pronoun goes anywhere a name goes
            return None
        for g in ("boy", "girl", "thing"):
            if p.get(g, 0) / p["n"] >= (0.9 if g != "thing" else 0.85) and \
                    all(p.get(o, 0) / p["n"] <= 0.5 for o in ("boy", "girl", "thing") if o != g):
                return g
        return None

    def observe_pronouns(self, clause, involved_genders):
        for it in clause.items:
            if (it[0] == "L" and it[1].isalpha()) or (it[0] == "P" and it[3]):
                p = self.pron.setdefault(it[1], {"n": 0})
                p["n"] += 1
                for g in involved_genders:
                    p[g] = p.get(g, 0) + 1
                frames = p.setdefault("frames", [])
                if clause.sig not in frames and len(frames) < 5:
                    frames.append(clause.sig)

    # -- learning --
    def credit(self, kind, clause, pairs, atoms, weight=1, appeared=()):
        """Each word in its frame (and the frame shape) is credited with the explanations that came true.
        It also counts, for every explanation it knows for that key, whether it was POSSIBLE this time
        (its numbers and cells were there): a meaning is judged only where it could have applied."""
        labels = set(clause.labels()) | {"ANS"} | {f"F:{x}" for x in clause.labels() if x in atoms}
        here = self.by_situation.setdefault(self.situation, {}).setdefault(kind, {})
        keys = clause.keys()
        for p in pairs:                                   # every confirmed explanation that used a tool:
            for op in tool_ops(p.split("=", 1)[-1]):      # the coordination region earns a reward for it
                self.coord.reward(op, True)
        if self.BLOCKING:
            keys = self._unblocked(kind, keys, pairs)
        for _, k in keys:
            e = self.table[kind].setdefault(k, {"n": 0, "m": {}, "o": {}})
            h = here.setdefault(k, {"n": 0, "m": {}, "o": {}})
            e.setdefault("o", {})
            e["n"] += weight
            h["n"] += weight
            for p in pairs:
                e["m"][p] = e["m"].get(p, 0) + weight
                h["m"][p] = h["m"].get(p, 0) + weight
            for p in e["m"]:
                target, expr = p.split("=", 1)
                if target in labels and all(a in atoms or (a == target and a in appeared) for a in uses(expr)):
                    e["o"][p] = e["o"].get(p, 0) + weight
                    h["o"][p] = h["o"].get(p, 0) + weight
        # the tables just changed: every sureness computed before this sentence is now wrong, so the
        # cache goes and the revision moves on (sureness reads nothing else that can change)
        self._rev += 1
        self._sure_cache.clear()

    def _unblocked(self, kind, keys, pairs):
        """Blocking (as in Rescorla-Wagner): if a word in its frame already explains what happened, the other
        words of the sentence learn nothing from it ('2 toys were removed': 'removed' explains it, so 'were' is not
        taught that it takes things away). The frame shape still learns, so a sentence of new words is never lost."""
        explain = []
        for rank, k in keys:
            e = self.table[kind].get(k)
            if rank == 3 and e and e["n"] >= 5 and any(p in e["m"] and self.sureness(kind, k, e, p)[0] >= 0.8
                                                       for p in pairs):
                explain.append(k)
        if not explain:
            return keys
        words = {k.split("|")[0] for k in explain}
        return [(rank, k) for rank, k in keys if k in explain or rank <= 1 or (rank == 2 and k.split("|")[0] in words)]

    def sureness(self, kind, k, e, p):
        """How sure a meaning is -> (sure, count, chances). Cached: candidates() asks about the same
        (kind, key, meaning) over and over while it reads a story (it was 2M calls in one lesson, each
        walking every situation), and credit() invalidates the whole cache whenever the tables change."""
        hit = self._sure_cache.get((kind, k, p))
        if hit is not None and hit[0] == self._rev:
            return hit[1]
        out = self._sureness(kind, k, e, p)
        self._sure_cache[(kind, k, p)] = (self._rev, out)
        return out

    def _sureness(self, kind, k, e, p):
        """How sure a meaning is: count / (chances + 1). Balanced: worked out in every situation where it could
        have applied, and averaged, each situation weighted by its evidence up to a full say (SAY chances), so a
        stage with thousands of lessons can't outvote one with hundreds. -> (sure, count, chances)"""
        cnt = e["m"][p]
        chances = max(e.get("o", {}).get(p, e["n"]), cnt)
        if not self.BALANCED or not self.by_situation:
            return cnt / (chances + 1), cnt, chances
        num = den = 0.0
        rest_m, rest_o = cnt, e.get("o", {}).get(p, 0)
        parts = []
        for kinds in self.by_situation.values():
            h = kinds.get(kind, {}).get(k)
            if h:
                m, o = h["m"].get(p, 0), h["o"].get(p, 0)
                rest_m, rest_o = rest_m - m, rest_o - o
                parts.append((m, o))
        parts.append((max(rest_m, 0), max(rest_o, 0)))   # 'earlier': what it learned before it kept situations apart
        for m, o in parts:
            o = max(o, m)
            if not o:
                continue
            w = o / (o + self.SAY)
            num += w * m / (o + 1)
            den += w
        if not den:
            return cnt / (chances + 1), cnt, chances
        return num / den, cnt, chances

    def _word_keys(self):
        cached = getattr(self, "_word_keys_cache", None)
        size = sum(len(t) for t in self.table.values())
        if cached is None or cached[0] != size:
            cached = (size, {k.split("|", 1)[0] for t in self.table.values() for k in t if "|" in k})
            self._word_keys_cache = cached
        return cached

    def _word_footprint(self, w):
        """How strongly the learned frames ever used the word at all (sum of its row sizes). A verb that has
        been taught in hundreds of stories is huge; a word that drifted in on a few lessons is not a verb."""
        cached = getattr(self, "_foot_cache", None)
        size = sum(len(t) for t in self.table.values())
        if cached is None or cached[0] != size:
            fp = {}
            for t in self.table.values():
                for k, e in t.items():
                    if "|" not in k:
                        continue
                    fp[k.split("|", 1)[0]] = fp.get(k.split("|", 1)[0], 0) + e["n"]
            cached = (size, fp)
            self._foot_cache = cached
        return cached[1].get(w, 0)

    def is_noun(self, w):
        if self.nouns.get(w, 0) >= 2 or self.nouns.get(singular(w), 0) >= 2:
            return True
        # A word the story has only ever HEARD (never perceived, no learned frame has ever used it) may still be
        # the new noun it never got to meet. A word with a grammar job ('six left', 'had 11') stays literal, and
        # so does any word some learned frame has ever used, so verbs are not read as things in noun positions.
        if w in _FUNCTION or self.pronoun(w) or self.heard.get(w, 0) == 0:
            return False
        keys = self._word_keys()[1]
        if w not in keys:
            return True
        # Counterfactual: a word the frames have only used a LITTLE (and that is no known verb) still gets the
        # new-noun chance, so 'cherries', 'shirts', 'customers' become things instead of invisible literals.
        # The rule stays OFF unless the runner switches _CHANGE_FIX on.
        if (_CHANGE_FIX or _CHANGE_FIX_NOUN) and w not in _VERB_WORDS and self._word_footprint(w) <= _NOUN_SHAPE_MAX:
            return True
        return False

    def word_property(self, w):
        """Learned property of a word from its frames. 
        Returns a set of properties: 'det', 'glue', 'break', 'between', 'small', 'where', 'not_noun', 'verb', 'prep'"""
        from .storyreader import singular
        w_singular = singular(w)
        props = set()

        # Known as a noun (after number, taught as thing) - check singular form
        if self.is_noun(w_singular):
            props.add("noun")
            return props  # nouns don't get other properties

        # Check frames where this word appears (rank 3: word in its frame, signature has _ marker)
        # Use original word form for frame lookup (frames are stored under original forms)
        frame_keys = [k for k in self.table.get("S", {}) if k.startswith(w + "|") and "_" in k.split("|", 1)[1]]
        frame_keys_q = [k for k in self.table.get("Q", {}) if k.startswith(w + "|") and "_" in k.split("|", 1)[1]]
        all_frames = frame_keys + frame_keys_q

        if not all_frames:
            return props

        # Analyze frame shapes to infer word category
        # Rank 3 key format: "word|sig_with_underscore" where _ marks word position in sig
        # sig uses P,N,T,D for person, number, thing, day
        # Examples: "the|_PNT" (at start before P_N_T), "has|P_NT" (after P, before N_T)

        pos_patterns = []
        for fk in all_frames:
            if "|" not in fk:
                continue
            sig = fk.split("|", 1)[1]  # signature with _ marking position
            if "_" not in sig:
                continue
            # Split signature at _: before = sig[:pos], after = sig[pos+1:]
            pos = sig.index("_")
            before = sig[:pos]
            after = sig[pos+1:]
            pos_patterns.append((before, after))

        # Classify based on dominant frame position
        # Count frames by position type
        start_NT = 0      # _N, _T, _NT... (frame start before N/T) -> determiner
        start_P = 0       # _P, _PN... (frame start before P) -> break/prep
        start_other = 0   # _D, _other -> prep
        after_P = 0       # P_... (after person) -> verb
        after_content = 0 # PNT_, NT_, T_... (after content) -> preposition
        between_content = 0 # between N/T/P elements
        total_weight = 0

        for fk in all_frames:
            if "|" not in fk:
                continue
            sig = fk.split("|", 1)[1]
            if "_" not in sig:
                continue
            pos = sig.index("_")
            before = sig[:pos]
            after = sig[pos+1:]
            weight = self.table["S"].get(fk, {}).get("n", 1)
            total_weight += weight

            if not before:
                # Frame start
                if after and after[0] in ("N", "T"):
                    start_NT += weight
                elif after and after[0] == "P":
                    start_P += weight
                elif after and after[0] in ("D",):
                    start_other += weight
                else:
                    start_other += weight
            elif before and before[-1] == "P":
                # After person
                after_P += weight
            elif before and before[-1] in ("N", "T", "D"):
                # After content word (thing, number, day)
                after_content += weight
                # Check for between pattern
                if after and after[0] in ("N", "T", "P") and before[-1] != after[0]:
                    between_content += weight
            else:
                after_content += weight

        # Primary classification based on dominant pattern - winner takes all for primary
        primary = None

        # Noun check (using singular form for noun lookup)
        if self.is_noun(w_singular):
            primary = "noun"

        # Special cases for known function words
        if w in ("is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got", "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken", "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown", "gave", "given", "took", "taken", "picked", "received", "collected", "got", "gets", "got"):
            primary = "verb"
        elif w in ("his", "her", "their", "my", "your", "our", "its", "every", "each", "all", "both", "some", "any", "another"):
            primary = "det"  # determiners including quantifiers
        elif w in ("then", "now"):
            primary = "break"
        elif w in ("more", "less", "fewer"):
            primary = "between"
        elif w in ("with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "per"):
            primary = "prep"

        # Determine primary category from dominant frame position (if not special-cased)
        if not primary and total_weight > 0:
            ratios = {
                "det": start_NT / total_weight,
                "verb": after_P / total_weight,
                "prep": (start_P + start_other) / total_weight,  # exclude after_content for prep
                "break": start_P / total_weight,
                "between": between_content / total_weight,
            }

            # Prepositions that appear between content: don't classify as "between"
            # The "between" category is for comparatives (more/less), not prepositions
            prep_words = {"with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "about", "into", "onto", "upon", "over", "under", "above", "below", "between", "among"}
            if w in prep_words:
                ratios["between"] = 0  # force zero

            # Find dominant category above threshold
            candidates = [(cat, ratio) for cat, ratio in ratios.items() if ratio >= 0.35]
            if candidates:
                primary = max(candidates, key=lambda x: x[1])[0]

        # Fallback: glue for high-frequency connectors
        if not primary and self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
            clause_connect = 0
            for fk in all_frames:
                if "|" not in fk:
                    continue
                sig = fk.split("|", 1)[1]
                if "_" not in sig:
                    continue
                pos = sig.index("_")
                before = sig[:pos]
                after = sig[pos+1:]
                if before and after and before[-1] in ("N", "T", "P", "D") and after[0] in ("N", "T", "P", "D"):
                    clause_connect += self.table["S"].get(fk, {}).get("n", 1)
            if clause_connect / total_weight >= 0.3:
                primary = "glue"

        # Small: high frequency, many frames, no primary category
        if not primary and self.heard.get(w, 0) > 2000 and len(all_frames) >= 15:
            primary = "small"

        props = set()
        if primary:
            props.add(primary)
            if primary == "prep":
                props.add("where")

        # Secondary categories (compatible only)
        if primary == "det":
            # Determiners can also be "break" if they start clauses (each, every)
            if total_weight > 0 and start_P / total_weight >= 0.3:
                props.add("break")
        elif primary == "verb":
            # Verbs can be "glue" if high-frequency connectors
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                props.add("glue")
        elif primary == "prep":
            # Prepositions can be "between" if between content (but not for known preps)
            prep_words = {"with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "about", "into", "onto", "upon", "over", "under", "above", "below", "between", "among"}
            if total_weight > 0 and between_content / total_weight >= 0.2 and w not in prep_words:
                props.add("between")
            # Can be "glue" if clause connector
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                clause_connect = 0
                for fk in all_frames:
                    if "|" not in fk:
                        continue
                    sig = fk.split("|", 1)[1]
                    if "_" not in sig:
                        continue
                    pos = sig.index("_")
                    before = sig[:pos]
                    after = sig[pos+1:]
                    if before and after and before[-1] in ("N", "T", "P", "D") and after[0] in ("N", "T", "P", "D"):
                        clause_connect += self.table["S"].get(fk, {}).get("n", 1)
                if clause_connect / total_weight >= 0.3:
                    props.add("glue")
        elif primary == "break":
            # Break words can be "glue" if also connector
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                props.add("glue")
        elif primary == "between":
            # Between words can be "prep/where" if also prepositional
            if total_weight > 0 and (start_P + start_other) / total_weight >= 0.3:
                props.add("prep")
                props.add("where")

        # Not noun: appears in noun-like positions but not noun/verb/det/prep
        if not self.is_noun(w_singular) and self.heard.get(w, 0) > 100:
            noun_like = start_NT + after_P
            if total_weight > 0 and noun_like / total_weight >= 0.3:
                if primary not in ("noun", "verb", "det", "prep"):
                    props.add("not_noun")

        return props

    def met_things(self, clause):
        """The words it saw as things are thing words from now on, even once they are familiar."""
        # Function words that should never be marked as nouns even if they appear in T positions
        NOT_NOUNS_MET = {"and", "or", "but", "so", "then", "of", "to", "for", "with", "in", "on", "at", "by", "from", "the", "a", "an", "his", "her", "their", "my", "your", "our", "its", "this", "that", "these", "those", "each", "every", "some", "any", "all", "both", "more", "less", "few", "many", "much", "fewer", "same", "other", "another", "such", "what", "which", "who", "whom", "whose", "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "do", "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must"}
        for it in clause.items:
            if it[0] == "T":
                for w in it[1].split(" of "):
                    if w not in NOT_NOUNS_MET:
                        self.nouns[w] = self.nouns.get(w, 0) + 1

    def hear(self, toks):
        """The ear hears every word of a sentence (before perception has worked out what they are)."""
        for w in toks:
            if w.isalpha():
                self.heard[w] = self.heard.get(w, 0) + 1

    def observe_statement(self, clause, before, after):
        """What did this clause do? Every small explanation the scene makes true."""
        atoms = clause.atoms(before, learning=True)
        exprs = expressions(atoms, self.ops_for(clause))
        pairs, appeared = [], set()
        for label in clause.labels():
            key = clause.cell(label)
            v = after.read(*key)
            if v is None:
                continue
            if self.APPEARED and label not in atoms and before.read(*key) is None:
                f = after.read(*key, first=True)
                if f is not None and f.known and v.known and f.c == v.c:
                    appeared.add(label)                 # it just appeared with this many: nothing was taken or added
            same = label in atoms and atoms[label].c == v.c
            # nothing changed: 'now she has 21' when she has 21. It can't have DONE something to it, so explanations
            # that use it ('twice 21 minus 21') are coincidences, not meanings
            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            if same:                                          # it says nothing new about now: maybe about the start
                f = after.read(*key, first=True)
                pairs += [f"F:{label}={e}" for e in exprs.get(f.c, []) if e != label and label not in uses(e)]
        if pairs:
            self.credit("S", clause, sorted(set(pairs)), atoms, appeared=appeared)
        return pairs

    def observe_question(self, clause, sit, answer, weight=1):
        atoms = clause.atoms(sit, question=True, learning=True)
        exprs = expressions(atoms, self.ops_for(clause))
        pairs = [f"ANS={e}" for e in exprs.get(Fraction(answer), [])]
        if pairs:
            self.credit("Q", clause, sorted(set(pairs)), atoms, weight)
        return pairs

    # -- understanding --
    def candidates(self, kind, clause, atoms):
        """Every meaning its words and frame suggest that can apply here, surest first. Sure = how often it
        came true when it was possible, a little less sure with little evidence (count / (chances + 1)).
        A word in its own frame wins a tie over the word anywhere, which wins over the bare frame shape."""
        labels = set(clause.labels()) | {f"F:{x}" for x in clause.labels() if x in atoms} if kind == "S" else {"ANS"}
        out = []
        allowed = self.ops_for(clause)             # the same rules for every key of this clause
        for rank, k in clause.keys():
            e = self.table[kind].get(k)
            if not e or e["n"] < (2 if rank else 1):
                continue
            for p in e["m"]:
                target, expr = p.split("=", 1)
                if target not in labels or any(a not in atoms for a in uses(expr)):
                    continue
                if expr.startswith("(") and "u" not in allowed:
                    continue
                if any(o in expr for o in "#$!") and not any(o in allowed for o in "#$!" if o in expr) or \
                        (len(uses(expr)) == 2 and uses(expr)[0] == uses(expr)[1] and "q" not in allowed):
                    continue
                c, cnt, chances = self.sureness(kind, k, e, p)
                if (rank >= 2 and (c < 0.7 or cnt < 2)) or (rank == 1 and c < 0.5):
                    continue
                c *= TRUST[rank] * (0.99 if "~" in expr or any(o in expr for o in _RULED) else 1) * \
                    (0.995 if "2" in expr.replace("N2", "") else 1)
                # on a tie the plainer explanation wins: minus over difference, no doubling over doubling
                out.append({"rank": rank, "c": c, "n": chances, "key": k, "target": target, "expr": expr})
        plain = lambda x: len(uses(x["expr"])) + x["expr"].startswith("(") + ("2" in x["expr"].replace("N2", "")) + ("~" in x["expr"]) + \
            any(o in x["expr"] for o in _RULED) + (len(set(uses(x["expr"]))) < len(uses(x["expr"])))
        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        return out

    def apply(self, clause, sit, asked=None):
        """Act a statement out. -> what it did, or None if it has no idea.
        `asked` (the request read from the question) is accepted but deliberately NOT used to pick
        the statement's meaning: what a sentence says cannot depend on what is asked afterwards --
        'Mia collected another 4 oranges' is an addition whatever the question wants, and reading it
        as a plain 4 because the question asks what is left destroyed the kindergarten exam and P1
        (measured 2026-10-07: exam 234/400, P1 78%). The request gate belongs on the ANSWER's
        readings (Frames.answer), one layer down, where it is checked against the question clause."""
        atoms = clause.atoms(sit)
        cands = self.candidates("S", clause, atoms)
        # a change to something it hasn't heard of yet ('Paco ate 19 cookies'): he must have had some
        # out of order: it may need an amount it hasn't heard yet ('6 more than Marin', 'Paco ate 19'):
        # it keeps an unknown for it, which a later sentence can find
        counted = {it[1] for it in clause.items if it[0] == "T" and len(it) > 3} | ({sit.thing[0]} if sit.thing else set())
        missing = {lb: Lin(0, {"?": 1}) for lb in clause.labels() if lb not in atoms and "@" not in lb
                   and clause.cell(lb) and clause.cell(lb)[1] in counted and sit.read(*clause.cell(lb)) is None}
        if missing:
            wider = [x for x in self.candidates("S", clause, {**atoms, **missing})
                     if sum(a in missing for a in uses(x["expr"])) == 1 and re.fullmatch(
                         r"(?:N\d[+-][A-Z][\w.@:]*|[A-Z][\w.@:]*[+-]N\d)", x["expr"]) and "@" not in x["expr"]]
            if wider and wider[0]["rank"] >= 2 and (not cands or cands[0]["rank"] <= 1 or
                                                      wider[0]["c"] > cands[0]["c"] + 0.05):
                for a in uses(wider[0]["expr"]):
                    if a in missing:
                        start = sit.unknown()
                        sit.cells[clause.cell(a)] = [start, start]
                atoms = clause.atoms(sit)
                cands = self.candidates("S", clause, atoms)
        if not clause.nums and self.WORDLESS:  # no number in it: only a word that means it can change amounts
            cands = [x for x in cands if x["rank"] >= 2]   # ('she ate half'), not the general sentence shapes
        # A cell where a thing owns its own noun is a slot error, not a meaning: 'each jar has 12
        # sandwiches' read as `jar's jar = 12` (the frame's first thing sat in the content slot) made
        # 'how many jars are there' add 72+12. A jar cannot hold jars -- the reading is dropped and
        # the next one is tried; if nothing else fits, the statement is simply not understood.
        # Scaling the sentence's number by the CONTENT total is the same kind of error: 'each car
        # holds 5 people' with 253 people in mind infers 1265 cars (measured 2026-10-07). The sentence
        # says how many content go in ONE container; the legitimate direction (per-container times the
        # container count, '12 per jar times 72 jars' -> all the content) passes through.
        cands = [x for x in cands if not _self_owned(clause, x["target"])
                 and not _scales_content_total(clause, x["target"], x["expr"])]
        if not cands:                          # it has no idea what happened, but it notes what the sentence is about
            if self.TRACK and clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                sit.subject = clause.persons[0]
            if self.TRACK and clause.things:   # 'Zoe thinks of a number': 'it' is the number from now on
                sit.thing = (clause.things[-1][0], ())
            return None
        if _RATE_FIX and len(clause.nums) == 1:       # a rate: 'ate 5 apples every hour'
            m = _RATE_PHRASE.search(" ".join(re.findall(r"[a-z]+", clause.text().lower())))
            n = atoms.get("N1")
            best = evaluate(cands[0]["expr"], atoms)
            if m and n is not None and n.known and (best is None or not best.known or best.c < 0):
                cell = clause.cell(cands[0]["target"].replace("F:", ""))
                if cell and cell[0] == m.group(1):             # the frame put it where the unit owns it
                    if cell in sit.cells:
                        sit.cells[cell][1] = Lin(n.c)          # the per-unit amount is positive and known
                    else:
                        sit.cells[cell] = [Lin(0), Lin(n.c)]   # nothing before the day, like the teacher's first=0
                    done = [{"rank": 1, "c": 0.8, "n": 0, "key": "rate",
                             "target": cands[0]["target"], "expr": "N1", "value": Lin(n.c)}]
                    if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                        sit.subject = clause.persons[0]
                    elif clause.thing_subject and not clause.persons:
                        sit.subject = clause.thing_subject
                    sit.thing = (cell[1], ())
                    return done
        if _CHANGE_EVENT and clause.nums:          # an event cell takes more of the same, not a departure
            evverb2 = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                            or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
            if evverb2 and (evverb2 in _OUT_VERBS or (_FLY_FIX and evverb2 in _FLY_AWAY)) and cands[0]:
                evcell2 = cands[0]["target"].replace("F:", "")
                evkey2 = clause.cell(evcell2) if not evcell2.startswith("F:") else None
                if evkey2 in sit.events:
                    evacc = f"{evcell2}+N1"
                    evhave = next((i for i, x in enumerate(cands)
                                   if x["expr"] == evacc and x["target"] == cands[0]["target"]), None)
                    if evhave is None:
                        cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "*",
                                         "target": cands[0]["target"], "expr": evacc})
                    else:
                        cands.insert(0, cands.pop(evhave))
        if (_CHANGE_FIX or _CHANGE_FIX_VERB) and clause.nums:     # a change-family verb on a quantity it already knows
            verb = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                         or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
            if verb and cands[0] and re.fullmatch(r"N\d+", cands[0]["expr"]):
                sign = "-" if verb in _OUT_VERBS or (_FLY_FIX and verb in _FLY_AWAY) else "+"
                cell = cands[0]["target"].replace("F:", "")
                expr = f"{cell}{sign}N1"
                key = clause.cell(cell) if not cell.startswith("F:") else None
                cur = sit.read(*key) if key else None
                if cur is not None and cur.known:
                    if _CHANGE_EVENT and sign == "-" and key in sit.events:
                        # an event cell TALLIES what went out of it: more going out ADDS to the tally
                        # ('gave away 11' then 'gave away 3 more' -> 14 given, not a balance of 8).
                        expr = f"{cell}+N1"
                    have = next((i for i, x in enumerate(cands)
                                 if x["expr"] == expr and x["target"] == cands[0]["target"]), None)
                    if have is None:
                        cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "*", "target": cands[0]["target"],
                                         "expr": expr})
                    elif _CHANGE_PROMOTE and have > 0:
                        # LANDED 2026-10-09 (measured): the frame table already teaches the departure
                        # ('she READ 11 of the pages' -> P1.T1-N1) but the plain overwrite outranks
                        # it ('read|P_NT' 0.89 vs 'read|*' 0.75), so the meaning the change verb
                        # REQUIRES loses on sureness alone. Move it ahead of the overwrite.
                        cands.insert(0, cands.pop(have))
                elif (cur is None or not cur.known) and _CHANGE_FIX_OWNERLESS:
                    # CF: the clause's own target is an owner the story never gave that noun
                    # ('two marbles are taken out OF THE BASKET' -> basket's marble, empty) while the
                    # story's marbles live in the ownerless cell -- depart from/arrive at the LONE
                    # ownerless known cell of the same noun; never another owner's (the rejected
                    # cellsfix hit other owners' quantities).
                    lone = [k for k, c in sit.cells.items()
                            if k[0] is None and k[1] == key[1] and k[2] == key[2]
                            and c[1].bind(sit.bound).known]
                    n = atoms.get("N1")
                    if len(lone) == 1 and n is not None and n.known:
                        k1 = lone[0]
                        f = sit.cells[k1][1].bind(sit.bound)
                        new = Lin(f.c - n.c) if sign == "-" else Lin(f.c + n.c)
                        if f.known and new.c >= 0:
                            sit.write(*k1, new)
                            done = [{"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": cands[0]["target"], "expr": expr, "value": new}]
                            if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                                sit.subject = clause.persons[0]
                            elif clause.thing_subject and not clause.persons:
                                sit.subject = clause.thing_subject
                elif (cur is None or not cur.known) and (_CHANGE_FIX or _CHANGE_FIX_CELLS or _CHANGE_FIX_TOPIC):
                    # CF (rejected 2026-10-08, flags stay off): the frame's own target holds nothing yet
                    # ('2 marbles are taken out OF THE BASKET' targets the basket's cell, but the story's
                    # marbles live in the ownerless one) -- depart from the KNOWN cell of the same noun
                    # instead. Fixes ASDiv marbles but hits other owners' quantities: worlds -2..3pt.
                    found = change_cell(sit, key, topic=bool(_CHANGE_FIX or _CHANGE_FIX_TOPIC))
                    n = atoms.get("N1")
                    if found and n is not None and n.known:
                        f = sit.cells[found][1].bind(sit.bound)
                        new = Lin(f.c - n.c) if sign == "-" else Lin(f.c + n.c)
                        if f.known and new.c >= 0:
                            sit.write(*found, new)
                            done = [{"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": cands[0]["target"], "expr": expr, "value": new}]
                            if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                                sit.subject = clause.persons[0]
                            elif clause.thing_subject and not clause.persons:
                                sit.subject = clause.thing_subject
                            sit.thing = (clause.cell(done[self.LAST]["target"].replace("F:", ""))[1], ())
                            return done
        best = cands[0]
        group = [x for x in cands if x["key"] == best["key"]] if best["rank"] >= 2 else [best]
        chosen, cells = [], []
        for x in group:
            cell = x["target"].replace("F:", "")                     # one meaning per cell: now OR its start
            base = cell.split("@")[0]
            clash = any(c == cell or (c.split("@")[0] == base and ("@" in c) != ("@" in cell)) for c in cells)
            if clash or (best["rank"] >= 2 and x["c"] < 0.7):       # a total and one of its parts: not both
                continue
            cells.append(cell)
            chosen.append(x)
        # the sentence's own number, kept where its own frame puts it: when the surest reading INFERS
        # a total by scaling ('each car holds 5 people' -> there are 1265 cars), the frame shape's
        # literal reading ('car's people = 5') still says what the sentence actually said, so the story
        # keeps that too. First in: the word's own write stays the last thing changed (LAST = -1).
        if best["rank"] >= 2 and not re.fullmatch(r"N\d+", best["expr"]):
            for x in cands:
                if x["rank"] != 1 or not re.fullmatch(r"N\d+", x["expr"]):
                    continue
                cell = x["target"].replace("F:", "")                  # one meaning per cell, as above
                base = cell.split("@")[0]
                clash = any(c == cell or (c.split("@")[0] == base and ("@" in c) != ("@" in cell))
                            for c in cells)
                if clash:
                    continue
                chosen.insert(0, x)
                break
        done = []
        evverb = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                       or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
        evout = evverb is not None and (evverb in _OUT_VERBS or (_FLY_FIX and evverb in _FLY_AWAY))
        evwords = set(re.findall(r"[a-z]+", clause.text().lower())) if _CHANGE_EVENT else set()
        values = [(x, evaluate(x["expr"], atoms)) for x in chosen]
        for x, v in values:
            if v is not None:
                evkey = clause.cell(x["target"].replace("F:", ""))
                evfresh = evkey not in sit.cells
                write(sit, clause, x["target"], v)
                if _CHANGE_EVENT and evkey and v.known and not x["target"].startswith("F:"):
                    evcell = sit.cells.get(evkey)
                    # a clause that also states a balance ('he spent a TOTAL of $700', 'initially
                    # had 34') writes that balance, not a tally -- only a bare change statement
                    # ('gave away 11', 'sold 12') starts an event cell
                    if evout and evfresh and not evwords & {"had", "has", "have", "is", "are",
                                                            "was", "were", "initially", "originally",
                                                            "before", "now", "still", "total",
                                                            "altogether", "together"}:
                        # a change statement CREATED this cell: it tallies what went out of it,
                        # it is not a balance ('a clown gave away 11' -> 11 given, nothing told now)
                        sit.events[evkey] = v.c
                    elif evout and evkey in sit.events and evcell and evcell[1].known:
                        sit.events[evkey] = evcell[1].c      # the tally runs with the cell's now
                    elif evverb is None and evkey in sit.events and evcell and evcell[1].known:
                        # a stative write ('now he has 3') stands on a balance the story never told:
                        # at first the cell held the tally more (sold 12; now has 3 -> at first 15)
                        sit.cells[evkey][0] = Lin(evcell[1].c + sit.events[evkey])
                        del sit.events[evkey]
                    elif evkey in sit.events and evcell and evcell[1].known:
                        # an arrival (or any other write) reusing the cell for a different quantity
                        # ('spent $2' then 'bought for $7 each') breaks the tally: drop the mark
                        del sit.events[evkey]
                done.append({**x, "value": v, "work": show_work(x["expr"], atoms)})
        if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
            sit.subject = clause.persons[0]
        elif clause.thing_subject and not clause.persons:
            sit.subject = clause.thing_subject
        if done:                               # the last thing it changed stays in mind (as when it learns)
            sit.thing = (clause.cell(done[self.LAST]["target"].replace("F:", ""))[1], ())
        elif clause.things:
            sit.thing = (clause.things[-1][0], ())
        return done or None

    def answer(self, clause, sit, rivals=None, atoms_out=None):
        """The surest meaning for this question. `rivals` (a list) is filled with the value of the next
        reading that genuinely competes, and `atoms_out` (a dict) with the numbers it used, so the
        prefrontal can doubt and check without a second pass."""
        atoms = clause.atoms(sit, question=True)
        if atoms_out is not None:
            atoms_out.update(atoms)
        # The request gate: the question says what the answer must be a count OF, so only readings
        # that could count that noun may answer it -- and no count of things is between none and one
        # (a dollars-per-pen rate is not an answer to 'how many pens'). If the gate leaves nothing,
        # the reader says it doesn't understand (like the taught recipes do), instead of guessing.
        asked = what_is_asked(clause.text())
        thing = singular(asked["thing"] or "") if asked["kind"] != "money" else singular(asked["thing"] or "")
        cands = self.candidates("Q", clause, atoms)
        if thing:
            keep = [x for x in cands if counts_thing(clause, x["expr"], thing)]
            # ('^' groups-needed counts the bottom noun and '/' a top counted out of bottoms, so the
            # correct '253 people ^ 5 per car' survives through that general rule -- no special case.)
            # The owner scope: 'how many people are in ONE CAR' wants the people of one car, so only
            # readings that live in car-owned cells may answer it (the total, 253, does not). It is a
            # preference, not a veto: with no scoped reading left it keeps what the count gate kept.
            owner = scope_owner(clause, thing)
            if owner:
                scoped = [x for x in keep if by_owner(clause, x["expr"], owner)]
                keep = scoped or keep
            cands = keep
        # The total question: 'how many muffins does first grade bake IN ALL' asks over every cell
        # of that noun (18 + 20 + 17 across three class owners), but the question's own slots only
        # reach one of them -- so the sum of the cells themselves is written as a candidate. Only
        # cells with a NAMED owner count: ownerless cells are the context's own total (or another
        # quantity in the same unit, like the pool's length), not parts of a list.
        if _LIST_FIX and thing and _TOTAL_Q.search(" ".join(re.findall(r"[a-z]+", clause.text().lower()))):
            total, vals = None, []
            for key in sit.cells:
                if key[1] != thing or key[0] is None:
                    continue
                v = sit.read(*key)
                if v is None or not v.known:
                    continue
                vals.append(v.c)
                total = v.c if total is None else total + v.c
                if len(vals) >= 8:
                    break
            # a part next to its own total ('each plate has 4' + the inferred 28) must not be added
            # to that total: when one cell's value divides another's, these are whole-and-parts, so
            # the total question falls back to its usual single-cell reading. Two cells are also
            # too easy to misread (a per-herd part next to a written total); a genuine list has
            # at least THREE owners' parts.
            parts = any(a and a < b and (b / a).denominator == 1 for a in vals for b in vals)
            if len(vals) >= 3 and not parts:      # the expression grammar holds two terms, so the
                v = Lin(total)                    # sum of many cells is written as one atom
                atoms["Z"] = v
                if atoms_out is not None:
                    atoms_out["Z"] = v
                cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total",
                                 "target": "ANS", "expr": "Z"})
        # The rate question: '5 apples every hour' left the per-unit amount in a TIME-OWNED cell, and
        # 'at the END OF 3 hours' supplies the unit count -- the answer is their product. The learned
        # 'in N days' key offers this for its own phrasing; this covers the other time phrasings, and
        # only when the thing's own cell is owned by a time word (a rate lives under its unit).
        if _RATE_FIX and thing and "N1" in atoms and atoms["N1"].known:
            text = " ".join(re.findall(r"[a-z]+", clause.text().lower()))
            if _RATE_Q.search(text) and set(text.split()) & _TIME_UNITS:
                slot = next((s for s in sorted(atoms) if re.fullmatch(r"P\d+\.T\d+", s)
                             and atoms[s].known and clause.cell(s)
                             and clause.cell(s)[0] in _TIME_UNITS), None)
                if slot:                             # the cell that holds the rate lives under its unit
                    expr = f"N1*{slot}"             # ('hour's apple' x 3 hours)
                    if counts_thing(clause, expr, thing):    # the learned 'end of' key holds this too,
                        cands = [x for x in cands if x["expr"] != expr]   # but AFTER its doubling guess
                        cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "rate",
                                         "target": "ANS", "expr": expr})
        # The event question: a cell a change statement CREATED with no balance told only tallies
        # what went out of it ('a clown gave away 11, then 3 more' -> the cell holds 14 GIVEN, not a
        # balance). A change question over such a cell wants that tally -- the now-minus-first
        # difference of a tally (14-11) is not the amount given. 'give away TOTAL' still asks for
        # that tally, but the direction requests ('left', 'before', 'at first', 'in a year') are
        # other readings of the same cells and stay out.
        if _CHANGE_EVENT and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if (words & _DELTA_Q and
                    not words & {"left", "remain", "remains", "before", "first", "start", "begin",
                                 "beginning", "now", "more", "need", "have", "has", "had", "are",
                                 "is", "there", "still", "in", "each", "again", "all"}):
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")) or clause.cell(base) not in sit.events:
                        continue
                    if thing and not counts_thing(clause, base, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "event",
                                     "target": "ANS", "expr": base})
                    break
        # The change question: 'how many WERE ADDED / did he eat / did she give' wants the changed
        # amount, not the quantity as it stands now. When a cell it wrote twice is known both now and
        # at first, the answer is the difference -- and the plain 'it is now' reading of that same cell
        # (which ignores the question's own verb) is dropped rather than kept as a rival opinion.
        if (_CHANGE_FIX or _CHANGE_FIX_DELTA) and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if words & _DELTA_Q and not words & _NO_DELTA_Q:
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")):
                        continue
                    if _CHANGE_EVENT and clause.cell(base) in sit.events:
                        continue    # a tally's now-minus-first is not the amount given: the event
                                    # block above already offered the tally itself
                    a, b = atoms[base], atoms[name]
                    if not (a.known and b.known) or a.c == b.c:
                        continue
                    expr = f"{base}~{name}"
                    if thing and not counts_thing(clause, expr, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": "ANS", "expr": expr})
                    break
        # The before question: 'how many oranges were in the basket BEFORE some were taken' wants the
        # quantity as it started, not as it stands now. The cell keeps its at-first value (the F:
        # atom), so the answer is that first value and the plain now-reading of the same cell is
        # dropped -- the delta question's trade, in the other direction.
        if _BEFORE_FIX and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if words & _BEFORE_Q and not words & _NO_BEFORE_Q:
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")):
                        continue
                    a, b = atoms[base], atoms[name]
                    if not (a.known and b.known) or a.c == b.c:
                        continue
                    if thing and not counts_thing(clause, name, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "before",
                                     "target": "ANS", "expr": name})
                    break
        best = spared = None
        for x in cands:
            if best is not None and (x["rank"] < 1 or x["c"] < best[2] - 0.12):
                continue                      # it cannot rival the surest reading: don't even work it out
            v = evaluate(x["expr"], atoms)
            if v is not None:
                v = v.bind(sit.bound)
                if v.known:
                    said = {**x, "work": show_work(x["expr"], atoms)}
                    if _NONNEG_FIX and v.c < 0:
                        continue          # no quantity (nor difference of quantities) is negative
                    if thing and v.c != 0 and v.c < 1:
                        spared = spared or (v.c, said, x["c"])
                        continue              # not a count of things; kept only as a last resort
                    if best is None:
                        best = (v.c, said, x["c"])
                    elif rivals is not None and v.c != best[0]:
                        rivals.append((v.c, x["c"]))  # a reading that competes, with its sureness
                        break
        best = best or spared
        return (None, None) if best is None else (best[0], best[1])

    def summary(self):
        meaningful = {}
        for kind in ("S", "Q"):
            star = self.table[kind].get("*", {"n": 0, "m": {}})
            for k, e in self.table[kind].items():
                if k.startswith("*") or "|*" in k or e["n"] < 3:
                    continue
                p, cnt = max(e["m"].items(), key=lambda kv: (_sure(e, kv[0]), kv[1]), default=(None, 0))
                if not p or cnt < 3 or _sure(e, p) < 0.75:
                    continue
                shape = self.table[kind].get("*|" + k.split("|", 1)[1].replace("_", ""))
                if shape and shape["m"] and p == max(shape["m"], key=lambda q: (_sure(shape, q) >= 0.5, shape["m"][q])):
                    continue                                   # the frame does that anyway: a grammar word here
                meaningful[k] = p
        pronouns = {w: self.pronoun(w) for w in self.pron if self.pronoun(w)}
        return meaningful, pronouns


def _sure(e, p):
    """How often an explanation came true when it was possible."""
    if not e or not e.get("n"):
        return 0
    cnt = e["m"].get(p, 0)
    return cnt / max(e.get("o", {}).get(p, e["n"]), cnt, 1)


# ---- reading a whole story ---------------------------------------------------------------------------


class StoryReader:
    def __init__(self, lexicon, frames, doubts=None):
        self.lex, self.frames = lexicon, frames
        self.doubts = doubts if doubts is not None else Doubts()

    def solve(self, text, sit=None, override=None):
        """Act the story out. -> (answer or None, how, trace). override: {clause index: [pair]} to try."""
        sit = sit or Situation()
        sit.units = self.frames.units
        sents = sentences(text)
        if not sents:
            return None, "nothing to read", []
        if getattr(self.lex, "CONTEXT", False):
            self.lex.read_context(sents)                  # first a look at how the story uses its words
        q = split_question(sents[-1])
        body = sents[:-1] if q else sents

        # Request gate: read the question first to know what kind of answer is wanted.
        # If the request is confidently identified (not "count"), only allow readings that
        # could answer it. This prevents confident wrong answers like "how many people"
        # on a story about cars.
        asked = None
        if q:
            asked = what_is_asked(" ".join(q[1]))

        trace, idx, unsure, guessed = [], 0, [], []
        parts = [s for s in body] + ([q[0]] if q and q[0] else [])
        for toks in parts:
            for items in clauses(perceive(toks, self.lex, sit), self.lex, sit):
                c = Clause(items, sit)
                if override and idx in override:
                    done = self._force(c, sit, override[idx])
                else:
                    done = self.frames.apply(c, sit, asked)
                sure = self._sure(c, done)
                trace.append({"clause": c.text(), "did": [self._say(c, d) for d in done or []],
                              "how": done[0]["key"] if done else None, "sure": sure,
                              "unknown": unfamiliar(c, self.lex) if c.nums else []})
                if c.nums and not done:
                    unsure.append(c.text())
                elif c.nums and not sure:
                    guessed.append(c.text())
                idx += 1
        if not q:
            return None, "no question", trace
        c = Clause(perceive(q[1], self.lex, sit), sit)
        rivals, qatoms = [], {}
        value, x = self.frames.answer(c, sit, rivals, qatoms)
        sure = self._sure(c, [x] if x else None)
        trace.append({"clause": c.text(), "question": True, "did": [self._say(c, x)] if x else [], "how": x and x["key"],
                      "sure": sure, "unknown": unfamiliar(c, self.lex)})
        if value is None:
            return None, "didn't understand the question" if not x else "doesn't know enough", trace
        if not sure:
            guessed.append(c.text())
        if unsure or guessed:
            return value, "guessed: " + "; ".join([f"didn't understand '{u}'" for u in unsure] +
                                                  [f"only guessed '{g}'" for g in guessed]), trace
        doubts, checks = self.doubt_about(text, c, sit, value, x, rivals, qatoms)   # the prefrontal asks and checks
        trace[-1]["doubts"], trace[-1]["checks"] = doubts, checks
        if doubts:
            return value, "not sure: " + "; ".join(doubts), trace
        return value, "understood every sentence", trace

    def doubt_about(self, text, clause, sit, value, x, rivals=(), atoms=None):
        """Before it claims to have understood: do the surest readings disagree (a second opinion), does
        the tool that made this answer agree when it works it out again, and has any of these words led
        it wrong before? -> (doubts in words, checks in words)."""
        doubts, checks = [], []
        if rivals:
            r = rivals[0]
            r_val, r_c = (r if isinstance(r, tuple) else (r, None))
            if _RIVAL_TIEBREAK and r_c is not None and x and r_c < x.get("c", 0):
                # CF: the rival is merely CLOSE in sureness (the answer loop lets anything within
                # 0.12 compete), not surer -- the surest reading already won, no second opinion here
                checks.append(f"the surest reading wins: {fmt(value)} over the rival {fmt(r_val)}")
            else:
                doubts.append(f"two ways of reading the question give {fmt(value)} or {fmt(r_val)}")
        if x:
            atoms = atoms if atoms is not None else clause.atoms(sit, question=True)
            names = uses(x["expr"])
            if len(names) == 2 and all(n in atoms and atoms[n].known for n in names):
                a, b = atoms[names[0]].c, atoms[names[1]].c
                for op in tool_ops(x["expr"]):
                    checked = self.frames.coord.check_story(op, a, b, value)
                    if checked is None:
                        continue
                    checks.append(checked[1])
                    if checked[0]:
                        self.doubts.passed("tool")
                    else:
                        doubts.append("the working does not check out: " + checked[1])
                        self.doubts.doubt("check", f"a {op} working did not check out on: {text[:60]}")
        if self.doubts.words and not _WORD_DOUBT_RELEASE:
            doubtful = sorted(w for w in _content_words(text) if self.doubts.doubted(w))
            if doubtful:
                doubts.append("these words have led me wrong before: " + ", ".join(doubtful[:3]))
        return doubts, checks

    def _sure(self, c, done):
        """Understood = it knows every word of the clause (heard it at least 3 times) and how sure the meaning it
        used is. A sentence with a word it never met is at best a guess, whatever the frame says."""
        if not done:
            return False
        return not unfamiliar(c, self.lex) and min(d["c"] for d in done) >= 0.6

    def _force(self, c, sit, pairs):
        atoms = c.atoms(sit)
        done = []
        for p in pairs:
            target, expr = p.split("=", 1)
            v = evaluate(expr, atoms)
            if v is not None and c.cell(target.replace("F:", "")):
                write(sit, c, target, v)
                done.append({"target": target, "expr": expr, "key": "taught", "value": v, "c": 1.0, "rank": 3})
        if c.persons:
            sit.subject = c.persons[0]
        if done:
            sit.thing = (c.cell(done[0]["target"].replace("F:", ""))[1], ())
        return done or None

    def _say(self, c, d):
        """Back in words: 'tom.apple = tom.apple - 2 -> 5'."""
        def name(label):
            if label.startswith("K"):
                return getattr(c, 'unit', 'the unit')
            if label.startswith("N"):
                n = c.nums[int(label[1:]) - 1]
                return "some" if n is not None and not n.known else str(n.c if n is not None else "?")
            first = label.startswith("F:")
            cell = c.cell(label[2:] if first else label)
            if not cell:
                return label
            owner, noun, desc = cell
            s = f"{owner or 'there'}'s {' '.join(sorted(desc))} {noun}".replace("  ", " ")
            return f"{s} at first" if first else s
        expr = re.sub(r"F:P\d\.T\d(?:@D\d)?|P\d\.T\d(?:@D\d)?|N\d|K\d", lambda m: name(m[0]), d["expr"])
        expr = re.sub(r"^\((.+)/(.+)\)\*(.+)$", lambda m: f"{m[1]} \u00f7 {m[2]} for one, times {m[3]}", expr)
        expr = re.sub(r"(.+)([%&^#$!])(.+)", lambda m: {"%": f"{m[1]} left over after groups of {m[3]}",
                                                         "&": f"full groups of {m[3]} in {m[1]}",
                                                         "^": f"groups of {m[3]} needed for {m[1]}",
                                                         "#": f"the greatest common factor of {m[1]} and {m[3]}",
                                                         "$": f"the least common multiple of {m[1]} and {m[3]}",
                                                         "!": f"{m[1]} percent of {m[3]}"}[m[2]], expr)
        target = "answer" if d["target"] == "ANS" else name(d["target"])
        v = d.get("value")
        return f"{target} = {expr}" + (f" = {fmt(v)}" if v is not None else "") + \
            (f" ({d['work']})" if d.get("work") else "")


def fmt(v):
    if isinstance(v, Lin):
        if not v.known:
            return "?"
        v = v.c
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


# ---- learning from a told story (scenes) and from a teacher's answer ----------------------------------


def learn_tale(tale, lex, frames):
    """A story from the world: after every sentence the brain sees the scene, and at the end the answer."""
    sit = Situation()
    sit.units = frames.units
    if getattr(lex, "CONTEXT", False):
        lex.read_context([t for line in tale.lines for t in sentences(line[0])] + sentences(tale.question))
    for sentence, truth, firsts in tale.lines:
        truth, firsts = lower_truth(truth), lower_truth(firsts)
        toks = sentences(sentence)
        after = Situation()
        after.cells = {k: list(v) for k, v in sit.cells.items()}
        changed = after.see(truth, firsts)
        for t in toks:
            for items in clauses(perceive(t, lex, sit), lex, sit):
                c = Clause(items, sit, learning=True)
                frames.met_things(c)
                frames.observe_statement(c, sit, after)
                named = {n for n, _ in c.things} | {it[1] for it in items if it[0] == "P" and not it[3]}
                unnamed = {o for o, _, _ in changed if o and o not in named}
                if unnamed:                                 # someone it isn't told by name: the pronoun's evidence
                    involved = {sit.gender.get(o, None if lex.person(o) else "thing") for o in unnamed}
                    frames.observe_pronouns(c, involved - {None})
                if c.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                    sit.subject = c.persons[0]
                elif c.thing_subject:
                    sit.subject = c.thing_subject
            frames.hear(t)                       # heard now; while reading it, its new words were still new
        sit.cells = after.cells
        if changed:
            sit.thing = (changed[-1][1], ())
        for o, _, _ in changed:
            if o and o not in sit.people:
                sit.mention(o, None if lex.person(o) or o[0].isupper() else "thing")
    q = split_question(sentences(tale.question)[-1])
    if q[0]:
        frames.observe_statement(Clause(perceive(q[0], lex, sit), sit, learning=True), sit, sit)
    c = Clause(perceive(q[1], lex, sit), sit, learning=True)
    frames.met_things(c)
    frames.observe_question(c, sit, tale.answer)
    frames.hear(sentences(tale.question)[-1])


def learn_from_answer(text, answer, reader, frames, weight=3):
    """The teacher told the answer to a whole story (no scenes). If it got it right, it strengthens what
    it did. If not, it looks for the ONE thing it misread: the question, or one sentence, so that acting
    the story out gives the teacher's answer, and learns that."""
    answer = Fraction(answer)
    got, how, trace = reader.solve(text)
    if got == answer:
        reader.doubts.confirmed(_words(trace))              # the teacher agrees: those words were fine
        reader.doubts.passed("answer")                      # ... and the answer checked out
        _reinforce(text, reader, frames, weight=1)
        return {"agreed": True, "own_answer": fmt(got) if got is not None else None, "learned": "what it did was right"}
    # it was wrong. First find the ONE thing it misread, then charge only the words of THAT sentence (or the
    # question, or - if nothing could be found - of the sentences it was unsure about). Doubting the words of
    # every unsure sentence is how 'basket', 'hilt' and 'green' got to the cap and now veto readings they had
    # nothing to do with.
    # 1) the question: an explanation over what it acted out
    sit = Situation()
    reader.solve(text, sit=sit)
    sents = sentences(text)
    q = split_question(sents[-1])
    if q:
        c = Clause(perceive(q[1], reader.lex, sit), sit)
        atoms = {k: v for k, v in c.atoms(sit, question=True).items() if v.known}
        exprs = expressions(atoms, frames.ops_for(c)).get(answer, [])
        if exprs and all(d.get("sure") for d in trace[:-1] if d["did"] or any(ch.isdigit() for ch in d["clause"])):
            reader.doubts.doubt("answer", f"I got '{text[:60]}' wrong", _content_words(trace[-1]["clause"]))
            frames.credit("Q", c, [f"ANS={e}" for e in exprs], atoms, weight)
            return {"agreed": False, "own_answer": fmt(got) if got is not None else None,
                    "learned": f"the question means: {reader._say(c, {'target': 'ANS', 'expr': exprs[0]})}",
                    "how": "question"}
    # 2) one sentence it misread
    n_clauses = sum(1 for t in trace if not t.get("question"))
    for idx in sorted(range(n_clauses), key=lambda i: (bool(trace[i].get("sure")), bool(trace[i]["did"]))):
        for pairs in _alternatives(text, idx, reader):
            g, _, _ = reader.solve(text, override={idx: pairs})
            if g == answer:
                _credit_clause(text, idx, pairs, reader, frames, weight)
                c, _ = _clause_at(text, idx, reader)
                reader.doubts.doubt("answer", f"I got '{text[:60]}' wrong", _content_words(trace[idx]["clause"]))
                said = "; ".join(reader._say(c, dict(zip(("target", "expr"), p.split("=", 1)))) for p in pairs)
                return {"agreed": False, "own_answer": fmt(got) if got is not None else None,
                        "learned": f"'{trace[idx]['clause']}' means: {said}", "how": "sentence"}
    reader.doubts.doubt("answer", f"I got '{text[:60]}' wrong", _words(trace, only_unsure=True))
    return {"agreed": False, "own_answer": fmt(got) if got is not None else None, "learned": None,
            "note": "I couldn't find which sentence I misread, so I didn't learn anything"}


_PLAIN = {"the", "a", "an", "is", "are", "was", "were", "has", "have", "had", "of", "to", "in", "on", "at",
          "it", "he", "she", "they", "we", "you", "this", "that", "and", "but", "or", "so", "then", "than",
          "how", "many", "much", "does", "do", "did", "now", "what", "when", "with", "for", "from", "his",
          "her", "their", "there", "here", "who", "which", "by", "as", "be", "been", "will", "would", "can",
          "more", "less", "few", "each", "every", "some", "any", "all", "both", "left", "still", "again"}


_WORD_CACHE = {}                  # story text -> its content words (sleep relives the same stories)


def _content_words(text):
    """The words in a story that could mean something (common words left out), memoised: sleep replays
    the same stories and the doubt check asks for this on every sure answer."""
    key = text if len(text) <= 400 else text[:400]
    got = _WORD_CACHE.get(key)
    if got is None:
        got = {w for w in re.findall(r"[a-z]+", key.lower()) if w not in _PLAIN and len(w) > 2}
        if len(_WORD_CACHE) < 20000:
            _WORD_CACHE[key] = got
    return got


def _words(trace, only_unsure=False):
    """The words of the sentences it had trouble with; when it was sure of all of them (and still got it
    wrong) the whole story. Common words are left out: they tell nothing about what it misread."""
    lines = [d["clause"] for d in trace if d.get("clause") and (not only_unsure or not d.get("sure"))]
    if only_unsure and not lines:
        lines = [d["clause"] for d in trace if d.get("clause")]
    out = set()
    for line in lines:
        out |= _content_words(line)
    return out


def _clause_at(text, idx, reader):
    """Replay the story up to clause idx; -> (clause, situation before it)."""
    sit = Situation()
    sit.units = reader.frames.units
    sents = sentences(text)
    q = split_question(sents[-1])
    parts = (sents[:-1] if q else sents) + ([q[0]] if q and q[0] else [])
    k = 0
    for toks in parts:
        for items in clauses(perceive(toks, reader.lex, sit), reader.lex, sit):
            c = Clause(items, sit)
            if k == idx:
                return c, sit
            reader.frames.apply(c, sit)
            k += 1
    return None, None


def _alternatives(text, idx, reader):
    c, sit = _clause_at(text, idx, reader)
    if not c:
        return []
    atoms = c.atoms(sit)
    known = {k: v for k, v in atoms.items() if v.known}
    exprs = [e for es in expressions(known, reader.frames.ops_for(c)).values() for e in es]
    if any(not v.known for v in atoms.values()):
        exprs += [k for k, v in atoms.items() if not v.known]
    exprs = sorted(set(exprs), key=lambda e: (len(uses(e)), "*2" in e or "/2" in e, e))[:60]
    return [[f"{label}={e}"] for label in list(c.labels())[:4] for e in exprs if e != label]


def _credit_clause(text, idx, pairs, reader, frames, weight):
    c, sit = _clause_at(text, idx, reader)
    if c:
        frames.credit("S", c, pairs, c.atoms(sit), weight)


def _reinforce(text, reader, frames, weight=1):
    sit = Situation()                       # replay and credit what it did, clause by clause
    sit.units = frames.units
    sents = sentences(text)
    q = split_question(sents[-1])
    parts = (sents[:-1] if q else sents) + ([q[0]] if q and q[0] else [])
    for toks in parts:
        for items in clauses(perceive(toks, reader.lex, sit), reader.lex, sit):
            c = Clause(items, sit)
            atoms = c.atoms(sit)
            done = frames.apply(c, sit)
            if done:
                frames.credit("S", c, [f"{d['target']}={d['expr']}" for d in done], atoms, weight)
    if q:
        c = Clause(perceive(q[1], reader.lex, sit), sit)
        _, x = frames.answer(c, sit)
        if x:
            frames.credit("Q", c, [f"ANS={x['expr']}"], c.atoms(sit, question=True), weight)
