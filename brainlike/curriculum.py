"""The school curriculum: what is taught at each level, and the exams.

Built from Singapore's 2021 Primary Mathematics syllabus and 2020 English
Language syllabus (lower primary = P1-P2: word- and phrase-level grammar
first), with Estonia's integrated, real-life tasks (math in English
sentences, money and time). Sources: Vault/research/2026-10-01-singapore-estonia-primary.

Lesson items (the teacher's moves):
  ("auto", "7+8")                      the brain tries a fact, the teacher says right/wrong until it gets it
  ("teach", question, answer)          the teacher gives the answer (the brain says what it would have said first)
  ("say", statement)                   a statement to learn: "a dog is an animal", "solve a+?=c by c-a"
  ("word", problem, bar_model)         a word problem: it tries; if wrong the teacher shows the model (5+3)
  ("fact", question, answer)           a plain fact for the knowledge region (minutes in an hour = 60)
Exam items: (topic, question, expected answer). Exams A and B are parallel: B is the retake.
Exams use words and numbers that were NOT in the lessons (and made-up "wug" words), so they
test whether it learned rules, not just memorised the lessons.
"""

# ---- the teacher's own knowledge of English word forms (to judge rules the brain notices) ----
KEY = {
    "plural": {
        "cat": "cats", "dog": "dogs", "book": "books", "pen": "pens", "tree": "trees", "girl": "girls", "car": "cars",
        "bag": "bags", "cup": "cups", "bird": "birds", "hat": "hats", "frog": "frogs", "ball": "balls", "door": "doors",
        "bed": "beds", "egg": "eggs", "duck": "ducks", "star": "stars", "desk": "desks", "shoe": "shoes",
        "bus": "buses", "glass": "glasses", "box": "boxes", "fox": "foxes", "dish": "dishes", "brush": "brushes",
        "watch": "watches", "bench": "benches", "class": "classes", "dress": "dresses", "lunch": "lunches",
        "wish": "wishes", "kiss": "kisses", "peach": "peaches", "match": "matches", "tax": "taxes",
        "baby": "babies", "city": "cities", "lady": "ladies", "story": "stories", "party": "parties",
        "berry": "berries", "puppy": "puppies", "fly": "flies", "pony": "ponies", "cherry": "cherries",
        "boy": "boys", "toy": "toys", "day": "days", "key": "keys", "monkey": "monkeys", "tray": "trays",
        "child": "children", "man": "men", "woman": "women", "foot": "feet", "tooth": "teeth", "mouse": "mice",
        "sheep": "sheep", "fish": "fish", "goose": "geese", "person": "people",
    },
    "third": {
        "play": "plays", "run": "runs", "eat": "eats", "sing": "sings", "jump": "jumps", "read": "reads",
        "walk": "walks", "swim": "swims", "sit": "sits", "like": "likes", "make": "makes", "ride": "rides",
        "help": "helps", "cook": "cooks", "drink": "drinks", "sleep": "sleeps", "write": "writes", "kick": "kicks",
        "go": "goes", "watch": "watches", "fix": "fixes", "wash": "washes", "catch": "catches", "brush": "brushes",
        "miss": "misses", "push": "pushes", "teach": "teaches", "mix": "mixes",
        "cry": "cries", "fly": "flies", "carry": "carries", "try": "tries", "study": "studies", "hurry": "hurries",
        "do": "does", "have": "has",
    },
    "past": {
        "walk": "walked", "jump": "jumped", "play": "played", "look": "looked", "help": "helped", "call": "called",
        "clean": "cleaned", "cook": "cooked", "kick": "kicked", "open": "opened", "paint": "painted", "pull": "pulled",
        "push": "pushed", "talk": "talked", "climb": "climbed", "rain": "rained", "visit": "visited", "wash": "washed",
        "like": "liked", "love": "loved", "smile": "smiled", "dance": "danced", "bake": "baked", "close": "closed",
        "skate": "skated", "live": "lived", "move": "moved", "share": "shared",
        "carry": "carried", "cry": "cried", "try": "tried", "study": "studied", "hurry": "hurried", "worry": "worried",
        "stop": "stopped", "hop": "hopped", "clap": "clapped", "drop": "dropped", "plan": "planned", "hug": "hugged",
        "nod": "nodded", "rub": "rubbed", "beg": "begged", "pat": "patted",
        "go": "went", "eat": "ate", "see": "saw", "run": "ran", "come": "came", "have": "had", "sit": "sat",
        "swim": "swam", "drink": "drank", "write": "wrote", "give": "gave", "take": "took", "sing": "sang",
        "make": "made", "get": "got", "say": "said", "do": "did", "is": "was", "buy": "bought", "fly": "flew",
    },
    "ing": {
        "play": "playing", "read": "reading", "eat": "eating", "sing": "singing", "jump": "jumping",
        "walk": "walking", "cook": "cooking", "drink": "drinking", "sleep": "sleeping", "look": "looking",
        "make": "making", "ride": "riding", "write": "writing", "smile": "smiling", "dance": "dancing",
        "bake": "baking", "skate": "skating", "come": "coming", "hide": "hiding", "share": "sharing",
        "run": "running", "swim": "swimming", "sit": "sitting", "hop": "hopping", "stop": "stopping",
        "dig": "digging", "clap": "clapping", "shop": "shopping", "cut": "cutting", "hug": "hugging",
    },
    "article": {w: ("an " if w[0] in "aeiou" else "a ") + w for w in [
        "apple", "egg", "orange", "umbrella", "ant", "elephant", "insect", "owl", "igloo", "onion", "ink", "arm",
        "cat", "dog", "ball", "book", "car", "pen", "tree", "girl", "boy", "house", "kite", "lion", "mango", "bag"]},
}

