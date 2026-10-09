"""A small simulated world: the brain's senses for kindergarten.

The brain has no eyes or body, so this module plays "reality". It shows scenes
(what the eyes would see: things with a look, a colour, a size, how many, where
they are, what they are doing, faces, the weather) and a teacher talks about
them in simple sentences. The brain only ever gets what it SEES (features such
as `colour:red`, `thing:dog`, `count:3`, `rel:under`) and what it HEARS (the
sentence); it is never told which word means which feature.

What the world knows about itself (dogs have four legs, a puppy is a young
dog) is used by the teacher to talk truthfully, not given to the brain.
"""
import random

COLOURS = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white", "grey"]
SIZES = ["big", "small"]
SHAPES = ["circle", "square", "triangle", "star", "heart", "rectangle"]
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty"]
PLACES = {"in": "in", "on": "on", "under": "under", "next to": "next", "behind": "behind", "in front of": "front"}
FEELINGS = ["happy", "sad", "angry", "scared", "tired", "surprised"]
WEATHER = {"sunny": "sun", "rainy": "rain", "cloudy": "cloud", "windy": "wind", "snowy": "snow"}
PEOPLE = {"Tom": "boy", "Ben": "boy", "Sam": "boy", "Raj": "boy", "Leo": "boy", "Ali": "boy",
          "Ana": "girl", "Mia": "girl", "Lily": "girl", "Zoe": "girl", "Kim": "girl", "Ema": "girl"}

