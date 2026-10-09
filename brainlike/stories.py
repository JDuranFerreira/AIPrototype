"""Stage 6 of the simulated world: a teacher who tells short stories.

Every sentence comes with the scene after it (who has how many of what), so the brain can see what the
sentence did, the way a child watches the apples move while hearing "Tom gives 2 apples to Ana". A scene
is {(owner, thing, frozenset(describing words)): how many}. The owner is None for things that just lie
somewhere ("there are 5 apples in the box"); describing words are colours, days and times of day.

The stories use present and past, he/she/his/her/him, comparisons (more, fewer, less, twice, half as
many), "each", days and times of day, colours, unknown amounts ("some", found out later) and halves.
"""
import random

from .world import COLOURS, CONTAINERS, COUNTABLE, DAYS, GAINS, LOSSES, MONEY_VERBS, PEOPLE, SETTINGS, TIMES, VERBS, plural


class Tale:
    def __init__(self, kind):
        self.kind = kind
        self.truth = {}
        self.first = {}            # what each thing was when the story started
        self.lines = []            # (sentence, scene after it, the starts)
        self.question = self.answer = None

    def put(self, owner, thing, n, *desc):
        k = (owner, thing, frozenset(desc))
        self.truth[k] = n
        self.first.setdefault(k, n)

    def add(self, owner, thing, n, *desc):
        k = (owner, thing, frozenset(desc))
        self.truth[k] = self.truth.get(k, 0) + n
        self.first.setdefault(k, self.truth[k])

    def get(self, owner, thing, *desc):
        want = set(desc)
        return sum(v for (o, t, d), v in self.truth.items() if o == owner and t == thing and want <= d)

    def say(self, sentence):
        self.lines.append((sentence, dict(self.truth), dict(self.first)))

    def ask(self, question, answer):
        self.question, self.answer = question, answer
        return self

    def text(self):
        return " ".join([line[0] for line in self.lines] + [self.question])