KEY["comparative"] = {
    "tall": "taller", "short": "shorter", "fast": "faster", "small": "smaller", "old": "older", "cold": "colder",
    "long": "longer", "strong": "stronger", "quick": "quicker", "kind": "kinder", "soft": "softer", "loud": "louder",
    "nice": "nicer", "large": "larger", "wide": "wider", "safe": "safer", "cute": "cuter", "late": "later",
    "happy": "happier", "easy": "easier", "busy": "busier", "heavy": "heavier", "pretty": "prettier", "funny": "funnier",
    "noisy": "noisier", "tidy": "tidier",
    "big": "bigger", "hot": "hotter", "thin": "thinner", "fat": "fatter", "sad": "sadder", "wet": "wetter",
    "beautiful": "more beautiful", "expensive": "more expensive", "dangerous": "more dangerous",
    "important": "more important", "famous": "more famous", "careful": "more careful", "modern": "more modern",
    "delicious": "more delicious", "colourful": "more colourful", "difficult": "more difficult",
    "good": "better", "bad": "worse", "far": "farther",
}
KEY["superlative"] = {
    w: ("most " + c.split(" ", 1)[1] if c.startswith("more ") else
        {"better": "best", "worse": "worst", "farther": "farthest"}.get(c, c[:-2] + "est" if c.endswith("er") else c))
    for w, c in KEY["comparative"].items()}
KEY["adverb"] = {
    "quick": "quickly", "slow": "slowly", "loud": "loudly", "quiet": "quietly", "careful": "carefully", "sad": "sadly",
    "kind": "kindly", "soft": "softly", "brave": "bravely", "nice": "nicely", "safe": "safely", "polite": "politely",
    "happy": "happily", "easy": "easily", "angry": "angrily", "lucky": "luckily", "noisy": "noisily", "busy": "busily",
    "gentle": "gently", "simple": "simply", "terrible": "terribly", "humble": "humbly",
    "good": "well", "fast": "fast", "hard": "hard",
}
KEY["negative"] = {
    "happy": "unhappy", "kind": "unkind", "fair": "unfair", "safe": "unsafe", "tidy": "untidy", "lucky": "unlucky",
    "well": "unwell", "friendly": "unfriendly", "clear": "unclear", "able": "unable", "known": "unknown",
    "agree": "disagree", "like": "dislike", "honest": "dishonest", "obey": "disobey", "appear": "disappear",
}