# the world's own knowledge: kind -> facts (the teacher's truth, not given to the brain directly)
KINDS = {
    # animals                          category   legs  sound      can
    "dog": ("animal", 4, "woof", "run"), "cat": ("animal", 4, "meow", "jump"), "cow": ("animal", 4, "moo", "walk"),
    "duck": ("bird", 2, "quack", "swim"), "hen": ("bird", 2, "cluck", "walk"), "owl": ("bird", 2, "hoot", "fly"),
    "sheep": ("animal", 4, "baa", "walk"), "pig": ("animal", 4, "oink", "run"), "horse": ("animal", 4, "neigh", "run"),
    "frog": ("animal", 4, "croak", "jump"), "lion": ("animal", 4, "roar", "run"), "bird": ("bird", 2, "tweet", "fly"),
    "fish": ("animal", 0, None, "swim"), "bee": ("insect", 6, "buzz", "fly"), "ant": ("insect", 6, None, "walk"),
    "spider": ("animal", 8, None, "walk"), "monkey": ("animal", 2, None, "climb"), "rabbit": ("animal", 4, None, "jump"),
    # food
    "apple": ("fruit",), "banana": ("fruit",), "orange": ("fruit",), "grape": ("fruit",), "mango": ("fruit",),
    "pear": ("fruit",), "carrot": ("vegetable",), "potato": ("vegetable",), "tomato": ("vegetable",),
    "bread": ("food",), "cake": ("food",), "egg": ("food",), "cookie": ("food",), "rice": ("food",),
    # toys and things
    "ball": ("toy",), "doll": ("toy",), "kite": ("toy",), "block": ("toy",), "car": ("vehicle",),
    "bus": ("vehicle",), "bike": ("vehicle",), "boat": ("vehicle",), "train": ("vehicle",),
    "book": ("thing",), "cup": ("thing",), "hat": ("clothes",), "shoe": ("clothes",), "sock": ("clothes",),
    "box": ("thing",), "table": ("furniture",), "chair": ("furniture",), "bed": ("furniture",), "bag": ("thing",),
    # the bigger world (grown after kindergarten stage 1-5): more things children count and swap
    "marble": ("toy",), "sticker": ("toy",), "balloon": ("toy",), "card": ("toy",), "puzzle": ("toy",),
    "pencil": ("thing",), "crayon": ("thing",), "shell": ("thing",), "stamp": ("thing",), "coin": ("thing",),
    "flower": ("plant",), "leaf": ("plant",), "tree": ("plant",), "peach": ("fruit",), "plum": ("fruit",),
    "lemon": ("fruit",), "candy": ("food",), "pie": ("food",), "sandwich": ("food",), "basket": ("thing",),
    "jar": ("thing",), "plate": ("thing",), "bowl": ("thing",), "shelf": ("furniture",), "bottle": ("thing",),
}
CONTAINERS = ["bag", "box", "basket", "jar", "plate", "bowl", "shelf"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TIMES = ["morning", "afternoon", "evening"]
CATEGORY_PARENTS = {"bird": "animal", "insect": "animal", "fruit": "food", "vegetable": "food"}
YOUNG = {"puppy": "dog", "kitten": "cat", "calf": "cow", "duckling": "duck", "chick": "hen", "lamb": "sheep",
         "piglet": "pig", "foal": "horse", "tadpole": "frog", "cub": "lion"}
ACTIONS = ["run", "jump", "walk", "swim", "fly", "climb", "sleep", "eat", "sing", "dance", "read", "sit"]
# things that happen to quantities: verb -> what happens to the subject and to the other person (n = the number said)
EVENTS = {
    "gives": ("-n", "+n"), "gets": ("+n", None), "finds": ("+n", None), "buys": ("+n", None),
    "eats": ("-n", None), "loses": ("-n", None), "takes": ("+n", "-n"), "sells": ("-n", None),
    "picks": ("+n", None), "drops": ("-n", None), "makes": ("+n", None), "breaks": ("-n", None),
}
FURNITURE = ["table", "chair", "bed", "box", "bag"]


# verbs in stories: base -> (he/she form, past, what happens to the subject, to the other person)
VERBS = {
    "give": ("gives", "gave", "-", "+"), "take": ("takes", "took", "+", "-"), "get": ("gets", "got", "+", None),
    "find": ("finds", "found", "+", None), "buy": ("buys", "bought", "+", None), "eat": ("eats", "ate", "-", None),
    "lose": ("loses", "lost", "-", None), "sell": ("sells", "sold", "-", None), "pick": ("picks", "picked", "+", None),
    "drop": ("drops", "dropped", "-", None), "make": ("makes", "made", "+", None), "break": ("breaks", "broke", "-", None),
    "collect": ("collects", "collected", "+", None), "use": ("uses", "used", "-", None), "win": ("wins", "won", "+", None),
    "receive": ("receives", "received", "+", None), "throw away": ("throws away", "threw away", "-", None),
    "give away": ("gives away", "gave away", "-", None),
}
MONEY_VERBS = {"spend": ("spends", "spent", "-"), "earn": ("earns", "earned", "+"), "save": ("saves", "saved", "+"),
               "get": ("gets", "got", "+"), "lose": ("loses", "lost", "-"), "find": ("finds", "found", "+")}
SETTINGS = ["at the park", "at school", "in the garden", "at the shop", "on the way home", "after school",
            "for {pos} birthday", "with {pos} friends", "at the market", "in {pos} room", "that day", "after lunch"]
GAINS = [v for v, f in VERBS.items() if f[2] == "+" and not f[3]]
LOSSES = [v for v, f in VERBS.items() if f[2] == "-" and not f[3]]
COUNTABLE = [k for k, v in KINDS.items() if v[0] in ("fruit", "food", "toy", "thing", "plant")
             and k not in CONTAINERS + ["tree", "rice", "bread"]]


def plural(word):
    irregular = {"sheep": "sheep", "fish": "fish", "mouse": "mice", "child": "children", "man": "men", "foot": "feet",
                 "leaf": "leaves", "candy": "candies", "shelf": "shelves"}
    if word in irregular:
        return irregular[word]
    if word.endswith(("s", "x", "ch", "sh")):
        return word + "es"
    if word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


class World:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def _thing(self, kinds=None):
        r = self.rng
        kind = r.choice(kinds or list(KINDS))
        return {"kind": kind, "colour": r.choice(COLOURS), "size": r.choice(SIZES),
                "count": r.choice([1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), "shape": r.choice(SHAPES)}

    # ---- stage 1-2: scenes and talk ------------------------------------------------------------
    def scene(self, focus=None):
        """A scene and what the teacher says about it. -> (seen: list of features, heard: sentence, truth)."""
        r = self.rng
        things = [self._thing() for _ in range(r.randint(2, 4))]
        weather = r.choice(list(WEATHER))
        person = r.choice(list(PEOPLE))
        feeling = r.choice(FEELINGS)
        action = r.choice(ACTIONS)
        day, time = r.choice(DAYS), r.choice(TIMES)
        seen = [f"sky:{WEATHER[weather]}", f"face:{feeling}", f"person:{PEOPLE[person]}", f"doing:{action}",
                f"day:{day}", f"time:{time}"]
        for t in things:
            seen += [f"thing:{t['kind']}", f"colour:{t['colour']}", f"size:{t['size']}", f"count:{t['count']}"]
        place_word, rel = r.choice(list(PLACES.items()))
        furniture = r.choice(FURNITURE)
        seen += [f"rel:{rel}", f"thing:{furniture}"]
        shape = r.choice(SHAPES)
        seen.append(f"shape:{shape}")
        t = things[0]
        name = t["kind"] if t["count"] == 1 else plural(t["kind"])
        say = focus or r.choice(["colour", "size", "count", "place", "feeling", "weather", "action", "shape", "thing",
                                 "day", "time"])
        if say == "colour":
            heard = r.choice([f"look a {t['colour']} {name}", f"the {name} is {t['colour']}", f"see the {t['colour']} {name}"])
        elif say == "size":
            heard = r.choice([f"what a {t['size']} {name}", f"the {name} is {t['size']}"])
        elif say == "count":
            heard = r.choice([f"there are {NUMBER_WORDS[t['count']]} {name}", f"look {NUMBER_WORDS[t['count']]} {name}"])
        elif say == "place":
            heard = f"the {name} is {place_word} the {furniture}"
        elif say == "feeling":
            heard = r.choice([f"{person} is {feeling}", f"look {person} feels {feeling}"])
        elif say == "weather":
            heard = r.choice([f"it is {weather} today", f"today is {weather}"])
        elif say == "action":
            heard = r.choice([f"{person} can {action}", f"look {person} likes to {action}"])
        elif say == "day":
            heard = r.choice([f"today is {day}", f"it is {day} today"])
        elif say == "time":
            heard = r.choice([f"it is {time}", f"good {time}"])
        elif say == "shape":
            heard = f"this is a {shape}"
        else:
            heard = r.choice([f"look a {t['kind']}", f"this is a {t['kind']}", f"can you see the {name}"])
        r.shuffle(seen)
        return seen, heard

    def quiz(self, kind):
        """A new scene and a question about it, with the right answer (for testing understanding)."""
        r = self.rng
        things = [self._thing() for _ in range(3)]
        while len({t["kind"] for t in things}) < 3 or len({t["colour"] for t in things}) < 3:
            things = [self._thing() for _ in range(3)]
        t = r.choice(things)
        if kind == "find colour":
            return things, f"find the {t['colour']} one", t
        if kind == "name colour":
            return things, f"what colour is the {t['kind']}", t["colour"]
        if kind == "count":
            return things, f"how many {plural(t['kind'])} are there", NUMBER_WORDS[t["count"]]
        raise ValueError(kind)

    # ---- stage 3: facts about the world ----------------------------------------------------------
    def facts(self):
        """True sentences about the world, as a teacher would say them."""
        out = []
        for kind, info in KINDS.items():
            out.append(f"a {kind} is a {info[0]}")
            if len(info) > 1:
                cat, legs, sound, can = info
                out.append(f"a {kind} has {NUMBER_WORDS[legs]} legs")
                if sound:
                    out.append(f"a {kind} says {sound}")
                out.append(f"a {kind} can {can}")
        for child, parent in CATEGORY_PARENTS.items():
            out.append(f"a {child} is an {parent}" if parent[0] in "aeiou" else f"a {child} is a {parent}")
        for young, adult in YOUNG.items():
            out.append(f"a {young} is a young {adult}")
        return out

    # ---- stage 4: things that happen ---------------------------------------------------------------
    def event(self, verbs=None):
        """Before, what is said, after: 'Tom gives Ana 2 apples'. Counts per person are what the eyes see."""
        r = self.rng
        verb = r.choice(verbs or list(EVENTS))
        a, b = r.sample(list(PEOPLE), 2)
        kind = r.choice([k for k, v in KINDS.items() if v[0] in ("fruit", "food", "toy", "thing")])
        n = r.randint(1, 6)
        before = {a: r.randint(n, n + 8), b: r.randint(n, n + 8)}
        sub, obj = EVENTS[verb]
        after = dict(before)
        after[a] += n if sub == "+n" else -n if sub == "-n" else 0
        if obj:
            after[b] += n if obj == "+n" else -n
        if obj and verb == "gives":
            heard = r.choice([f"{a} gives {b} {n} {plural(kind)}", f"{a} gives {n} {plural(kind)} to {b}"])
        elif obj:
            heard = f"{a} {verb} {n} {plural(kind)} from {b}"
        else:
            heard = f"{a} {verb} {n} {plural(kind)}"
        return before, heard, after, {"subject": a, "other": b if obj else None, "n": n, "kind": kind}

    def story(self, verbs=None, ask=None):
        """A short story and a question: 'Mia has 7 cookies. She eats 2 cookies. How many cookies does Mia have now?'"""
        r = self.rng
        verb = r.choice(verbs or list(EVENTS))
        a, b = r.sample(list(PEOPLE), 2)
        kind = r.choice([k for k, v in KINDS.items() if v[0] in ("fruit", "food", "toy", "thing")])
        n = r.randint(1, 9)
        start_a, start_b = r.randint(n, n + 12), r.randint(n, n + 12)
        pron = "he" if PEOPLE[a] == "boy" else "she"
        sub, obj = EVENTS[verb]
        lines = [f"{a} has {start_a} {plural(kind)}."]
        if obj:
            lines.append(f"{b} has {start_b} {plural(kind)}.")
        if obj and verb == "gives":
            lines.append(f"{pron.capitalize()} gives {n} {plural(kind)} to {b}.")
        elif obj:
            lines.append(f"{pron.capitalize()} {verb} {n} {plural(kind)} from {b}.")
        else:
            lines.append(f"{pron.capitalize()} {verb} {n} {plural(kind)}.")
        end_a = start_a + (n if sub == "+n" else -n)
        end_b = start_b + ((n if obj == "+n" else -n) if obj else 0)
        ask = ask or r.choice(["subject", "other", "altogether"] if obj else ["subject"])
        if ask == "subject":
            q, ans = f"How many {plural(kind)} does {a} have now?", end_a
        elif ask == "other":
            q, ans = f"How many {plural(kind)} does {b} have now?", end_b
        else:
            q, ans = f"How many {plural(kind)} do {a} and {b} have altogether now?", end_a + end_b
        return " ".join(lines + [q]), ans
