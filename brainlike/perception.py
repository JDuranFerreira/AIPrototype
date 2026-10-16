"""Word forms and (later) the rest of perception: what each word IS in a sentence.

Extracted from storyreader.py (size plan steps 3-4, 2026-10-09); storyreader re-exports every
name here so old imports keep working. Step 3 moved the pure word-form helpers; step 4 moves
the rest (tokens, Lexicon, perceive, clauses, Clause).
"""
import re
from fractions import Fraction

from . import wordvec
from .expressions import expressions
from .model import Lin



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


_WHERE = {"at", "in", "on", "for", "with", "after", "to", "from", "into", "near", "by", "before", "during"}
_NOT_NOUNS = {"same", "total", "lot", "few", "little", "most", "rest", "other", "next", "first", "last", "start",
              "beginning", "end", "more", "half", "day", "way", "time", "week", "year", "moment", "while"}


# ---- tokens, sentences, the lexicon ---------------------------------------------------------------


_TOKEN = re.compile(r"\d+(?:\.\d+)?|[a-z]+(?:[-'][a-z]+)*|[.?!,]")
_GLUE = {"the", "a", "an", "if", "then", "now", "and", ",", "so"}
_BREAK = {"and", ",", "then", "while", "but"}


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


_FUNCTION = _DET | _SMALL | _BETWEEN | _NOT_NOUNS | _WHERE | _GLUE | _BREAK   # words with a grammar job, not things




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
        from .storyreader import _NAMES_FIX          # late: the CF runners set it on storyreader
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

_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
               "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
               "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
               "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
               "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
               "flew", "added", "gained", "read"}


# ---- one clause's slots ---------------------------------------------------------------------------


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


# ---- word sets and question shapes (from storyreader's flag farm, 2026-10-09) --------------------


_NOUN_SHAPE_MAX = 15                       # a word whose Frames rows total this many lessons is not a verb

_OUT_VERBS = {"sold", "gave", "gaveaway", "lost", "ate", "used", "spent", "removed", "deleted",
              "finished", "read", "filled", "threw", "took", "taken", "eaten"}

_IN_VERBS = {"bought", "got", "received", "collected", "picked", "found", "brought", "board", "boarded", "get"}

_FLY_AWAY = {"flies", "fly", "flew", "flown", "flying"}

_BEFORE_Q = {"before", "originally", "initially", "begin", "beginning", "first", "start", "started"}

_NO_BEFORE_Q = {"left", "remain", "remains", "difference", "differences", "now", "total", "totals",
                "together", "altogether", "more", "again", "still", "next"}

_TOTAL_Q = re.compile(r"\b(?:in all|altogether|in total|all together|together)\b")

_RATE_Q = re.compile(r"\b(?:end of|after|within)\b")

_RATE_PHRASE = re.compile(r"\b(?:every|each|per|a|an)\s+(day|hour|week|month|year|night|minute|second)s?\b")

_TIME_UNITS = {"day", "hour", "week", "month", "year", "night", "minute", "second"}

_DELTA_Q = _OUT_VERBS | _IN_VERBS | ((_FLY_AWAY) |
        {"add", "added", "give", "gives", "giving", "given", "eat", "eats",
         "eating", "delete", "deletes", "deleting", "sell", "sells",
         "selling", "spend", "spends", "spending", "take", "takes",
         "taking", "use", "uses", "using", "finish", "finishing", "buy",
         "buys", "buying", "gets", "getting", "collect", "collecting"})

_NO_DELTA_Q = {"left", "remain", "remains", "now", "begin", "beginning", "start", "before", "first",
               "together", "altogether", "total", "each", "again", "more", "need", "needs", "needed",
               "have", "has", "had", "are", "is", "there", "still", "all", "in"}