# words a teacher knows are exceptions: they don't count against a rule (made doesn't disprove "like -> liked")
IRREGULAR = {
    "plural": {"child", "man", "woman", "foot", "tooth", "mouse", "sheep", "fish", "goose", "person"},
    "past": {"go", "eat", "see", "run", "come", "have", "sit", "swim", "drink", "write", "give", "take", "sing",
             "make", "get", "say", "do", "is", "buy", "fly"},
    "third": {"have"},
    "ing": set(),
    "article": set(),
    "comparative": {"good", "bad", "far"},
    "superlative": {"good", "bad", "far"},
    "adverb": {"good", "fast", "hard"},
    "negative": {"agree", "like", "honest", "obey", "appear"},     # dis- words: which prefix is a matter of memory
}

LEVELS = ["P1", "P2", "P3"]           # P4-P6 follow

CURRICULUM = {
    "P1": {
        "math": {
            "about": "numbers to 100; adding and subtracting within 100 (mental within 20); number bonds "
                     "(missing numbers); comparing; concepts of multiplication and division; money; time",
            "lessons": [
                *[("auto", f"{a}+{b}") for a in range(10) for b in range(10) if a + b <= 18],
                *[("auto", f"{a}-{b}") for a in range(10) for b in range(a + 1)],
                ("teach", "5 + ?", "9 = 4"), ("teach", "3 + ?", "10 = 7"), ("teach", "6 + ?", "8 = 2"),
                ("teach", "? + 4", "7 = 3"), ("teach", "? + 2", "9 = 7"), ("teach", "? + 5", "12 = 7"),
                ("teach", "9 - ?", "4 = 5"), ("teach", "8 - ?", "6 = 2"), ("teach", "7 - ?", "3 = 4"),
                ("fact", "cents in a dollar", "100"), ("fact", "minutes in an hour", "60"),
                ("fact", "minutes in half an hour", "30"),
                ("word", "Tom has 5 apples and gets 3 more. How many apples does he have now?", "5+3"),
                ("word", "There are 12 birds on a tree. 4 fly away. How many birds are left?", "12-4"),
                ("word", "Ana has 7 pencils. Ben has 2 more pencils than Ana. How many pencils does Ben have?", "7+2"),
                ("word", "There are 3 plates with 4 cakes on each plate. How many cakes are there?", "3*4"),
                ("word", "Mum shares 12 sweets equally among 3 children. How many sweets does each child get?", "12/3"),
            ],
            "exams": [[
                ("adding within 20", "8+6", "14"), ("adding within 20", "9+7", "16"),
                ("subtracting within 20", "15-7", "8"), ("subtracting within 20", "13-9", "4"),
                ("within 100", "45+3", "48"), ("within 100", "56+30", "86"), ("within 100", "78-40", "38"),
                ("missing numbers", "4 + ? = 13", "9"), ("missing numbers", "? + 6 = 14", "8"),
                ("missing numbers", "10 - ? = 3", "7"),
                ("comparing", "Which number is bigger, 67 or 76?", "76"), ("comparing", "38 ? 83", "38 < 83"),
                ("multiplying and dividing", "5*4", "20"), ("multiplying and dividing", "20/5", "4"),
                ("word problems", "Sam has 9 marbles. He finds 6 more. How many marbles does he have now?", "15"),
                ("word problems", "A bag has 16 oranges. 7 are eaten. How many oranges are left?", "9"),
                ("money", "Lily has 1 dollar and 25 cents. How many cents does she have?", "125"),
                ("time", "A film lasts 2 hours. How many minutes is that?", "120"),
            ], [
                ("adding within 20", "7+8", "15"), ("adding within 20", "9+6", "15"),
                ("subtracting within 20", "14-6", "8"), ("subtracting within 20", "16-8", "8"),
                ("within 100", "62+5", "67"), ("within 100", "34+40", "74"), ("within 100", "95-30", "65"),
                ("missing numbers", "5 + ? = 12", "7"), ("missing numbers", "? + 8 = 15", "7"),
                ("missing numbers", "12 - ? = 5", "7"),
                ("comparing", "Which number is smaller, 54 or 45?", "45"), ("comparing", "91 ? 19", "91 > 19"),
                ("multiplying and dividing", "2*9", "18"), ("multiplying and dividing", "15/3", "5"),
                ("word problems", "Kim has 8 stickers. Her friend gives her 7 more. How many stickers does Kim have now?", "15"),
                ("word problems", "There are 18 children in a room. 9 go out. How many children are still in the room?", "9"),
                ("money", "Raj has 2 dollars and 40 cents. How many cents does he have?", "240"),
                ("time", "Lunch break lasts half an hour. How many minutes is that?", "30"),
            ]],
        },
        "english": {
            "about": "nouns: one and many (-s, -es); a/an; verbs: present (he plays) and past (-ed); "
                     "opposites; groups of things (a cow is an animal); nouns, verbs and adjectives",
            "lessons": [
                *[("teach", f"plural of {w}", KEY["plural"][w]) for w in
                  ["cat", "dog", "book", "pen", "tree", "girl", "car", "bag", "cup", "hat", "frog", "ball", "door", "bed",
                   "bus", "glass", "box", "fox", "dish", "brush", "watch", "bench", "dress", "lunch"]],
                *[("teach", f"article of {w}", KEY["article"][w]) for w in
                  ["apple", "egg", "orange", "umbrella", "ant", "elephant", "cat", "dog", "ball", "book", "car", "pen"]],
                *[("teach", f"third of {w}", KEY["third"][w]) for w in
                  ["play", "run", "eat", "sing", "jump", "read", "walk", "help", "go", "watch", "fix", "wash", "catch"]],
                *[("teach", f"past of {w}", KEY["past"][w]) for w in
                  ["walk", "jump", "play", "look", "help", "call", "clean", "cook", "kick", "pull", "talk", "climb",
                   "like", "love", "smile", "dance", "bake", "close"]],
                ("teach", "She (play) with her friends every day.", "plays"),
                ("teach", "He (read) a book every night.", "reads"), ("teach", "Tom (eat) an apple every day.", "eats"),
                ("teach", "They (play) football every day.", "play"), ("teach", "I (walk) to school every day.", "walk"),
                ("teach", "We (sing) songs every morning.", "sing"), ("teach", "You (help) your mum every day.", "help"),
                ("teach", "It (jump) every morning.", "jumps"), ("teach", "She (watch) TV every evening.", "watches"),
                ("teach", "Yesterday she (walk) to the park.", "walked"), ("teach", "Yesterday we (play) in the rain.", "played"),
                ("teach", "Last week I (cook) rice.", "cooked"), ("teach", "Yesterday Tom (kick) the ball.", "kicked"),
                ("teach", "Last night they (talk) for hours.", "talked"), ("teach", "Yesterday he (help) his dad.", "helped"),
                ("teach", "Last week she (bake) a cake.", "baked"), ("teach", "Yesterday the baby (smile) at me.", "smiled"),
                *[("teach", f"opposite of {a}", b) for a, b in
                  [("big", "small"), ("hot", "cold"), ("happy", "sad"), ("tall", "short"), ("fast", "slow"),
                   ("up", "down"), ("day", "night"), ("old", "young"), ("wet", "dry"), ("open", "shut")]],
                ("say", "a dog is an animal"), ("say", "a cat is an animal"), ("say", "a cow is an animal"),
                ("say", "a lion is an animal"), ("say", "a puppy is a dog"), ("say", "a kitten is a cat"),
                ("say", "an apple is a fruit"), ("say", "a banana is a fruit"), ("say", "a mango is a fruit"),
                ("say", "red is a colour"), ("say", "blue is a colour"), ("say", "a calf is a cow"),
                *[("teach", f"word class of {w}", c) for w, c in
                  [("cat", "noun"), ("book", "noun"), ("school", "noun"), ("apple", "noun"), ("run", "verb"),
                   ("eat", "verb"), ("jump", "verb"), ("sing", "verb"), ("big", "adjective"), ("happy", "adjective"),
                   ("red", "adjective"), ("tall", "adjective")]],
            ],
            "exams": [[
                ("plurals: add -s", "plural of bird", "birds"), ("plurals: add -s", "plural of duck", "ducks"),
                ("plurals: add -s", "plural of wug", "wugs"),
                ("plurals: add -es", "plural of peach", "peaches"), ("plurals: add -es", "plural of wish", "wishes"),
                ("plurals: add -es", "plural of tass", "tasses"),
                ("a or an", "article of insect", "an insect"), ("a or an", "article of owl", "an owl"),
                ("a or an", "article of kite", "a kite"), ("a or an", "article of lion", "a lion"),
                ("he/she form", "third of drink", "drinks"), ("he/she form", "third of push", "pushes"),
                ("past -ed", "past of paint", "painted"), ("past -ed", "past of skate", "skated"),
                ("past -ed", "past of rick", "ricked"),
                ("sentences", "She (cook) dinner every day.", "cooks"), ("sentences", "They (walk) home every day.", "walk"),
                ("sentences", "Yesterday I (climb) a tree.", "climbed"),
                ("opposites", "opposite of small", "big"), ("opposites", "opposite of night", "day"),
                ("groups", "is a puppy an animal?", "yes"), ("groups", "is a kitten an animal?", "yes"),
            ], [
                ("plurals: add -s", "plural of star", "stars"), ("plurals: add -s", "plural of desk", "desks"),
                ("plurals: add -s", "plural of blick", "blicks"),
                ("plurals: add -es", "plural of match", "matches"), ("plurals: add -es", "plural of kiss", "kisses"),
                ("plurals: add -es", "plural of zatch", "zatches"),
                ("a or an", "article of igloo", "an igloo"), ("a or an", "article of onion", "an onion"),
                ("a or an", "article of house", "a house"), ("a or an", "article of mango", "a mango"),
                ("he/she form", "third of sleep", "sleeps"), ("he/she form", "third of brush", "brushes"),
                ("past -ed", "past of rain", "rained"), ("past -ed", "past of live", "lived"),
                ("past -ed", "past of glorp", "glorped"),
                ("sentences", "He (kick) the ball every day.", "kicks"), ("sentences", "We (clean) our room every day.", "clean"),
                ("sentences", "Last week we (visit) grandma.", "visited"),
                ("opposites", "opposite of cold", "hot"), ("opposites", "opposite of slow", "fast"),
                ("groups", "is a calf an animal?", "yes"), ("groups", "is a mango a fruit?", "yes"),
            ]],
        },
        "integrated": {
            "about": "math in English sentences, money and time in real life (Estonia: learning across subjects)",
            "lessons": [
                ("word", "A pencil costs 30 cents and a rubber costs 20 cents. How many cents do they cost together?", "30+20"),
                ("word", "Ali has 1 dollar. He spends 40 cents. How many cents does he have left?", "1*100-40"),
                ("word", "School starts at 8 o'clock and ends 6 hours later. At what o'clock does it end?", "8+6"),
            ],
            "exams": [[
                ("money", "A bun costs 60 cents and a drink costs 35 cents. How many cents do they cost together?", "95"),
                ("money", "Mia has 1 dollar. She buys a pencil for 45 cents. How many cents does she have left?", "55"),
                ("time", "A game starts at 3 o'clock and lasts 2 hours. At what o'clock does it end?", "5"),
                ("word problems", "There are 4 boxes with 5 crayons in each box. How many crayons are there?", "20"),
                ("word problems", "Dad has 20 stamps. He gives 5 stamps to each of his children and has none left. How many children does he have?", "4"),
            ], [
                ("money", "An apple costs 45 cents and a pear costs 50 cents. How many cents do they cost together?", "95"),
                ("money", "Ben has 1 dollar. He spends 70 cents. How many cents does he have left?", "30"),
                ("time", "The shop opens at 9 o'clock and closes 8 hours later. At what o'clock does it close?", "17"),
                ("word problems", "There are 5 vases with 3 flowers in each vase. How many flowers are there?", "15"),
                ("word problems", "18 eggs are put into boxes of 6. How many boxes are there?", "3"),
            ]],
        },
    },
    "P2": {
        "math": {
            "about": "numbers to 1000; adding and subtracting up to 3 digits; times tables 2, 3, 4, 5 and 10 and the "
                     "link between multiplying and dividing; fractions (part of a whole, compare, add like fractions); "
                     "money in dollars and cents; length, mass, volume; time in hours and minutes",
            "lessons": [
                *[("auto", f"{t}*{n}") for t in (2, 3, 4, 5) for n in range(10)],
                *[("auto", f"{n}*{t}") for t in (2, 3, 4, 5) for n in range(10)],
                ("teach", "3 * ?", "12 = 4"), ("teach", "5 * ?", "35 = 7"), ("teach", "2 * ?", "16 = 8"),
                ("teach", "? * 4", "20 = 5"), ("teach", "? * 3", "27 = 9"), ("teach", "? * 5", "40 = 8"),
                ("teach", "? / 2", "6 = 12"), ("teach", "? / 5", "4 = 20"), ("teach", "? / 3", "3 = 9"),
                ("fact", "cm in a metre", "100"), ("fact", "g in a kilogram", "1000"),
                ("fact", "ml in a litre", "1000"),
                ("word", "A ribbon is 3 metres long. How many centimetres long is it?", "3*100"),
                ("word", "A shop has 245 red balloons and 138 blue balloons. How many balloons are there?", "245+138"),
                ("word", "A baker made 500 buns and sold 263. How many buns are left?", "500-263"),
                ("word", "There are 5 bags with 4 apples in each bag. 6 apples are eaten. How many apples are left?",
                 "plan: apples = 5*4; apples-6"),
                ("word", "A cake is cut into 8 equal pieces. Sam eats 3 pieces. What fraction of the cake did he eat?", "3/8"),
            ],
            "exams": [[
                ("3-digit adding and subtracting", "356+487", "843"), ("3-digit adding and subtracting", "702-358", "344"),
                ("times tables", "4*7", "28"), ("times tables", "3*9", "27"), ("times tables", "5*8", "40"),
                ("times tables", "10*6", "60"),
                ("dividing", "24/4", "6"), ("dividing", "45/5", "9"), ("dividing", "18/3", "6"),
                ("missing numbers", "? * 4 = 32", "8"), ("missing numbers", "3 * ? = 21", "7"),
                ("missing numbers", "? / 4 = 5", "20"),
                ("fractions", "Which is bigger, 1/3 or 1/4?", "1/3"), ("fractions", "2/7+3/7", "5/7"),
                ("fractions", "5/9-2/9", "1/3"),
                ("measurement", "A rope is 4 metres long. How many centimetres long is it?", "400"),
                ("measurement", "A bag of rice weighs 2 kilograms. How many grams is that?", "2000"),
                ("time", "A trip takes 2 hours and 15 minutes. How many minutes is that?", "135"),
                ("money", "A book costs 3 dollars and 45 cents. How many cents is that?", "345"),
                ("word problems", "There are 6 rows of 5 chairs. 7 chairs are taken away. How many chairs are left?", "23"),
            ], [
                ("3-digit adding and subtracting", "468+275", "743"), ("3-digit adding and subtracting", "801-456", "345"),
                ("times tables", "4*8", "32"), ("times tables", "3*7", "21"), ("times tables", "5*9", "45"),
                ("times tables", "10*8", "80"),
                ("dividing", "28/4", "7"), ("dividing", "35/5", "7"), ("dividing", "27/3", "9"),
                ("missing numbers", "? * 5 = 30", "6"), ("missing numbers", "4 * ? = 36", "9"),
                ("missing numbers", "? / 3 = 6", "18"),
                ("fractions", "Which is smaller, 1/5 or 1/2?", "1/5"), ("fractions", "3/8+4/8", "7/8"),
                ("fractions", "7/10-3/10", "2/5"),
                ("measurement", "A path is 6 metres long. How many centimetres long is it?", "600"),
                ("measurement", "A bottle holds 3 litres of water. How many millilitres is that?", "3000"),
                ("time", "A show lasts 1 hour and 40 minutes. How many minutes is that?", "100"),
                ("money", "A toy costs 5 dollars and 60 cents. How many cents is that?", "560"),
                ("word problems", "There are 4 shelves with 9 books on each shelf. 5 books are taken out. How many books are left?", "31"),
            ]],
        },
        "english": {
            "about": "plurals with -ies and words that change (child -> children); past tense: doubled letters, "
                     "-ied and irregular verbs (went, saw); -ing and 'is ...-ing' sentences; same meanings (big = large)",
            "lessons": [
                *[("teach", f"plural of {w}", KEY["plural"][w]) for w in
                  ["baby", "city", "lady", "story", "party", "berry", "boy", "toy", "day", "key", "monkey",
                   "child", "man", "woman", "foot", "tooth", "mouse", "sheep", "fish", "goose", "person"]],
                *[("teach", f"past of {w}", KEY["past"][w]) for w in
                  ["carry", "cry", "try", "study", "stop", "hop", "clap", "drop", "plan", "hug",
                   "go", "eat", "see", "run", "come", "have", "sit", "swim", "drink", "write", "give", "take",
                   "sing", "make", "get", "say", "do", "buy", "fly"]],
                *[("teach", f"ing of {w}", KEY["ing"][w]) for w in
                  ["play", "read", "eat", "sing", "jump", "walk", "make", "ride", "write", "smile", "dance",
                   "run", "swim", "sit", "hop", "stop", "clap"]],
                *[("teach", f"third of {w}", KEY["third"][w]) for w in ["cry", "fly", "carry", "try", "do", "have"]],
                ("teach", "Look! She (dance) now.", "is dancing"), ("teach", "They (play) now.", "are playing"),
                ("teach", "I (read) a book now.", "am reading"), ("teach", "Listen! The bird (sing) now.", "is singing"),
                ("teach", "We (swim) at the moment.", "are swimming"), ("teach", "He (write) a letter at the moment.", "is writing"),
                ("teach", "Yesterday we (go) to the zoo.", "went"), ("teach", "Last night I (eat) noodles.", "ate"),
                ("teach", "Yesterday she (see) a rainbow.", "saw"),
                *[("teach", f"synonym of {a}", b) for a, b in
                  [("big", "large"), ("small", "little"), ("happy", "glad"), ("fast", "quick"), ("begin", "start"),
                   ("shut", "close"), ("sick", "ill"), ("end", "finish")]],
                *[("teach", f"opposite of {a}", b) for a, b in
                  [("light", "dark"), ("full", "empty"), ("early", "late"), ("rich", "poor"), ("clean", "dirty")]],
                ("say", "a car is a vehicle"), ("say", "a bus is a vehicle"), ("say", "a sparrow is a bird"),
                ("say", "a bird is an animal"), ("say", "a rose is a flower"), ("say", "a flower is a plant"),
            ],
            "exams": [[
                ("plurals: -ies or -s", "plural of puppy", "puppies"), ("plurals: -ies or -s", "plural of pony", "ponies"),
                ("plurals: -ies or -s", "plural of tray", "trays"), ("plurals: -ies or -s", "plural of blicky", "blickies"),
                ("plurals that change", "plural of child", "children"), ("plurals that change", "plural of tooth", "teeth"),
                ("plurals that change", "plural of mouse", "mice"),
                ("past: doubling and -ied", "past of nod", "nodded"), ("past: doubling and -ied", "past of beg", "begged"),
                ("past: doubling and -ied", "past of hurry", "hurried"), ("past: doubling and -ied", "past of worry", "worried"),
                ("irregular past", "past of go", "went"), ("irregular past", "past of swim", "swam"),
                ("irregular past", "past of write", "wrote"),
                ("-ing", "ing of bake", "baking"), ("-ing", "ing of dig", "digging"), ("-ing", "ing of cook", "cooking"),
                ("sentences now", "Look! He (ride) a bike now.", "is riding"), ("sentences now", "They (cook) dinner now.", "are cooking"),
                ("same meaning", "synonym of large", "big"), ("same meaning", "synonym of finish", "end"),
                ("opposites by reasoning", "opposite of large", "small"),
                ("groups", "is a sparrow an animal?", "yes"), ("groups", "is a rose a plant?", "yes"),
            ], [
                ("plurals: -ies or -s", "plural of cherry", "cherries"), ("plurals: -ies or -s", "plural of fly", "flies"),
                ("plurals: -ies or -s", "plural of monkey", "monkeys"), ("plurals: -ies or -s", "plural of drippy", "drippies"),
                ("plurals that change", "plural of man", "men"), ("plurals that change", "plural of foot", "feet"),
                ("plurals that change", "plural of goose", "geese"),
                ("past: doubling and -ied", "past of rub", "rubbed"), ("past: doubling and -ied", "past of pat", "patted"),
                ("past: doubling and -ied", "past of study", "studied"), ("past: doubling and -ied", "past of cry", "cried"),
                ("irregular past", "past of eat", "ate"), ("irregular past", "past of take", "took"),
                ("irregular past", "past of give", "gave"),
                ("-ing", "ing of hide", "hiding"), ("-ing", "ing of shop", "shopping"), ("-ing", "ing of sleep", "sleeping"),
                ("sentences now", "Look! She (skate) now.", "is skating"), ("sentences now", "We (drink) milk now.", "are drinking"),
                ("same meaning", "synonym of glad", "happy"), ("same meaning", "synonym of little", "small"),
                ("opposites by reasoning", "opposite of little", "big"),
                ("groups", "is a car a vehicle?", "yes"), ("groups", "is a sparrow an animal?", "yes"),
            ]],
        },
        "integrated": {
            "about": "word problems in English with money, length and time (several steps)",
            "lessons": [
                ("word", "A shirt costs 8 dollars and a cap costs 5 dollars. Ken pays with 20 dollars. How much change does he get?",
                 "plan: cost = 8+5; 20-cost"),
                ("word", "A pencil is 15 centimetres long. How long are 4 pencils in a row, in centimetres?", "15*4"),
            ],
            "exams": [[
                ("money", "A cup costs 4 dollars and a plate costs 7 dollars. Amy pays with 20 dollars. How much change does she get?", "9"),
                ("length", "A paper clip is 3 centimetres long. How long are 6 clips in a row, in centimetres?", "18"),
                ("time", "Lessons start at 8 o'clock. There are 3 lessons of 1 hour each. At what o'clock do they end?", "11"),
                ("word problems", "A farmer has 3 baskets with 9 eggs each. He sells 10 eggs. How many eggs are left?", "17"),
            ], [
                ("money", "A book costs 6 dollars and a pen costs 3 dollars. Joe pays with 10 dollars. How much change does he get?", "1"),
                ("length", "A brick is 20 centimetres long. How long are 5 bricks in a row, in centimetres?", "100"),
                ("time", "A trip starts at 9 o'clock and takes 3 hours. At what o'clock does it end?", "12"),
                ("word problems", "There are 4 boxes with 6 pens each. 9 pens are given away. How many pens are left?", "15"),
            ]],
        },
    },
}


from .curriculum_p3 import P3 as _P3  # noqa: E402  (one file per level from P3 on)
CURRICULUM["P3"] = _P3
