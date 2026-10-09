"""The world-based primary school: P1 and P2 taught from the simulated world, like the kindergarten.

The school region's way of teaching is kept (Singapore + Estonia): readiness pre-test on a copy ->
lessons -> self-assessment (it predicts its score from how many stories it says it understood) ->
exam on stories it never heard -> descriptive feedback, the teacher shows the right answers for what
it got wrong, more lessons of the weak kinds, and a retake (parallel exam B).

What is new is WHAT is taught. Every lesson is a story from the simulated world, and every sentence
comes with the scene after it, as in the kindergarten. The topics follow Singapore's P1 and P2 math
syllabus (see Vault research/2026-10-01-singapore-estonia-primary):
  P1  numbers to 100 (number words, from counting scenes); adding and taking away within 100;
      comparing (more / fewer, also told out of order); equal groups (x); sharing and grouping (/);
      money in cents; time in o'clock; length in cm
  P2  numbers to 1000; everything in P1 with bigger numbers; times tables (groups, prices);
      fractions of a whole; money in dollars and change; mass (kg) and volume (litres);
      two steps (groups, then some are eaten)
The outside exam for each level is ASDiv (grade 1 for P1, grade 2 for P2), read with no language
model; it is reported, not used to teach.

  python -m brainlike.primary P1            teach one level (saves the brain)
  python -m brainlike.primary P1 --dry-run  teach a copy, save nothing
"""
import argparse
import copy
import json
import random
import re
import sys
from datetime import date
from pathlib import Path

from .school import AL_BANDS, MASTERY, al
from .stories import Storyteller, Tale
from .world import COUNTABLE, DAYS, NUMBER_WORDS, PEOPLE, VERBS, World, plural