class Storyteller:
    KINDS = ["change", "transfer", "compare", "each", "days", "colours", "unknown", "half", "money"]

    def __init__(self, seed=0):
        self.r = random.Random(seed)

    def tale(self, kind=None):
        kind = kind or self.r.choice(self.KINDS)
        return getattr(self, f"_{kind}")(Tale(kind))

    # ---- helpers --------------------------------------------------------------------------------
    def _people(self, n):
        while True:
            ps = self.r.sample(list(PEOPLE), n)
            if n == 1 or len({PEOPLE[p] for p in ps}) == n:     # a clear teacher: he and she never mix two people up
                return ps

    @staticmethod
    def _he(p, form="sub"):
        boy = PEOPLE[p] == "boy"
        return {"sub": "he" if boy else "she", "pos": "his" if boy else "her", "obj": "him" if boy else "her"}[form]

    @staticmethod
    def _v(verb, past):
        return VERBS[verb][1] if past else VERBS[verb][0]

    @staticmethod
    def _has(past):
        return "had" if past else "has"

    def _who(self, p):
        """The person again: by name, or by he/she."""
        return self._he(p).capitalize() if self.r.random() < 0.6 else p

    def _at(self, p, chance=0.3):
        """Sometimes where or when it happened: ' at the park', ' for his birthday' (it changes no numbers)."""
        return " " + self.r.choice(SETTINGS).format(pos=self._he(p, "pos")) if self.r.random() < chance else ""

    def _end(self, p, n, thing):
        """How much someone has at the end, said in different ways."""
        he = self._he(p)
        return self.r.choice([f"Now {he} has {n} {thing}.", f"{he.capitalize()} still has {n} {thing}.",
                              f"{he.capitalize()} has {n} {thing} left.", f"In the end {he} has {n} {thing}."])

    # ---- story kinds ------------------------------------------------------------------------------
    def _change(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        past = r.random() < 0.5
        n = r.randint(5, 20)
        t.put(a, thing, n)
        if r.random() < 0.15:
            t.say(f"{a} {self._has(past)} a {r.choice(CONTAINERS)} of {n} {plural(thing)}{self._at(a)}.")
        else:
            t.say(f"{a} {'already ' if self.r.random() < 0.15 else ''}{self._has(past)} {n} {plural(thing)}{self._at(a)}.")
        events = []
        for i in range(r.choice([1, 1, 2])):
            verb = r.choice(GAINS + LOSSES)
            gain = VERBS[verb][2] == "+"
            m = r.randint(1, 9) if gain else r.randint(1, max(1, t.get(a, thing) - 1))
            t.add(a, thing, m if gain else -m)
            events.append(verb)
            who, style = self._who(a), r.random()
            if i and style < 0.3:
                t.say(f"Then {who.lower() if who != a else a} {self._v(verb, past)} {m} more.")
            elif i and style < 0.6:
                t.say(f"Then {who.lower() if who != a else a} {self._v(verb, past)} {m} more {plural(thing)}.")
            elif gain and style < 0.75:
                t.say(f"{who} {self._v(verb, past)} another {m} {plural(thing)}.")
            elif not gain and style < 0.75:
                t.say(f"{who} {self._v(verb, past)} {m} of {r.choice(['them', self._he(a, 'pos') + ' ' + plural(thing)])}.")
            else:
                t.say(f"{who} {self._v(verb, past)} {m} {plural(thing)}{self._at(a)}.")
        now = t.get(a, thing)
        q = r.random()
        if q < 0.1:
            return t.ask(f"How many {plural(thing)} does {a} {r.choice(['still have', 'have in the end'])}?", now)
        if q < 0.3:
            return t.ask(f"How many {plural(thing)} does {a} have now?", now)
        if q < 0.45:
            return t.ask(f"How many {plural(thing)} does {self._he(a) if r.random() < 0.5 else a} have left?", now)
        if q < 0.6:
            return t.ask(f"How many {plural(thing)} are left?", now)
        if q < 0.8 and len(events) == 1:
            return t.ask(f"How many {plural(thing)} did {a} {events[0]}?", abs(now - n))
        return t.ask(f"How many {plural(thing)} did {a} have {r.choice(['at first', 'in the beginning', 'initially', 'at the start'])}?", n)

    def _transfer(self, t):
        r = self.r
        a, b = self._people(2)
        thing = r.choice(COUNTABLE)
        past = r.random() < 0.5
        na, nb = r.randint(5, 20), r.randint(2, 20)
        t.put(a, thing, na)
        t.put(b, thing, nb)
        h = self._has(past)
        if r.random() < 0.3:
            t.say(f"{a} {h} {na} {plural(thing)} and {b} {h} {nb} {plural(thing)}.")
        else:
            t.say(f"{a} {h} {na} {plural(thing)}.")
            t.say(f"{b} {h} {nb} {plural(thing)}.")
        if r.random() < 0.6:
            m = r.randint(1, na - 1)
            t.add(a, thing, -m)
            t.add(b, thing, m)
            g = self._v("give", past)
            t.say(r.choice([f"{a} {g} {m} {plural(thing)} to {b}.", f"{a} {g} {b} {m} {plural(thing)}.",
                            f"{a} {g} {m} of {self._he(a, 'pos')} {plural(thing)} to {b}."]))
        else:
            m = r.randint(1, nb - 1)
            t.add(a, thing, m)
            t.add(b, thing, -m)
            t.say(f"{a} {self._v('take', past)} {m} {plural(thing)} from {b}.")
        va, vb = t.get(a, thing), t.get(b, thing)
        q = r.random()
        if q < 0.3:
            return t.ask(f"How many {plural(thing)} does {a} have now?", va)
        if q < 0.55:
            return t.ask(f"How many {plural(thing)} does {b} have now?", vb)
        if q < 0.8 or va == vb:
            return t.ask(f"How many {plural(thing)} do {a} and {b} have {r.choice(['altogether', 'in all'])}?", va + vb)
        hi, lo = (a, b) if va > vb else (b, a)
        if r.random() < 0.6:
            return t.ask(f"How many more {plural(thing)} does {hi} have than {lo}?", abs(va - vb))
        return t.ask(f"How many {r.choice(['fewer', 'less'])} {plural(thing)} does {lo} have than {hi}?", abs(va - vb))

    def _compare(self, t):
        r = self.r
        a, b = self.r.sample(list(PEOPLE), 2)
        thing = r.choice(COUNTABLE)
        past = r.random() < 0.5
        h = self._has(past)
        na = r.randint(2, 12) * 2
        t.put(a, thing, na)
        t.say(f"{a} {h} {na} {plural(thing)}.")
        how = r.choice(["more", "fewer", "twice", "half"])
        if how == "more":
            k = r.randint(1, 9)
            nb = na + k
            sentence = r.choice([f"{b} {h} {k} more {plural(thing)} than {a}.",
                                 f"{b} {h} {k} more {plural(thing)} than {a} does."])
        elif how == "fewer":
            k = r.randint(1, na - 1)
            nb = na - k
            sentence = f"{b} {h} {k} {r.choice(['fewer', 'less'])} {plural(thing)} than {a}."
        elif how == "twice":
            nb = na * 2
            sentence = f"{b} {h} twice as many {plural(thing)} as {a}."
        else:
            nb = na // 2
            sentence = f"{b} {h} half as many {plural(thing)} as {a}."
        t.put(b, thing, nb)
        t.say(sentence)
        q = r.random()
        if q < 0.5:
            return t.ask(f"How many {plural(thing)} does {b} have?", nb)
        if q < 0.8:
            return t.ask(f"How many {plural(thing)} do {a} and {b} have {r.choice(['altogether', 'in all'])}?", na + nb)
        hi, lo = (a, b) if na > nb else (b, a)
        return t.ask(f"How many more {plural(thing)} does {hi} have than {lo}?", abs(na - nb))

    def _each(self, t):
        r = self.r
        a, = self._people(1)
        box = r.choice(CONTAINERS)
        thing = r.choice([k for k in COUNTABLE if k != box])
        past = r.random() < 0.5
        n, m = r.randint(2, 9), r.randint(2, 9)
        t.put(a, box, n)
        t.say(f"{a} {self._has(past)} {n} {plural(box)}.")
        t.put(a, thing, n * m)
        t.say(r.choice([f"Each {box} {'had' if past else 'has'} {m} {plural(thing)}.",
                        f"There {'were' if past else 'are'} {m} {plural(thing)} in each {box}."]))
        if r.random() < 0.3:
            k = r.randint(1, n * m - 1)
            t.add(a, thing, -k)
            t.say(f"{self._who(a)} {self._v(r.choice(LOSSES), past)} {k} {plural(thing)}.")
            return t.ask(r.choice([f"How many {plural(thing)} does {a} have now?", f"How many {plural(thing)} are left?"]),
                         n * m - k)
        return t.ask(f"How many {plural(thing)} does {a} have{r.choice(['', ' altogether', ' in all'])}?", n * m)

    def _days(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        past = r.random() < 0.5
        verb = r.choice(GAINS)
        v = self._v(verb, past)
        days = r.random() < 0.6
        k = r.choice([2, 2, 3])
        slots = r.sample(DAYS if days else TIMES, k)
        on = (lambda d: f"on {d}") if days else (lambda d: f"in the {d}")
        counts = [r.randint(1, 20) for _ in slots]
        hidden = r.randrange(k) if r.random() < 0.25 else None
        for d, c in zip(slots, counts):
            t.put(a, thing, c, d)
        if hidden is None and r.random() < 0.3:
            parts = [f"{c} {plural(thing)} {on(d)}" for d, c in zip(slots, counts)]
            t.say(f"{a} {v} " + ", ".join(parts[:-1]) + " and " + parts[-1] + ".")
        else:
            t.truth = {}
            for i, (d, c) in enumerate(zip(slots, counts)):
                t.put(a, thing, c, d)
                who = a if i == 0 else self._who(a)
                amount = "some" if i == hidden else str(c)
                more = " more" if i and r.random() < 0.3 else ""
                t.say(f"{who} {v} {amount}{more} {plural(thing)} {on(d)}.")
        total = sum(counts)
        if hidden is not None:
            if r.random() < 0.5:
                t.say(f"{self._who(a)} {v} {total} {plural(thing)} {r.choice(['altogether', 'in all'])}.")
                return t.ask(f"How many {plural(thing)} did {a} {verb} {on(slots[hidden])}?", counts[hidden])
            return t.ask(f"If {self._he(a)} {v} a total of {total} {plural(thing)}, how many {plural(thing)} did {a} "
                         f"{verb} {on(slots[hidden])}?", counts[hidden])
        q = r.random()
        if q < 0.35:
            return t.ask(f"How many {plural(thing)} did {a} {verb} {r.choice(['altogether', 'in all'])}?", total)
        i, j = r.sample(range(k), 2)
        if q < 0.7 and counts[i] != counts[j]:
            hi, lo = (i, j) if counts[i] > counts[j] else (j, i)
            return t.ask(f"How many more {plural(thing)} did {a} {verb} {on(slots[hi])} than {on(slots[lo])}?",
                         counts[hi] - counts[lo])
        if k == 3:
            return t.ask(f"How many {plural(thing)} did {a} {verb} {on(slots[i])} and {on(slots[j])}?", counts[i] + counts[j])
        return t.ask(f"How many {plural(thing)} did {a} {verb} {on(slots[i])}?", counts[i])

    def _colours(self, t):
        r = self.r
        thing = r.choice(COUNTABLE)
        c1, c2 = r.sample([c for c in COLOURS if c != "orange"], 2)
        n1, n2 = r.randint(1, 20), r.randint(1, 20)
        past = r.random() < 0.5
        if r.random() < 0.5:
            a, = self._people(1)
            t.put(a, thing, n1, c1)
            t.put(a, thing, n2, c2)
            t.say(f"{a} {self._has(past)} {n1} {c1} {plural(thing)} and {n2} {c2} {plural(thing)}.")
            whose = have = f"does {a} have"
        else:
            box = r.choice(CONTAINERS)
            t.put(None, thing, n1, c1)
            t.put(None, thing, n2, c2)
            be = "were" if past else "are"
            t.say(r.choice([f"There {be} {n1} {c1} {plural(thing)} and {n2} {c2} {plural(thing)} in the {box}.",
                            f"{n1} {c1} {plural(thing)} and {n2} {c2} {plural(thing)} {be} in the {box}."]))
            whose, have = f"are in the {box}", "are there"
        q = r.random()
        if q < 0.35:
            return t.ask(f"How many {plural(thing)} {whose}{r.choice(['', ' altogether', ' in all'])}?", n1 + n2)
        if q < 0.7 and n1 != n2:
            hi, lo = (c1, c2) if n1 > n2 else (c2, c1)
            return t.ask(f"How many more {hi} {plural(thing)} than {lo} {plural(thing)} {have}?", abs(n1 - n2))
        c, n = r.choice([(c1, n1), (c2, n2)])
        return t.ask(f"How many {c} {plural(thing)} {whose}?", n)

    def _unknown(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        n = r.randint(5, 20)
        verb = r.choice(GAINS + LOSSES)
        gain = VERBS[verb][2] == "+"
        m = r.randint(1, 9) if gain else r.randint(1, n - 1)
        end = n + m if gain else n - m
        t.put(a, thing, n)
        if r.random() < 0.25:                                  # told out of order: the start comes after
            t.add(a, thing, m if gain else -m)
            t.say(f"{a} {self._v(verb, True)} {m} {plural(thing)}{self._at(a)}.")
            start = r.choice(["at first", "initially", "at the start"])
            left = r.choice(["now", "left"])
            if r.random() < 0.5:
                t.say(f"{self._he(a).capitalize()} had {n} {plural(thing)} {start}.")
                return t.ask(f"How many {plural(thing)} does {a} have {left}?", end)
            return t.ask(f"If {self._he(a)} had {n} {plural(thing)} {start}, how many {plural(thing)} does {self._he(a)} "
                         f"have {left}?", end)
        if r.random() < 0.5:                                   # it doesn't say how many there were at the start
            t.say(f"{a} had some {plural(thing)}.")
            t.add(a, thing, m if gain else -m)
            t.say(f"{self._who(a)} {self._v(verb, True)} {m} {plural(thing)}{self._at(a)}.")
            t.say(self._end(a, end, plural(thing)))
            return t.ask(f"How many {plural(thing)} did {a} have {r.choice(['at first', 'in the beginning', 'initially', 'at the start'])}?", n)
        t.say(f"{a} had {n} {plural(thing)}.")
        t.add(a, thing, m if gain else -m)
        t.say(f"{self._who(a)} {self._v(verb, True)} some{' more' if gain and r.random() < 0.5 else ''} {plural(thing)}{self._at(a)}.")
        t.say(self._end(a, end, plural(thing)))
        return t.ask(f"How many {plural(thing)} did {a} {verb}?", m)

    def _half(self, t):
        r = self.r
        a, b = self._people(2)
        thing = r.choice(COUNTABLE)
        past = r.random() < 0.5
        n = r.randint(2, 12) * 2
        t.put(a, thing, n)
        t.say(f"{a} {self._has(past)} {n} {plural(thing)}.")
        t.add(a, thing, -(n // 2))
        if r.random() < 0.6:
            t.say(f"{self._who(a)} {self._v(r.choice(LOSSES), past)} half of {self._he(a, 'pos')} {plural(thing)}.")
            return t.ask(r.choice([f"How many {plural(thing)} does {a} have left?", f"How many {plural(thing)} are left?",
                                   f"How many {plural(thing)} does {a} have now?"]), n // 2)
        t.add(b, thing, n // 2)
        t.say(f"{self._who(a)} {self._v('give', past)} half of {self._he(a, 'pos')} {plural(thing)} to {b}.")
        return t.ask(f"How many {plural(thing)} does {b} have now?", n // 2)

    def _money(self, t):
        """Dollars: spend, earn, save, buy something for $3. The scene shows only how much money people have."""
        r = self.r
        a, b = self._people(2)
        past = r.random() < 0.5
        n = r.randint(10, 40)
        t.put(a, "dollar", n)
        t.say(r.choice([f"{a} {self._has(past)} ${n}{self._at(a)}.", f"{a} {self._has(past)} ${n} in {self._he(a, 'pos')} wallet."]))
        spent = 0
        for i in range(r.choice([1, 1, 2])):
            kind = r.random()
            who = self._who(a)
            if kind < 0.45:
                m = r.randint(1, max(1, t.get(a, "dollar") - 1))
                thing = r.choice(COUNTABLE)
                t.add(a, "dollar", -m)
                spent += m
                v = MONEY_VERBS["spend"][1 if past else 0]
                t.say(r.choice([f"{who} {v} ${m} on a {thing}.", f"{who} {v} ${m} on {plural(thing)}{self._at(a)}.",
                                f"{who} {'bought' if past else 'buys'} a {thing} for ${m}."]))
            elif kind < 0.8:
                verb = r.choice(["earn", "save", "get", "find"])
                m = r.randint(1, 15)
                t.add(a, "dollar", m)
                t.say(f"{who} {MONEY_VERBS[verb][1 if past else 0]} ${m}{self._at(a)}.")
            else:
                m = r.randint(1, 15)
                t.add(a, "dollar", m)
                t.say(r.choice([f"{b} {'gave' if past else 'gives'} {self._he(a, 'obj')} ${m}.",
                                f"{who} {'got' if past else 'gets'} ${m} from {b}."]))
        now = t.get(a, "dollar")
        q = r.random()
        if q < 0.5:
            return t.ask(r.choice([f"How much money does {a} have now?", f"How much money does {a} have left?",
                                   f"How much money is left?", f"How much money does {self._he(a)} still have?"]), now)
        if q < 0.75 and spent and spent == n - now:
            return t.ask(f"How much money did {a} spend?", spent)
        return t.ask(f"How much money did {a} have {r.choice(['at first', 'initially', 'at the start'])}?", n)