# ---- number words to 100 (and hundreds), for counting lessons ------------------------------------
TENS = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_word(n):
    if n < 21:
        return NUMBER_WORDS[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + (f"-{NUMBER_WORDS[o]}" if o else "")
    h, rest = divmod(n, 100)
    return f"{NUMBER_WORDS[h]} hundred" + (f" and {number_word(rest)}" if rest else "")


def counting_scene(r, top):
    """A scene with many things and the teacher counting them: 'there are forty-two marbles'."""
    n = r.randint(1, top) if top <= 1000 or r.random() < 0.5 else r.randint(1, 100)   # small things are counted too,
    kind = r.choice(COUNTABLE)                                                        # or 'one' drifts to 'one hundred'
    seen = [f"thing:{kind}", f"count:{n}", f"colour:{r.choice(['red', 'blue', 'green', 'yellow'])}"]
    said = number_word(n) if n <= 100 else str(n)      # big numbers are read as numerals (P2), so 'seven' stays 7
    heard = r.choice([f"there are {said} {plural(kind)}", f"look {said} {plural(kind)}", f"we count {said} {plural(kind)}"])
    return seen, heard


# ---- new kinds of stories for P1 and P2 -----------------------------------------------------------------
WHOLES = ["cake", "pizza", "pie", "pancake", "sandwich"]
LONG = ["pencil", "ruler", "ribbon", "rope", "stick", "crayon", "worm", "scarf"]
HEAVY = ["bag", "box", "basket", "parcel", "melon", "pumpkin"]
HOLDS = ["jug", "bottle", "bucket", "tank", "pot"]
EVENTS = ["game", "lesson", "party", "show", "film", "race"]
FRIENDS = ["children", "friends", "pupils"]


class SchoolTeller(Storyteller):
    """The kindergarten's storyteller plus the P1-P2 kinds of stories."""
    P1 = Storyteller.KINDS + ["groups", "share", "cents", "clock", "length", "before", "place", "parts", "difference",
                              "need", "rate", "removed"]
    P2 = P1 + ["fraction", "price", "pay", "mass"]
    P3 = P2 + ["leftover", "needed", "afford", "twostep"]          # division with remainder, two steps
    P4 = P3 + ["lastday"]                                          # the same with numbers to 100 000
    P5 = P4 + ["convert", "percent", "square"]                     # units, percentage, area of a square
    P6 = P5 + ["common", "meet", "speed"]                          # greatest common factor, least common multiple
    S1 = P6 + ["negative", "equation", "proportion", "average", "circle"]   # secondary 1
    S2 = S1 + ["ratio", "interest", "volume", "threestep"]                    # secondary 2

    def __init__(self, seed=0, kinds=None, top=100):
        super().__init__(seed)
        self.kinds = kinds or self.P1
        self.top = top

    def tale(self, kind=None):
        t = super().tale(kind or self.r.choice(self.kinds))
        if self.r.random() < 0.15:                       # sometimes the story starts with how the day was
            t.lines.insert(0, (self.r.choice(["It was a sunny day.", "It was a rainy day.", "It was a cold morning."]),
                               {}, {}))
        return t

    def _big(self, lo, hi):
        """Numbers up to the level's top (100 for P1, 1000 for P2), mostly small like real lessons."""
        return self.r.randint(lo, hi) if self.r.random() < 0.6 else self.r.randint(lo, max(hi, self.top // 2))

    # x: equal groups
    def _groups(self, t):
        r = self.r
        box, thing = r.choice(["plate", "bag", "box", "basket", "jar", "tray"]), r.choice(COUNTABLE)
        n, m = r.randint(2, 9), r.randint(2, 10)
        t.put(None, box, n)
        t.put(None, thing, n * m)
        on = "on" if box in ("plate", "tray") else "in"
        t.say(r.choice([f"There are {n} {plural(box)} with {m} {plural(thing)} {on} each {box}.",
                        f"Each of the {n} {plural(box)} has {m} {plural(thing)}.",
                        f"There are {n} {plural(box)}. There are {m} {plural(thing)} {on} each {box}."]))
        if " There are " in t.lines[-1][0]:                    # two sentences: split the scene too
            s1, s2 = t.lines[-1][0].split(" There are ")
            t.lines[-1:] = [(s1, {(None, box, frozenset()): n}, {(None, box, frozenset()): n}),
                            ("There are " + s2, dict(t.truth), dict(t.first))]
        return t.ask(f"How many {plural(thing)} are there{r.choice(['', ' altogether', ' in all'])}?", n * m)

    # /: sharing equally, and putting into groups
    def _share(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        n, m = r.randint(2, 9), r.randint(2, 10)
        total = n * m
        if r.random() < 0.5:
            who = r.choice(FRIENDS)
            t.put(a, thing, total)
            t.put(a, singular_of(who), n)
            t.say(f"{a} {r.choice(['shares', 'shared'])} {total} {plural(thing)} equally among {n} {who}.")
            return t.ask(f"How many {plural(thing)} does each {singular_of(who)} get?", m)
        box = r.choice(["bag", "box", "plate", "jar"])
        t.put(a, thing, total)
        t.put(a, box, n)
        t.say(f"{a} {r.choice(['puts', 'put'])} {total} {plural(thing)} into {plural(box)} of {m}.")
        return t.ask(r.choice([f"How many {plural(box)} does {a} have?", f"How many {plural(box)} are there?"]), n)

    # money in cents (P1) and dollars (P2)
    def _cents(self, t, unit="cents"):
        r = self.r
        x, y = r.sample(COUNTABLE, 2)
        p, q = r.sample(range(5, 95 if unit == "cents" else 30, 5 if unit == "cents" else 1), 2)
        t.put(x, unit[:-1], p)
        t.say(f"A {x} costs {p} {unit}.")
        t.put(y, unit[:-1], q)
        t.say(f"A {y} costs {q} {unit}.")
        k = r.random()
        if k < 0.4:
            return t.ask(r.choice([f"How many {unit} do they cost together?", f"How much do they cost together?",
                                   f"How many {unit} do a {x} and a {y} cost altogether?"]), p + q)
        if k < 0.7:
            hi, lo = (x, y) if p > q else (y, x)
            return t.ask(f"How much more does the {hi} cost than the {lo}?", abs(p - q))
        a, = self._people(1)
        have = max(p, q) + r.randint(1, 50)
        t.put(a, unit[:-1], have - p)
        t.first[(a, unit[:-1], frozenset())] = have
        t.lines.append((f"{a} has {have} {unit}.", {**t.truth, (a, unit[:-1], frozenset()): have}, dict(t.first)))
        t.say(f"{self._he(a).capitalize()} {r.choice(['buys', 'bought'])} a {x}.")
        return t.ask(f"How many {unit} does {a} have left?", have - p)

    # time in o'clock: an event's clock moves on while it lasts
    def _clock(self, t):
        r = self.r
        e = r.choice(EVENTS)
        s, d = r.randint(1, 8), r.randint(1, 4)
        t.put(e, "o'clock", s)
        if r.random() < 0.6:
            t.say(f"The {e} starts at {s} o'clock.")
            t.put(e, "o'clock", s + d)
            t.say(r.choice([f"It lasts {d} hours.", f"The {e} lasts {d} hours.", f"It ends {d} hours later."]))
            return t.ask(r.choice([f"At what o'clock does it end?", f"At what o'clock does the {e} end?"]), s + d)
        t.say(f"The {e} starts at {s} o'clock.")
        t.put(e, "o'clock", s + d)
        t.say(r.choice([f"It ends at {s + d} o'clock.", f"The {e} ends at {s + d} o'clock."]))
        return t.ask(f"How many hours does the {e} last?", d)

    # length in cm (P1), mass and volume (P2)
    def _length(self, t, unit="cm", things=LONG, verb="is {n} {unit} long", more="longer", less="shorter", how="How long"):
        r = self.r
        x, y = r.sample(things, 2)
        p, q = r.sample(range(2, 60), 2)
        t.put(x, unit, p)
        t.say(f"The {x} {verb.format(n=p, unit=unit)}.")
        if r.random() < 0.4:
            k = abs(q - p) or 1
            q = p + k if r.random() < 0.5 else max(1, p - k)
            t.put(y, unit, q)
            t.say(f"The {y} is {abs(q - p)} {unit} {more if q > p else less} than the {x}.")
            return t.ask(f"{how} is the {y}?", q)
        t.put(y, unit, q)
        t.say(f"The {y} {verb.format(n=q, unit=unit)}.")
        if r.random() < 0.5:
            hi, lo = (x, y) if p > q else (y, x)
            return t.ask(f"How much {more} is the {hi} than the {lo}?", abs(p - q))
        return t.ask(f"{how} are the {x} and the {y} together?", p + q)

    def _mass(self, t):
        if self.r.random() < 0.5:
            return self._length(t, "kg", HEAVY, "weighs {n} {unit}", "heavier", "lighter", "How heavy")
        return self._length(t, "litres", HOLDS, "holds {n} {unit}", "more", "less", "How much")

    # comparing, told out of order: 'Ellen has 6 more balls than Marin. Marin has 9 balls.'
    def _before(self, t):
        r = self.r
        a, b = r.sample(list(PEOPLE), 2)
        thing = r.choice(COUNTABLE)
        nb, k = r.randint(2, 20), r.randint(1, 9)
        more = r.random() < 0.6
        na = nb + k if more else max(1, nb - k)
        t.put(a, thing, na)
        t.put(b, thing, nb)
        first = dict(t.first)
        t.lines.append((f"{a} has {abs(na - nb)} {'more' if more else 'fewer'} {plural(thing)} than {b}.",
                        {(a, thing, frozenset()): na, (b, thing, frozenset()): nb}, first))
        t.say(f"{b} has {nb} {plural(thing)}.")
        if r.random() < 0.6:
            return t.ask(f"How many {plural(thing)} does {a} have?", na)
        return t.ask(f"How many {plural(thing)} do {a} and {b} have {r.choice(['together', 'altogether', 'in all'])}?",
                     na + nb)

    # things at a place: some come, some go ('birds on a fence', 'children on a bus')
    def _place(self, t):
        r = self.r
        who, where = r.choice([("bird", "on the fence"), ("bird", "in the tree"), ("duck", "in the pond"),
                               ("child", "on the bus"), ("frog", "on the rock"), ("fish", "in the pond"),
                               ("child", "in the park"), ("ant", "on the log")])
        many = {"child": "children", "fish": "fish"}.get(who, who + "s")
        n = self._big(2, 20)
        t.put(None, who, n)
        t.say(r.choice([f"{n} {many} are sitting {where}.", f"There are {n} {many} {where}.",
                        f"{n} {many} were {where}."]))
        come = r.random() < 0.5
        m = r.randint(1, 9) if come else r.randint(1, n - 1)
        t.add(None, who, m if come else -m)
        if come:
            t.say(r.choice([f"{m} more {many} come to join them.", f"{m} more {many} joined them.",
                            f"Then {m} more {many} came.", f"{m} more {many} get on."]))
        else:
            t.say(r.choice([f"{m} {many} fly away.", f"{m} {many} go home.", f"{m} {many} got off.",
                            f"{m} of them left.", f"Then {m} {many} went away."]))
        return t.ask(r.choice([f"How many {many} are {where} now?", f"How many {many} are there now?",
                               f"How many {many} are left?" if not come else f"How many {many} are there in all?"]),
                     t.get(None, who))

    # missing addend: 'How many more crickets do you need to collect to have 11 crickets?'
    def _need(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        have = self._big(2, 30)
        want = have + r.randint(1, 15)
        verb = r.choice(["collect", "pick", "find", "make", "buy", "get"])
        t.put(a, thing, have)
        t.say(f"{a} has {have} {plural(thing)}.")     # not 'has collected 7': it would teach 'collected' = has
        he = self._he(a) if r.random() < 0.5 else a
        return t.ask(r.choice([f"How many more {plural(thing)} does {he} need to have {want} {plural(thing)}?",
                               f"How many more {plural(thing)} does {he} need to {verb} to have {want} {plural(thing)}?",
                               f"How many more {plural(thing)} does {he} need to {verb} to have {want}?"]), want - have)

    # rates: 'Mrs. Hilt reads 5 books a day. How many books does she read in 3 days?'
    def _rate(self, t):
        r = self.r
        a, = self._people(1)
        verb, thing = r.choice([("read", "book"), ("make", "cake"), ("pick", "flower"), ("draw", "picture"),
                                ("bake", "cookie"), ("find", "shell"), ("collect", "stamp")])
        forms = {"read": ("reads", "read"), "draw": ("draws", "drew"), "bake": ("bakes", "baked")}.get(verb) or VERBS[verb][:2]
        past = r.random() < 0.4
        p, d = r.randint(2, 10), r.randint(2, 9)
        t.put(a, thing, p)
        t.first[(a, thing, frozenset())] = 0                   # none before the day: in a day the verb adds p
        t.say(f"{a} {forms[1] if past else forms[0]} {p} {plural(thing)} {r.choice(['a day', 'per day', 'each day', 'every day'])}.")
        he = self._he(a) if r.random() < 0.6 else a
        return t.ask(f"How many {plural(thing)} {'did' if past else 'does'} {he} {verb} in {d} days?", p * d)

    # things taken out of a place: 'Some of the balls were removed from the basket. Now there are six balls.'
    def _removed(self, t):
        r = self.r
        who, where, off = r.choice([("ball", "in the basket", "were removed from the basket"),
                                    ("apple", "in the box", "were taken out of the box"),
                                    ("student", "on the bus", "got off the bus"),
                                    ("child", "on the bus", "got off of the bus"),
                                    ("toy", "on the shelf", "were removed from the shelf"),
                                    ("pencil", "in the jar", "were removed from the jar")])
        many = {"child": "children"}.get(who, who + "s")
        n = self._big(3, 20)
        m = r.randint(1, n - 1)
        t.put(None, who, n)
        t.say(r.choice([f"There were {n} {many} {where}.", f"{n} {many} were {where}."]))
        t.add(None, who, -m)
        stop = r.choice(["", "At the first stop, ", "At the next stop, "]) if "bus" in where else ""
        if r.random() < 0.4:                                     # it doesn't say how many: found from the end
            t.say(f"{stop}Some of the {many} {off}.")
            t.say(r.choice([f"Now there are {n - m} {many}.", f"Now there are {n - m} {many} {where}."]))
            return t.ask(f"How many {many} {off}?", m)
        t.say(f"{stop}{m} {many} {off}.")
        return t.ask(r.choice([f"How many {many} are left {where}?", f"How many {many} are {where} now?",
                               f"How many {many} are left?"]), n - m)

    # ---- P3-P4 ---------------------------------------------------------------------------------------
    def _factor(self):
        """A times-table number: to 9 (P3 adds 6-9), bigger now and then once numbers go to 10 000 and 100 000."""
        r = self.r
        if self.top >= 100000 and r.random() < 0.4:
            return r.randint(11, 99)
        if self.top >= 10000 and r.random() < 0.3:
            return r.randint(10, 12)
        return r.randint(2, 9)

    def _uneven(self):
        """A total that doesn't share out evenly: groups of m, q full groups and r left over."""
        m, q = self._factor(), self._factor()
        return m, q, self.r.randint(1, m - 1)

    # division with a remainder: 'George has 17 candies. He puts them into bags of 5. How many are left over?'
    def _leftover(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        m, q, rest = self._uneven()
        total = q * m + rest
        t.put(a, thing, total)
        t.say(f"{a} has {total} {plural(thing)}.")
        if r.random() < 0.5:
            box = r.choice(["bag", "box", "jar", "basket"])
            t.put(a, box, q)
            t.put(a, thing, rest)
            t.say(f"{self._he(a).capitalize()} {r.choice(['puts', 'put', 'packs', 'packed'])} them into {plural(box)} of {m}.")
            if r.random() < 0.5:
                return t.ask(f"How many full {plural(box)} {r.choice(['are there', 'does ' + self._he(a) + ' have'])}?", q)
            return t.ask(f"How many {plural(thing)} are left over?", rest)
        who = r.choice(FRIENDS)
        t.put(a, thing, rest)
        t.put(a, singular_of(who), m)
        t.say(f"{self._he(a).capitalize()} {r.choice(['shares', 'shared'])} them equally among {m} {who}.")
        if r.random() < 0.5:
            return t.ask(f"How many {plural(thing)} does each {singular_of(who)} get?", q)
        return t.ask(f"How many {plural(thing)} are left over?", rest)

    # rounding up: '105 people are going to a movie. 6 people can ride in each car. How many cars are needed?'
    def _needed(self, t):
        r = self.r
        who, car = r.choice([("child", "van"), ("child", "bus"), ("person", "car"), ("pupil", "table"),
                             ("person", "boat"), ("child", "tent")])
        many = {"child": "children", "person": "people"}.get(who, who + "s")
        m, q, rest = self._uneven()
        total = q * m + (rest if r.random() < 0.8 else 0)
        need = q + (total % m > 0)
        t.put(None, who, total)
        t.say(r.choice([f"{total} {many} are going on a trip.", f"There are {total} {many}."]))
        t.put(car, who, m)
        t.say(r.choice([f"{m} {many} can {'sit at' if car == 'table' else 'ride in'} each {car}.",
                        f"Each {car} {r.choice(['can hold', 'holds'])} {m} {many}."]))
        return t.ask(r.choice([f"How many {plural(car)} are needed?", f"How many {plural(car)} do they need?"]), need)

    # how many can you buy: 'If one pack of gum costs $2, how many packs can you buy with $16?'
    def _afford(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        p, q = self._factor(), self._factor()
        rest = r.randint(0, p - 1) if r.random() < 0.6 else 0
        have = p * q + rest
        t.put(thing, "dollar", p)
        t.say(f"A {thing} costs {p} dollars.")
        t.put(a, "dollar", have)
        t.say(f"{a} has {have} dollars.")
        if rest and r.random() < 0.4:
            return t.ask(f"If {self._he(a)} buys as many {plural(thing)} as {self._he(a)} can, how many dollars are left?", rest)
        return t.ask(f"How many {plural(thing)} can {self._he(a)} buy?", q)

    # two steps: 'Maggi had 3 packages of cupcakes. There are 4 cupcakes in each package. She ate 5. How many are left?'
    def _twostep(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        box = r.choice(["bag", "box", "pack", "jar", "basket"])
        n, m = self._factor(), self._factor()
        t.put(a, box, n)
        t.say(f"{a} {r.choice(['has', 'had', 'bought'])} {n} {plural(box)} of {plural(thing)}.")
        t.put(a, thing, n * m)
        t.say(r.choice([f"There are {m} {plural(thing)} in each {box}.", f"Each {box} has {m} {plural(thing)}."]))
        verb = r.choice(LOSSES_P3)
        k = r.randint(1, n * m - 1)
        t.add(a, thing, -k)
        t.say(f"{self._he(a).capitalize()} {VERBS[verb][1]} {k} {plural(thing)}.")
        return t.ask(r.choice([f"How many {plural(thing)} are left?", f"How many {plural(thing)} does {a} have now?"]),
                     n * m - k)

    # P4: the last day ('Jane can arrange 16 vases a day. There are 248 vases. How many will she arrange on the last day?')
    def _lastday(self, t):
        r = self.r
        a, = self._people(1)
        verb, thing = r.choice([("read", "page"), ("make", "cake"), ("pick", "apple"), ("pack", "box"),
                                ("paint", "picture"), ("plant", "tree")])
        forms = {"read": "reads", "pack": "packs", "paint": "paints", "plant": "plants"}.get(verb) or VERBS[verb][0]
        m, q, rest = self._uneven()
        total = q * m + rest
        t.put(None, thing, total)
        t.say(f"There are {total} {plural(thing)}.")
        t.put(a, thing, m)
        t.first[(a, thing, frozenset())] = 0
        t.say(f"{a} {forms} {m} {plural(thing)} a day.")
        if r.random() < 0.5:
            return t.ask(f"How many {plural(thing)} does {self._he(a)} {verb} on the last day?", rest)
        return t.ask(f"How many days does {self._he(a)} need?", q + 1)

    # ---- P5-P6 ---------------------------------------------------------------------------------------
    # unit change: 'Cora sliced 18 kg of apples. How many grams of apples is that?'
    def _convert(self, t):
        r = self.r
        a, = self._people(1)
        u = r.choice(UNITS)
        n = r.randint(2, 9 if u["k"] >= 100 else 20)
        big, small = u["big"][1], u["small"][1]
        if u["kind"] == "mass":
            thing = r.choice(["flour", "rice", "sugar", "apples", "potatoes"])
            t.put(a, f"{u['big'][0]} of {thing.rstrip('s')}", n)
            t.say(f"{a} {r.choice(['has', 'bought', 'needs'])} {n} {big} of {thing}.")
            return t.ask(f"How many {small} of {thing} {r.choice(['is that', 'does ' + self._he(a) + ' have'])}?", n * u["k"])
        if u["kind"] == "length":
            thing = r.choice(["rope", "ribbon", "path", "fence", "road"])
            t.put(thing, u["big"][0], n)
            t.say(f"The {thing} is {n} {big} long.")
            return t.ask(f"How many {small} long is the {thing}?", n * u["k"])
        if u["kind"] == "time":
            what = r.choice(EVENTS if u["big"][0] == "hour" else ["holiday", "trip", "camp"])
            t.put(what, u["big"][0], n)
            t.say(f"The {what} lasts {n} {big}.")
            return t.ask(f"How many {small} does the {what} last?", n * u["k"])
        t.put(a, u["big"][0], n)
        t.say(f"{a} has {n} {big}.")
        return t.ask(f"How many {small} does {self._he(a)} have?", n * u["k"])

    # percentage: '20% of the 50 children are boys', 'what is 4% of 450 dollars?'
    def _percent(self, t):
        r = self.r
        p = r.choice([5, 10, 20, 25, 30, 40, 50, 60, 75])
        b = r.randint(1, 20) * (100 // __import__("math").gcd(p, 100))
        part = b * p // 100
        if r.random() < 0.5:
            who = r.choice(["ball", "apple", "car", "flower", "kite", "cup"])
            c, other = r.sample(["red", "blue", "green", "yellow"], 2)
            t.lines.append((f"There are {b} {plural(who)}.", {(None, who, frozenset()): b}, {}))
            t.put(None, who, part, c)                      # as with parts of a whole: the part and the rest
            t.put(None, who, b - part, other)
            t.lines.append((f"{p}% of the {plural(who)} are {c}.", {(None, who, frozenset([c])): part,
                                                                     (None, who, frozenset([other])): b - part}, {}))
            return t.ask(f"How many {plural(who)} are {c}?", part)
        thing = r.choice(["bag", "bike", "coat", "lamp", "game"])
        t.put(thing, "dollar", b)
        t.say(f"A {thing} costs {b} dollars.")
        return t.ask(r.choice([f"What is {p}% of {b} dollars?", f"How many dollars is {p}% of {b} dollars?"]), part)

    # area of a square: 'Each side of a square kitchen tile is 7 inches long. What is the tile's area?'
    def _square(self, t):
        r = self.r
        unit = r.choice(["cm", "m", "inches"])
        side = r.randint(2, 30)
        t.put("square", unit if unit != "inches" else "inch", side)
        t.say(f"Each side of a square is {side} {unit} long.")
        return t.ask(r.choice(["What is the area of the square?", "What is the square's area?"]), side * side)

    # greatest common factor: 'Lexi has 10 cans of soup and 15 boxes of tissue ... the greatest number of kits'
    def _common(self, t):
        r = self.r
        from math import gcd
        a, = self._people(1)
        x_thing, y_thing = r.sample(COUNTABLE, 2)
        g = r.randint(2, 12)
        x, y = g * r.randint(1, 9), g * r.randint(1, 9)
        while gcd(x, y) != g or x == y:
            x, y = g * r.randint(1, 9), g * r.randint(1, 9)
        box = r.choice(["bag", "box", "kit", "basket"])
        t.put(a, x_thing, x)
        t.put(a, y_thing, y)
        t.say(f"{a} has {x} {plural(x_thing)} and {y} {plural(y_thing)}.")
        t.say(f"{self._he(a).capitalize()} puts them into {plural(box)} with the same number of {plural(x_thing)} and "
              f"the same number of {plural(y_thing)} in each, and nothing left over.")
        return t.ask(f"What is the greatest number of {plural(box)} {self._he(a)} can make?", g)

    # least common multiple: 'It takes Henry 7 minutes and Margo 12 minutes to go round. When are both at the start?'
    def _meet(self, t):
        r = self.r
        from math import gcd
        a, b = self._people(2)
        x, y = r.sample(range(2, 16), 2)
        if r.random() < 0.5:
            t.put(a, "minute", x)
            t.say(f"{a} runs round the track in {x} minutes.")
            t.put(b, "minute", y)
            t.say(f"{b} walks round the track in {y} minutes.")
            t.say("They start together.")
            return t.ask("After how many minutes are they both at the start again?", x * y // gcd(x, y))
        t.put(a, "day", x)
        t.say(f"{a} visits the library every {x} days.")
        t.put(b, "day", y)
        t.say(f"{b} visits the library every {y} days.")
        t.say("Today they are both there.")
        return t.ask("In how many days are they both there again?", x * y // gcd(x, y))

    # speed: 'A car goes 60 km in an hour. How far does it go in 3 hours?'
    def _speed(self, t):
        r = self.r
        car = r.choice(["car", "train", "bus", "bike", "boat"])
        v, h = r.randint(2, 90), r.randint(2, 9)
        if r.random() < 0.5:
            t.put(car, "km", v)
            t.say(f"A {car} goes {v} km in an hour.")
            return t.ask(f"How many km does it go in {h} hours?", v * h)
        t.put(car, "km", v * h)
        t.put(car, "hour", h)
        t.say(f"A {car} goes {v * h} km in {h} hours.")
        return t.ask("How many km does it go in one hour?", v)

    # ---- S1 (secondary 1) ---------------------------------------------------------------------------
    # negative numbers: 'The temperature is 4 degrees. It falls by 9 degrees. What is the temperature now?'
    def _negative(self, t):
        r = self.r
        place = r.choice(["town", "city", "garden", "village"])
        a, d = r.randint(1, 15), r.randint(2, 20)
        below = r.random() < 0.4                          # it starts below zero and rises, or falls below zero
        start = -a if below else a
        end = start + d if below else start - d
        key = ("temperature", "degree", frozenset())       # 'the temperature is 7 degrees': as it is perceived
        t.lines.append((f"In the {place} the temperature is {a} degrees{' below zero' if below else ''}.",
                        {key: start}, {key: start}))
        t.truth, t.first = {key: end}, {key: start}
        t.say(f"The temperature {'rises' if below else 'falls'} by {d} degrees.")
        return t.ask("What is the temperature now?", end)

    # simple equations: 'Tom thinks of a number. He adds 7 to it. He gets 15. What number did he think of?'
    def _equation(self, t):
        r = self.r
        a, = self._people(1)
        x = r.randint(2, 20)
        how = r.choice(["add", "take", "times"])
        k = r.randint(2, 9)
        end = x + k if how == "add" else (x - k if how == "take" and x > k else x * k)
        if how == "take" and x <= k:
            how, end = "add", x + k
        t.put(a, "number", x)
        t.say(f"{a} thinks of a number.")
        t.put(a, "number", end)
        t.first[(a, "number", frozenset())] = x
        t.say({"add": f"{self._he(a).capitalize()} adds {k} to it.", "take": f"{self._he(a).capitalize()} subtracts {k} from it.",
               "times": f"{self._he(a).capitalize()} multiplies it by {k}."}[how])
        t.say(f"The answer is {end}.")                    # not 'she gets 9': 'gets' means 'gets more' everywhere else
        return t.ask(f"What number did {self._he(a)} think of?", x)

    # proportion, the unitary method: '5 pens cost 15 dollars. How much do 8 pens cost?'
    def _proportion(self, t):
        r = self.r
        thing = r.choice(COUNTABLE)
        one, n, m = r.randint(2, 12), r.randint(2, 9), r.randint(2, 12)
        while m == n:
            m = r.randint(2, 12)
        if r.random() < 0.6:
            t.put(None, thing, n)
            t.put(None, "dollar", one * n)
            t.say(f"{n} {plural(thing)} cost {one * n} dollars.")
            return t.ask(f"How much do {m} {plural(thing)} cost?", one * m)
        a, = self._people(1)
        t.put(a, thing, one * n)
        t.put(a, "hour", n)
        t.say(f"{a} makes {one * n} {plural(thing)} in {n} hours.")
        return t.ask(f"How many {plural(thing)} does {self._he(a)} make in {m} hours?", one * m)

    # the average of two: 'Ana scored 70 in the first test and 90 in the second. What is her average score?'
    def _average(self, t):
        r = self.r
        a, = self._people(1)
        d1, d2 = r.sample(DAYS[:5], 2)
        x = r.randint(20, 99)
        y = x + 2 * r.randint(-9, 9)
        if not 1 <= y <= 100:
            y = x
        t.put(a, "point", x, d1)
        t.say(f"{a} scored {x} points on {d1}.")
        t.put(a, "point", y, d2)
        t.say(f"{self._he(a).capitalize()} scored {y} points on {d2}.")
        return t.ask(f"What is {self._he(a, 'pos')} average score?", (x + y) // 2)

    # circles: 'A round table has a diameter of 10 feet. What is its radius?'
    def _circle(self, t):
        r = self.r
        thing = r.choice(["table", "plate", "pond", "wheel", "clock"])
        d = 2 * r.randint(2, 30)
        t.put(thing, "cm", d)
        if r.random() < 0.5:
            t.say(f"A round {thing} is {d} cm across.")
            return t.ask(f"What is the radius of the {thing} in cm?", d // 2)
        t.lines.append((f"The radius of a round {thing} is {d // 2} cm.", {(thing, "cm", frozenset()): d // 2}, {}))
        t.truth = {(thing, "cm", frozenset()): d // 2}
        return t.ask(f"How many cm across is the {thing}?", d)

    # ---- S2 (secondary 2) ---------------------------------------------------------------------------
    # ratios, with the unitary method: 'A recipe uses 2 eggs for 6 pancakes. How many eggs for 15 pancakes?'
    def _ratio(self, t):
        r = self.r
        thing = r.choice(COUNTABLE)
        unit = r.choice(["eggs", "spoons", "coins", "stamps", "pencils"])
        per, made = r.randint(2, 6), r.choice([2, 3, 4, 5, 6, 8, 10, 12])
        want = r.choice([n for n in range(2, 13) if (per * n) % made == 0])
        t.put(None, unit, per * made)
        t.say(f"{per} {unit} make {made} {plural(thing)}.")
        return t.ask(f"How many {unit} do you need for {want} {plural(thing)}?", per * want // made)

    # simple interest, by the percent tool: 'You put 200 dollars in a bank. It earns 5 percent a year.'
    def _interest(self, t):
        r = self.r
        money, rate = self._big(50, 500), r.randint(2, 12)
        years = r.randint(1, 3)
        t.put(None, "dollar", money)
        t.say(f"You put {money} dollars in a bank. It earns {rate} percent a year.")
        return t.ask(f"How much do you have after {years} year{'s' if years > 1 else ''}?",
                     money + money * rate * years // 100)

    # volume of a box, three numbers multiplied: 'A box is 3 cm long, 4 cm wide and 2 cm high.'
    def _volume(self, t):
        r = self.r
        box = r.choice(["box", "case", "crate", "brick"])
        l, w, h = r.randint(2, 12), r.randint(2, 12), r.randint(2, 12)
        key = lambda what: (box, what, frozenset())
        t.put(None, box, l, "length")
        t.put(None, box, w, "width")
        t.put(None, box, h, "height")
        t.say(f"A {box} is {l} cm long, {w} cm wide and {h} cm high.")
        return t.ask(f"How many cubic cm are inside the {box}?", l * w * h)

    # three steps: 'A shop has 12 boxes with 8 pens in each. Ana buys 5 boxes and gives 3 pens away.'
    def _threestep(self, t):
        r = self.r
        a, = self._people(1)
        box, thing = r.choice(["box", "crate", "bag", "basket"]), r.choice(LONG)
        each, want, give = r.randint(3, 12), r.randint(2, 8), r.randint(1, 9)
        t.put(None, box, each)
        t.put(None, thing, each * want)
        t.say(f"There are {want} {plural(box)} with {each} {plural(thing)} in each {box}.")
        t.put(a, thing, each * want)
        t.say(f"{a} takes {want} {plural(box)} and gives away {give} {plural(thing)}.")
        return t.ask(f"How many {plural(thing)} does {a} have now?", each * want - give)

    # number bonds: a whole and its parts ('22 are red and the rest are green')
    def _parts(self, t):
        r = self.r
        thing = r.choice(COUNTABLE)
        c1, c2 = r.sample(["red", "green", "blue", "yellow", "pink", "white"], 2)
        n = self._big(3, 40)
        k = r.randint(1, n - 1)
        t.put(None, thing, k, c1)
        t.put(None, thing, n - k, c2)
        t.lines.append((f"There are {n} {plural(thing)} in the box.", {(None, thing, frozenset()): n}, {}))
        t.say(f"{k} are {c1} and the rest are {c2}.")
        return t.ask(f"How many {plural(thing)} are {c2}?", n - k)

    # 'what is the difference between ...'
    def _difference(self, t):
        r = self.r
        a, b = self._people(2)
        thing = r.choice(COUNTABLE)
        na, nb = r.sample(range(2, 40), 2)
        t.put(a, thing, na)
        t.say(f"{a} has {na} {plural(thing)}.")
        t.put(b, thing, nb)
        t.say(f"{b} has {nb} {plural(thing)}.")
        return t.ask(r.choice([f"What is the difference between the number of {plural(thing)} {a} has and {b} has?",
                               f"What is the difference between {a}'s {plural(thing)} and {b}'s {plural(thing)}?"]),
                     abs(na - nb))

    # P2: fractions of a whole
    def _fraction(self, t):
        r = self.r
        a, = self._people(1)
        whole = r.choice(WHOLES)
        n = r.randint(2, 12)
        k = r.randint(1, n - 1)
        t.put(whole, "piece", n)
        t.say(f"A {whole} is cut into {n} equal pieces.")
        t.put(a, "piece", k)
        verb = r.choice(["takes", "gets", "took", "got"])
        t.say(f"{a} {verb} {k} pieces.")
        base = {"takes": "take", "gets": "get", "took": "take", "got": "get"}[verb]
        return t.ask(f"What fraction of the {whole} did {a} {base}?", _frac(k, n))

    # P2: times tables with prices
    def _price(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        p, n = r.randint(2, 10), r.randint(2, 10)
        if r.random() < 0.5:
            t.put(thing, "dollar", p)
            t.say(f"A {thing} costs {p} dollars.")
            return t.ask(f"How much do {n} {plural(thing)} cost?", p * n)
        t.put(a, thing, n)
        t.say(f"{a} {r.choice(['buys', 'bought'])} {n} {plural(thing)}.")
        t.put(a, "dollar", p * n)
        t.say(f"Each {thing} costs {p} dollars.")
        return t.ask(f"How much does {self._he(a)} pay?", p * n)

    # P2: paying and getting change
    def _pay(self, t):
        r = self.r
        a, = self._people(1)
        thing = r.choice(COUNTABLE)
        p = r.randint(2, 18)
        q = r.choice([10, 20, 50]) if p < 10 else r.choice([20, 50])
        t.put(thing, "dollar", p)
        t.say(f"A {thing} costs {p} dollars.")
        t.put(a, "dollar", q - p)
        t.first[(a, "dollar", frozenset())] = q
        t.say(f"{a} {r.choice(['pays', 'paid'])} with {q} dollars.")
        return t.ask(f"How much change does {self._he(a)} get?", q - p)


LOSSES_P3 = ["eat", "sell", "lose", "use", "give away"]
# unit facts the teacher tells in P5 (word in the scene, word in the story)
UNITS = [{"big": ("kg", "kg"), "small": ("g", "grams"), "k": 1000, "kind": "mass"},
         {"big": ("km", "km"), "small": ("m", "metres"), "k": 1000, "kind": "length"},
         {"big": ("m", "metres"), "small": ("cm", "cm"), "k": 100, "kind": "length"},
         {"big": ("hour", "hours"), "small": ("minute", "minutes"), "k": 60, "kind": "time"},
         {"big": ("week", "weeks"), "small": ("day", "days"), "k": 7, "kind": "time"},
         {"big": ("dollar", "dollars"), "small": ("cent", "cents"), "k": 100, "kind": "money"}]


def singular_of(w):
    return {"children": "child", "friends": "friend", "pupils": "pupil"}.get(w, w)


def _frac(k, n):
    from fractions import Fraction
    return Fraction(k, n)


# ---- the levels -----------------------------------------------------------------------------------------
LEVELS = {
    "P1": {"about": "numbers to 100 (number words); adding and taking away within 100; comparing (also told out of "
                    "order); equal groups and sharing; money in cents; o'clock; length in cm; how many more are "
                    "needed; a day / per day; taken out, removed, got off",
           "count_to": 100, "counting": 3000, "stories": 4000, "kinds": SchoolTeller.P1, "top": 100, "asdiv": 1},
    "P2": {"about": "numbers to 1000; everything in P1 with bigger numbers; times tables and prices; fractions of a "
                    "whole; dollars and change; mass and volume; two steps",
           "count_to": 1000, "counting": 2000, "stories": 4000, "kinds": SchoolTeller.P2, "top": 1000, "asdiv": 2},
    "P3": {"about": "numbers to 10 000; times tables 6, 7, 8, 9; division with a remainder (left over, full groups, "
                    "how many are needed, how many you can buy); two steps",
           "count_to": 10000, "counting": 1000, "stories": 4000, "kinds": SchoolTeller.P3, "top": 10000, "asdiv": 3},
    "P4": {"about": "numbers to 100 000; multiplying and dividing by 2-digit numbers; remainders in bigger stories "
                    "(the last day)",
           "count_to": 100000, "counting": 1000, "stories": 4000, "kinds": SchoolTeller.P4, "top": 100000, "asdiv": 4},
    "P5": {"about": "numbers to 10 million; units (kg and g, km and m, m and cm, hours and minutes, weeks and days, "
                    "dollars and cents); percentage; the area of a square",
           "count_to": 1000000, "counting": 500, "stories": 4000, "kinds": SchoolTeller.P5, "top": 1000000, "asdiv": 5},
    "P6": {"about": "greatest common factor and least common multiple; speed, distance and time",
           "count_to": 10000000, "counting": 500, "stories": 4000, "kinds": SchoolTeller.P6, "top": 10000000, "asdiv": 6},
    "S1": {"about": "secondary 1: negative numbers; simple equations; proportion (the unitary method); averages; circles",
           "count_to": 10000000, "counting": 500, "stories": 4000, "kinds": SchoolTeller.S1, "top": 10000000,
           "asdiv": "gsm8k"},
    "S2": {"about": "secondary 2: ratios; simple interest; volume; problems with three steps",
           "count_to": 100000000, "counting": 500, "stories": 4000, "kinds": SchoolTeller.S2, "top": 100000000,
           "asdiv": "gsm8k"},
}
EXAM_PER_KIND = 20


def exam_tales(level, which, round_no=0, per_kind=EXAM_PER_KIND):
    """Stories it never heard, with their scenes: exams A and B (school rounds) and C (exams asked for in the chat) use
    their own seeds, new to the lessons and new every round."""
    lv = LEVELS[level]
    teller = SchoolTeller(seed={"A": 7001, "B": 7002, "C": 7003}[which] + 10 * list(LEVELS).index(level) + 1000 * round_no,
                          kinds=lv["kinds"], top=lv["top"])
    return [(kind, t) for kind in lv["kinds"] for t in (teller.tale(kind) for _ in range(per_kind))]


def exam_items(level, which, round_no=0):
    return [(kind, t.text(), t.answer) for kind, t in exam_tales(level, which, round_no)]


# ---- the teacher explains a story from its scenes ----------------------------------------------------------
_UNIT_WORDS = {"cm", "kg", "km", "m", "g", "inch", "dollar", "cent", "minute", "hour", "day", "week"}


def _who(owner, thing, desc):
    head = thing.split(" of ")[0]
    if head in _UNIT_WORDS or " of " in thing:          # 'kg of rice', 'ribbon's m': units are not counted things
        name = thing if head not in ("inch", "dollar", "cent", "minute", "hour", "day", "week") else plural(head) + thing[len(head):]
    else:
        name = plural(thing)
    what = " ".join(sorted(desc) + [name])
    return f"{owner}'s {what}" if owner else f"the {what} there"


_SAY_OP = {"+": " + ", "-": " \u2212 ", "*": " \u00d7 ", "/": " \u00f7 ", "~": " and ",
           "%": " left over after groups of ", "&": " in full groups of ", "^": " in groups needed of "}


KIND_RULE = {"common": "#", "meet": "$", "square": "*", "leftover": "%&", "needed": "^", "afford": "&%", "lastday": "%^",
             "proportion": "("}


def _plainest(atoms, names, value, prefer=(), compare=True, rule=None):
    """The plainest explanation of value over the atoms, in words; prefer uses the atoms the question talks about."""
    from fractions import Fraction
    from .storyreader import expressions, uses
    ways = expressions(atoms, "%&^#$!qu").get(Fraction(value), [])
    if not ways:
        return None
    if rule and any(any(o in e for o in rule) for e in ways):    # the teacher knows which rule the story practises
        ways = [e for e in ways if any(o in e for o in rule)]
    cost = {"+": 0, "-": 0, "~": 0, "*": 1, "/": 1, "%": 2, "&": 2, "^": 2, "#": 2, "$": 2, "!": 2}

    def score(e):                       # what the question names counts; other numbers and multiplying need a reason
        used = uses(e)
        ops = [c for c in e if c in cost] + (["*"] if re.search(r"[*/]2", e) else [])
        return (-(sum(a in prefer for a in used) - sum(a not in prefer for a in used) - sum(cost[o] for o in ops)),
                len(used), len(e))
    single = [e for e in ways if e in prefer]
    if single and not compare:                         # it asks for exactly something the story shows
        e = single[0]
    else:
        e = sorted(ways, key=score)[0]
    u = re.match(r"^\(([A-Z]\w*)/([A-Z]\w*)\)\*([A-Z]\w*)$", e)
    if u:
        return f"{names[u[1]]} \u00f7 {names[u[2]]} for one, times {names[u[3]]}"
    term = r"([A-Z]\w*)(?:([*/])2)?"
    m = re.match(rf"^{term}(?:([-+*/~%&^#$!]){term})?$", e)
    if not m:
        return None

    def name(atom, half):
        return names[atom] if not half else (f"twice {names[atom]}" if half == "*" else f"half of {names[atom]}")
    a = name(m[1], m[2])
    if not m[3]:
        return a
    b = name(m[4], m[5])
    if m[3] == "~":
        return f"the difference between {a} and {b} (bigger minus smaller)"
    if m[3] == "*" and m[1] == m[4]:
        return f"{a} \u00d7 {a} (side \u00d7 side)"
    if m[3] in "#$!":
        return {"#": f"the greatest common factor of {a} and {b}", "$": f"the least common multiple of {a} and {b}",
                "!": f"{a}% of {b}"}[m[3]]
    return f"{a}{_SAY_OP[m[3]]}{b}"


def explain(tale):
    """The teacher's walk-through: what every sentence does (from the scene after it) and the sum that gives it, then
    why the answer is that."""
    from fractions import Fraction
    from .storyreader import Lin, fmt
    out, before = [], {}
    for li, (sentence, truth, firsts) in enumerate(tale.lines):
        later = " ".join(x[0] for x in tale.lines[li + 1:])
        nums = {f"N{j}": Lin(Fraction(n)) for j, n in enumerate(re.findall(r"\d+(?:\.\d+)?", sentence))}
        names = {k: fmt(v.c) for k, v in nums.items()}
        known = {**before, **{k: v for k, v in truth.items() if k not in before}}   # incl. what it says of others
        did = []
        for k, v in truth.items():
            old = before.get(k)
            if old == v:
                continue
            v = Fraction(v)
            atoms = dict(nums)
            for i, (k2, v2) in enumerate(known.items()):
                if k2 != k:
                    atoms[f"B{i}"], names[f"B{i}"] = Lin(Fraction(v2)), f"{_who(*k2)} ({fmt(Fraction(v2))})"
            how = None
            if all(n.c != v for n in nums.values()):            # not just said: a sum gives it
                if re.search(rf"\b{re.escape(fmt(v))}\b", later):
                    how = "the story says so in a later sentence"
                else:
                    how = _plainest(atoms, names, v, prefer=set(nums))
            if old is None:
                start = Fraction(firsts.get(k, v))
                if start != v and not how:               # 'bought 8 ... had 5 at the start': 13 = 5 + 8
                    atoms["S"], names["S"] = Lin(start), f"the start ({fmt(start)}, told later)"
                    how = _plainest(atoms, names, v, prefer=set(nums) | {"S"})
                if not nums and "some" in sentence.lower():
                    did.append(f"{_who(*k)}: some (the story tells us later: {fmt(v)})")
                    continue
                did.append(f"{_who(*k)}: {fmt(v)}" + (f" = {how}" if how else "") +
                           (f" (at the start {fmt(start)})" if start != v else ""))
            else:
                d = v - Fraction(old)
                did.append(f"{_who(*k)}: {fmt(Fraction(old))} \u2192 {fmt(v)} "
                           f"({fmt(Fraction(old))} {'+' if d > 0 else '\u2212'} {fmt(abs(d))})")
        out.append(f"\u2022 \"{sentence}\" \u2192 " + ("; ".join(did) if did else "nothing new: it says what we know"))
        before = dict(truth)
    end = tale.lines[-1][1] if tale.lines else {}
    firsts = tale.lines[-1][2] if tale.lines else {}
    q = tale.question.lower()
    atoms, names, prefer = {}, {}, set()
    people = {k[0] for k in end if k[0] and k[0] in PEOPLE}
    asked = {p for p in people if re.search(rf"\b{p.lower()}\b", q)}
    for i, (k, v) in enumerate(end.items()):
        atoms[f"A{i}"], names[f"A{i}"] = Lin(Fraction(v)), f"{_who(*k)} ({fmt(Fraction(v))})"
        thing = plural(k[1]) in q or re.search(rf"\b{re.escape(k[1])}\b", q)
        named = (k[0] in asked) if asked and k[0] in people else bool(thing)   # 'does Sam have': Sam's, not Mia's
        if named:
            prefer.add(f"A{i}")
        if firsts.get(k, v) != v:
            atoms[f"F{i}"], names[f"F{i}"] = Lin(Fraction(firsts[k])), f"{_who(*k)} at the start ({fmt(Fraction(firsts[k]))})"
            if named and re.search(r"at first|start|beginning|initially|did .* (buy|find|get|eat|sell|lose|use)", q):
                prefer.add(f"F{i}")
    for j, n in enumerate(re.findall(r"\d+(?:\.\d+)?", tale.question)):
        atoms[f"Q{j}"], names[f"Q{j}"] = Lin(Fraction(n)), n
        prefer.add(f"Q{j}")
    for u in UNITS:                                       # the unit fact the question needs ('1 kg is 1000 g')
        if re.search(rf"\b{u['small'][1]}\b", q) and any(u["big"][0] == k[1].split(" of ")[0] for k in end):
            atoms["U"], names["U"] = Lin(Fraction(u["k"])), f"{u['k']} (1 {u['big'][0]} is {u['k']} {u['small'][1]})"
            prefer.add("U")
    compare = bool(re.search(r"\b(difference|more|fewer|less|than|together|altogether|in all|total|both|left|"
                             r"did .* (buy|find|get|eat|sell|lose|use|pick|collect|win|give|take))\b", q))
    said = _plainest(atoms, names, tale.answer, prefer, compare, KIND_RULE.get(getattr(tale, "kind", None)))
    return out + [f"So the question \"{tale.question}\" asks for " + (f"{said} = {fmt(Fraction(tale.answer))}."
                                                                        if said else f"{fmt(Fraction(tale.answer))}.")]


EXPLAINED = 1              # the explained story is lived through once more, with its scenes
CHECK = 10000              # stories it got right on the exam that a new lesson must not break (all of them)


def review_exam(kg, level, which="C", round_no=None, per_kind=EXAM_PER_KIND):
    """An exam asked for in the chat, then the teacher goes over every mistake: how it read the story, the right answer,
    WHY (the teacher's walk-through of the scenes), what it learned, and whether it now reads it right."""
    if round_no is None:
        round_no = kg.lessons.get(f"exams_{level}", 0)
        kg.lessons[f"exams_{level}"] = round_no + 1
    from fractions import Fraction
    from .storyreader import learn_tale
    tales = exam_tales(level, which, round_no, per_kind)
    exam = take_exam(kg, [(k, t.text(), t.answer) for k, t in tales])
    kg.frames.situation = level
    reviewed = []
    right = [(r["question"], r["expected"]) for r in exam["rows"] if r["ok"]]
    check = random.Random(round_no).sample(right, min(CHECK, len(right)))
    for (kind, tale), row in zip(tales, exam["rows"]):
        if row["ok"]:
            continue
        _, how, trace = kg.reader().solve(row["question"])
        read = [f"{t['clause']} \u2192 {'; '.join(t['did']) if t['did'] else '?'}" for t in trace]
        keep = copy.deepcopy(kg.state())                   # what it knew before this lesson
        res = kg.learn_story(row["question"], row["expected"], taught_words=False)     # the right answer
        for _ in range(EXPLAINED):                         # and the explanation: what each sentence does (its scenes)
            learn_tale(tale, kg.lexicon(), kg.frames)
        kg._lex = None
        reader = kg.reader()
        broke = [q for q, a in check if str(reader.solve(q)[0]) != a and reader.solve(q)[0] != Fraction(a)]
        if broke:                                          # it checks the lesson against what it knew: it broke something
            kept_situation = kg.frames.situation
            kg.__init__(keep)
            kg.frames.situation = kept_situation
            res = {**res, "lesson": f"dropped: it broke {len(broke)} stories it had right (e.g. {broke[0][:60]}...)"}
        else:
            kg.remember(level, tale)
        got, how2, _ = kg.reader().solve(row["question"])
        reviewed.append({"topic": kind, "story": row["question"], "said": row["got"], "right": row["expected"],
                         "it_read": read, "why": explain(tale), "learned": res.get("lesson"),
                         "now": None if got is None else str(got), "now_right": got == tale.answer})
    by = {}
    for r in exam["rows"]:
        b = by.setdefault(r["topic"], [0, 0])
        b[0] += r["ok"]
        b[1] += 1
    return {"level": level, "exam_set": round_no + 1, "score": round(exam["score"], 3), "grade": al(exam["score"]),
            "predicted": round(exam["predicted"], 3), "n": len(exam["rows"]), "by_topic": by, "reviewed": reviewed,
            "fixed": sum(r["now_right"] for r in reviewed)}


def take_exam(kg, items):
    """Read only (on a copy): how many it gets right, and how many it SAYS it understood (its prediction)."""
    pupil = copy.deepcopy(kg)
    reader = pupil.reader()
    rows = []
    for kind, text, answer in items:
        got, how, _ = reader.solve(text)
        rows.append({"topic": kind, "question": text, "expected": str(answer), "got": None if got is None else str(got),
                     "ok": got is not None and got == answer, "sure": how == "understood every sentence", "how": how})
    n = len(rows)
    return {"score": sum(r["ok"] for r in rows) / n, "predicted": sum(r["sure"] for r in rows) / n, "rows": rows}


def load_outside(grade):
    """ASDiv by grade (1-6); from secondary 1 on, GSM8K test (harder multi-step grade-school problems)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))
    if grade == "gsm8k":
        from fractions import Fraction
        rows = []
        for i, line in enumerate((Path(__file__).resolve().parent.parent / "benchmarks" / "gsm8k_test.jsonl")
                                 .read_text(encoding="utf-8").splitlines()):
            x = json.loads(line)
            rows.append({"id": f"gsm8k-{i}", "text": x["question"],
                         "answer": Fraction(x["answer"].split("####")[-1].strip().replace(",", ""))})
        return rows
    from asdiv import load_asdiv
    return load_asdiv(grade)


def outside_exam(kg, grade, split="test"):
    """The outside exam: even problems are the dev half (looked at while improving), odd ones the test."""
    rows = [x for i, x in enumerate(load_outside(grade)) if (i % 2 == 1) == (split == "test")]
    reader = kg.reader()
    out = []
    for x in rows:
        got, how, trace = reader.solve(x["text"])
        sure = got is not None and how == "understood every sentence"
        out.append({"id": x["id"], "text": x["text"], "answer": str(x["answer"]), "got": None if got is None else str(got),
                    "understood": sure, "right": sure and got == x["answer"], "guess_right": got == x["answer"],
                    "how": how, "trace": trace})
    n = len(out)
    return {"grade": grade, "split": split, "n": n, "understood": sum(r["understood"] for r in out),
            "right": sum(r["right"] for r in out), "guess_right": sum(r["guess_right"] for r in out), "rows": out}


# ---- real stories: word problems people wrote (MAWPS), no scenes, the teacher only gives the answer ---------
REAL = {"P1": {"lessons": 200, "ops": "+-", "steps": 1, "top": 100},
        "P2": {"lessons": 300, "ops": "+-*/", "steps": 2, "top": 1000},
        "P3": {"lessons": 600, "ops": "+-*/", "steps": 2, "top": 10000},      # about the whole clean pool once
        "P4": {"lessons": 600, "ops": "+-*/", "steps": 3, "top": 100000},
        "P5": {"lessons": 600, "ops": "+-*/", "steps": 3, "top": 10000000},
        "P6": {"lessons": 600, "ops": "+-*/", "steps": 3, "top": 10000000},
        "S1": {"lessons": 600, "ops": "+-*/", "steps": 3, "top": 10000000},
        "S2": {"lessons": 600, "ops": "+-*/", "steps": 4, "top": 100000000}}
REAL_EXAM = 60
REAL_WEIGHT = 3           # the teacher told the answer (as in the chat); 1 was tried: within noise


_LIBRARY = {}
LIBRARY_SOURCES = ("svamp_train",)            # MAWPS; adding gsm8k_train made grades 1-2 worse (2026-10-02)


def real_stories(level):
    """Word problems people wrote, at this level, from the clean library (benchmarks/library.py): MAWPS (svamp_train)
    and GSM8K train, with every problem that is the same as or a NEAR-COPY of an ASDiv (any grade) or SVAMP problem
    left out (half of the words the same, numbers masked), so the outside exams stay unseen. -> (lessons, exam)."""
    import re
    from fractions import Fraction
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))
    if "all" not in _LIBRARY:
        import library                        # GSM8K is in the library but not taught: it is too hard to learn
        _LIBRARY["all"] = [x for x in library.load()[0] if x["source"] in LIBRARY_SOURCES]   # from (6% right first)
    cfg = REAL[level]
    out = []
    for x in _LIBRARY["all"]:
        nums = [Fraction(n.replace(",", "")) for n in re.findall(r"\d+(?:[.,]\d+)*", x["text"])]
        if not nums or max(nums) > cfg["top"] or x["answer"].denominator != 1 or x["steps"] > cfg["steps"]:
            continue
        if any(c not in cfg["ops"] for c in x.get("ops", "")):
            continue
        out.append((x["text"], x["answer"]))
    random.Random(11).shuffle(out)
    return out[REAL_EXAM:], out[:REAL_EXAM]


def real_lessons(kg, level, n):
    """It reads each real story first, then the teacher says the answer, and it looks for what it misread."""
    pool, _ = real_stories(level)
    start = kg.lessons.get(f"real_{level}", 0)
    kg.frames.situation = f"real {level}"
    tried = right = learned = 0
    read = []
    for i in range(n):
        text, answer = pool[(start + i) % len(pool)]
        got, how, trace = kg.reader().solve(text)
        if kg.unknown_words(trace):
            read.append(text)
        tried += 1
        right += got == answer
        r = kg.learn_story(text, answer, weight=REAL_WEIGHT, taught_words=False)   # at school it lists them instead   # a guess about what it misread: counts like one story
        kg.remember(f"real {level}", real=(text, answer))
        learned += bool(r.get("lesson") and r["lesson"] != "what it did was right")
        kg._lex = None
    kg.lessons[f"real_{level}"] = start + n
    ask = [e["word"] for e in kg.words_to_teach(read)["ask"]]
    return {"real stories": n, "right first time": right, "learned from": learned, "pool": len(pool),
            "words to ask": ask}


def words_to_learn(kg, top=20):
    """The words worth teaching, from every real story it has read at school so far (read only; words taught
    since then drop out). Real stories never include ASDiv or SVAMP problems, so teaching these can't leak a test."""
    stories = []
    for level in LEVELS:
        n = kg.lessons.get(f"real_{level}", 0)
        if n:
            pool, _ = real_stories(level)
            stories += [pool[i % len(pool)][0] for i in range(n)]
    out = kg.words_to_teach(stories, top=top)
    out["stories"] = len(stories)
    return out


def real_exam(kg, level):
    """Real stories kept apart from the lessons (read only)."""
    _, exam = real_stories(level)
    reader = copy.deepcopy(kg).reader()
    und = right = guess = 0
    for text, answer in exam:
        got, how, _ = reader.solve(text)
        sure = got is not None and how == "understood every sentence"
        und += sure
        right += sure and got == answer
        guess += got == answer
    return {"n": len(exam), "understood": und, "right": right, "guess_right": guess}


def feedback(exam):
    topics = {}
    for r in exam["rows"]:
        t = topics.setdefault(r["topic"], [0, 0])
        t[0] += r["ok"]
        t[1] += 1
    return {"strengths": [t for t, (ok, n) in topics.items() if ok == n],
            "work_on": [f"{t} ({ok}/{n})" for t, (ok, n) in topics.items() if ok < n],
            "weak": [t for t, (ok, n) in topics.items() if ok < n],
            "mistakes": [f"{r['question']} -> {r['got']} (right: {r['expected']}; {r['how']})"
                         for r in exam["rows"] if not r["ok"]]}


def lessons(kg, level, log, kinds=None, stories=None):
    """Counting lessons (number words), then stories with scenes. -> how many stories were right before learning."""
    from .storyreader import Lexicon, learn_tale
    lv = LEVELS[level]
    r = random.Random(5000 + kg.lessons.get("school_stories", 0))
    if kinds is None:
        for _ in range(lv["counting"]):
            kg.words.observe(*counting_scene(r, lv["count_to"]), context="counting")
        kg.lessons["scenes"] += lv["counting"]
        kg._lex = None
    teller = SchoolTeller(seed=6000 + kg.lessons.get("school_stories", 0), kinds=kinds or lv["kinds"], top=lv["top"])
    lex = kg.lexicon()
    kg.frames.situation = level
    k = stories or lv["stories"]
    tried = right_first = 0
    for i in range(k):
        tale = teller.tale()
        if i % 10 == 0:                                   # now and then it tries first, before it sees the scenes
            tried += 1
            right_first += kg.reader().solve(tale.text())[0] == tale.answer
        learn_tale(tale, lex, kg.frames)
        kg.remember(level, tale)
        if i % 500 == 499:
            kg._lex = lex = Lexicon(kg.words, kg.frames)
    kg.lessons["stories"] += k
    kg.lessons["school_stories"] = kg.lessons.get("school_stories", 0) + k
    kg._lex = None
    return {"stories": k, "tried": tried, "right first time": right_first}


def remediate(kg, exam, log, level=None):
    """The teacher shows the answer of every exam story it got wrong; it looks for the sentence it misread."""
    fixed = 0
    kg.frames.situation = level or kg.frames.situation
    for r in exam["rows"]:
        if not r["ok"]:
            res = kg.learn_story(r["question"], r["expected"], taught_words=False)
            fixed += bool(res.get("lesson") and res["lesson"] != "what it did was right")
    return fixed


SLEEP = 1000           # stories replayed in each night's sleep (an equal share from every stage)


# ---- rules and the process, taught before the stories that need them ---------------------------------------
RULES = {
    "P5": [{"fact": u} for u in UNITS] + [
        {"op": "!", "phrase": "percent of", "said": "A percent is a part of every hundred: a% of b is b \u00f7 100, "
                                                     "times a.", "examples": [((20, 50), 10), ((4, 450), 18), ((25, 80), 20), ((50, 36), 18)]},
        {"op": "q", "phrase": "area of a square", "said": "The area of a square is its side times its side.",
         "examples": [((7,), 49), ((3,), 9), ((12,), 144), ((5,), 25)]}],
    "P6": [
        {"op": "#", "phrase": "greatest common factor", "said": "The greatest common factor of two numbers is the biggest "
         "number that goes into both with nothing left over.", "examples": [((10, 15), 5), ((42, 63), 21), ((12, 18), 6), ((8, 20), 4)]},
        {"op": "$", "phrase": "least common multiple", "said": "The least common multiple of two numbers is the smallest "
         "number they both go into.", "examples": [((7, 12), 84), ((4, 6), 12), ((3, 5), 15), ((6, 8), 24)]}],
    "S1": [
        {"op": "u", "phrase": "unitary method", "said": "To find many from some, first find one: divide, then multiply.",
         "examples": [((15, 5, 8), 24), ((12, 3, 7), 28), ((40, 8, 3), 15), ((21, 7, 10), 30)]}],
    "P3": [("full groups", "To put things into groups of the same size, count up in that size until the next group "
                           "would be too many: those are the full groups.", "&"),
           ("left over", "What is left over is the whole minus the full groups: it is always less than one group.", "%"),
           ("groups needed", "To fit everything, you need the full groups, and one more group if anything is left over.",
            "^")],
}


def rules_lesson(kg, level, log):
    """The teacher says each rule and works examples out step by step; the brain checks every example with its own
    process and keeps the rule only if it finds the teacher's number in the same place every time."""
    from .coordination import group_steps
    taught = []
    for lv in list(LEVELS)[:list(LEVELS).index(level) + 1]:
        for rule in RULES.get(lv, []):
            if isinstance(rule, dict):
                if "fact" in rule:
                    u = rule["fact"]
                    fact = {"big": [u["big"][0], u["big"][1]], "small": [u["small"][0], u["small"][1]], "k": u["k"],
                            "said": f"1 {u['big'][0]} is {u['k']} {u['small'][1]}"}
                    if any(x["said"] == fact["said"] for x in kg.frames.units):
                        continue
                    kg.learn_fact(fact)
                    log(f"  fact: {fact['said']} (e.g. 3 {u['big'][1]} = 3 \u00d7 {u['k']} = {3 * u['k']} {u['small'][1]})")
                    taught.append({"rule": fact["said"], "said": fact["said"], "learned": True})
                    continue
                if rule["op"] in kg.frames.rules:
                    continue
                kept, mine = kg.learn_op(rule["op"], rule["said"], rule["phrase"], rule["examples"])
                for (args, told), work in zip(rule["examples"], mine):
                    log(f"    teacher: {rule['phrase']} of {', '.join(map(str, args))} = {told}; its own working: {work}")
                log(f"  rule '{rule['phrase']}': {rule['said']} -> "
                    f"{'learned: its own working gives the teacher' + chr(39) + 's answer every time' if kept else 'not learned'}")
                taught.append({"rule": rule["phrase"], "said": rule["said"], "learned": kept})
                continue
            phrase, said, op = rule
            if op in kg.frames.rules:
                continue
            r = random.Random(f"{lv}{phrase}")
            examples = []
            while len(examples) < 4:
                b = r.randint(3, 9)
                a = b * r.randint(2, 9) + r.randint(1, b - 1)        # never exact: full, left over and needed all differ
                q, rest, work = group_steps(a, b)
                if len({q, rest, q + 1}) < 3:
                    continue
                examples.append((a, b, {"&": q, "%": rest, "^": q + 1}[op]))
                log(f"    teacher: {a} in groups of {b}: {work}" + (f"; so {q + 1} groups are needed" if op == "^" else "")
                    + f" -> {phrase}: {examples[-1][2]}")
            kept, mine = kg.learn_rule(said, phrase, examples)
            log(f"  rule '{phrase}': {said} -> {'learned: its own working gives the teacher' + chr(39) + 's number every time' if kept else 'not learned: its working did not match'}")
            taught.append({"rule": phrase, "said": said, "learned": kept})
    return taught


def run_level(mind, level, log=print, real=True, sleep=True):
    """One round of a level. Every round has new stories (lessons and exams); with real=True it also reads real
    word problems and learns from the teacher's answers."""
    kg = mind.language.reading
    lv = LEVELS[level]
    done_before = next((r for r in mind.report.get("report", []) if r["level"] == level and r["subject"] == "world"), None)
    round_no = max(kg.lessons.get(f"rounds_{level}", 0), done_before.get("round", 1) if done_before else 0)
    exam_a, exam_b = exam_items(level, "A", round_no), exam_items(level, "B", round_no)
    log(f"\n== {level} world school, round {round_no + 1}: {lv['about']}")
    pre = take_exam(kg, exam_a)
    outside_before = outside_exam(kg, lv["asdiv"])
    real_before = real_exam(kg, level) if real else None
    log(f"  readiness (pre-test, no learning): {pre['score']:.0%}   outside (ASDiv grade {lv['asdiv']}, test half): "
        f"{outside_before['right']}/{outside_before['n']} understood and right"
        + (f"   real-story exam: {real_before['right']}/{real_before['n']}" if real else ""))
    rules = rules_lesson(kg, level, log)
    done = lessons(kg, level, log)
    log(f"  lessons: {lv['counting']} counting scenes (number words to {lv['count_to']}), {done['stories']} stories "
        f"with scenes; tried first on {done['tried']}: {done['right first time']} right")
    real_done = None
    if real:
        real_done = real_lessons(kg, level, REAL[level]["lessons"])
        log(f"  real stories: {real_done['real stories']} word problems people wrote, no scenes; right first time "
            f"{real_done['right first time']}; it found what it misread in {real_done['learned from']}")
        log(f"  words it met but doesn't know (teach them in the chat, like 'migrating means flying away'): "
            f"{', '.join(real_done['words to ask'][:12])}")
    slept = kg.sleep(SLEEP) if sleep else None
    if slept and slept["replayed"]:
        log(f"  sleep: relived {slept['replayed']} remembered stories, an equal share from every stage: "
            f"{', '.join(f'{k} {v}' for k, v in slept['by_stage'].items())}")
    final = take_exam(kg, exam_a)
    attempts = [{"exam": "A", "score": final["score"], "predicted": final["predicted"]}]
    log(f"  self-assessment: says it understood {final['predicted']:.0%}   exam A: {final['score']:.0%} ({al(final['score'])})")
    fb = feedback(final)
    if final["score"] < MASTERY:
        log(f"  below mastery. Work on: {', '.join(fb['work_on'])}")
        for m in fb["mistakes"][:8]:
            log(f"    - {m}")
        fixed = remediate(kg, final, log, level)
        more = lessons(kg, level, log, kinds=fb["weak"], stories=1500)
        log(f"  feedback: the teacher showed {len(fb['mistakes'])} answers ({fixed} misread sentences found); "
            f"{more['stories']} more stories of the weak kinds")
        final = take_exam(kg, exam_b)
        attempts.append({"exam": "B", "score": final["score"], "predicted": final["predicted"]})
        fb = feedback(final)
        log(f"  retake (parallel exam B): says it understood {final['predicted']:.0%}   exam: {final['score']:.0%} "
            f"({al(final['score'])})")
        for m in fb["mistakes"][:8]:
            log(f"    - {m}")
    outside = outside_exam(kg, lv["asdiv"])
    log(f"  outside exam (ASDiv grade {lv['asdiv']}, test half, no language model): understood {outside['understood']}"
        f"/{outside['n']}, right {outside['right']} ({outside['right'] / outside['n']:.1%}); always answering: "
        f"{outside['guess_right'] / outside['n']:.1%}")
    real_after = real_exam(kg, level) if real else None
    if real:
        log(f"  real-story exam ({real_after['n']} it never read): understood {real_after['understood']}, right "
            f"{real_after['right']}; always answering {real_after['guess_right']}")
    kg.lessons[f"rounds_{level}"] = round_no + 1
    entry = {"level": level, "subject": "world", "about": lv["about"], "readiness": round(pre["score"], 3),
             "score": round(final["score"], 3), "grade": al(final["score"]), "predicted": round(final["predicted"], 3),
             "attempts": attempts, "mastered": final["score"] >= MASTERY, "strengths": fb["strengths"],
             "work_on": fb["work_on"], "mistakes": fb["mistakes"][:20], "date": date.today().isoformat(),
             "outside": {k: outside[k] for k in ("grade", "split", "n", "understood", "right", "guess_right")},
             "outside_before": {k: outside_before[k] for k in ("n", "understood", "right", "guess_right")},
             "round": round_no + 1, "real": real_after, "real_before": real_before, "real_lessons": real_done,
             "words_to_learn": (real_done or {}).get("words to ask", []), "rules": rules}
    return entry


def file_report(mind, entry, subject="world"):
    """Put a round on the report card; earlier rounds of the level stay in its history."""
    old = next((r for r in mind.report.get("report", []) if r["level"] == entry["level"] and r["subject"] == subject), None)
    history = (old.get("history", []) + [{k: old.get(k) for k in ("round", "score", "grade", "outside", "real", "date")}]
               if old else [])
    mind.report["report"] = [r for r in mind.report.get("report", [])
                             if not (r["level"] == entry["level"] and r["subject"] == subject)] + [{**entry, "history": history}]


def main():
    from .regions import Mind
    ap = argparse.ArgumentParser()
    ap.add_argument("level", choices=list(LEVELS))
    ap.add_argument("--state", default=str(Path(__file__).resolve().parent.parent / "brain_state"))
    ap.add_argument("--dry-run", action="store_true", help="teach a copy and save nothing")
    ap.add_argument("--world-only", action="store_true", help="no real stories this round")
    args = ap.parse_args()
    mind = Mind.load(args.state)
    entry = run_level(mind, args.level, real=not args.world_only)
    if not args.dry_run:
        file_report(mind, entry)
        mind.save(args.state)
    sys.stdout.buffer.write(("\nREPORT " + json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
