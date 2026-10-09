"""P3 of the school curriculum (Singapore P3 math and English, Estonia-style integrated tasks).
See curriculum.py for the item format."""
from .curriculum import KEY

P3 = {
    "math": {
        "about": "numbers to 10 000; adding and subtracting up to 4 digits; times tables 6, 7, 8 and 9; division with "
                 "remainder and what the remainder means; equivalent fractions and simplest form; money with $; "
                 "km/m, l/ml; time in minutes; area and perimeter of rectangles and squares",
        "lessons": [
            *[("auto", f"{a}-{b}") for a in range(10) for b in range(a + 1, 10)],     # used inside column methods
            *[("auto", f"{t}*{n}") for t in (6, 7, 8, 9) for n in range(10)],
            *[("auto", f"{n}*{t}") for t in (6, 7, 8, 9) for n in range(10)],
            ("fact", "m in a km", "1000"), ("fact", "seconds in a minute", "60"),
            ("fact", "area of a rectangle", "length times width"),
            ("fact", "perimeter of a rectangle", "2 times (length plus width)"),
            ("fact", "area of a square", "side times side"), ("fact", "perimeter of a square", "4 times side"),
            ("word", "A farmer packs 245 eggs into boxes of 12. How many boxes can he fill completely?", "245 div 12"),
            ("word", "Each box holds 24 books. How many boxes are needed for 1000 books?", "1000 divup 24"),
            ("word", "29 sweets are shared equally by 4 children. How many sweets are left over?", "29 rem 4"),
            ("word", "A lesson starts at 9:15 and ends at 10:05. How long is the lesson in minutes?", "(10*60+5)-(9*60+15)"),
            ("word", "A road is 3 km 250 m long. How many metres is that?", "3*1000+250"),
            ("word", "What is the perimeter of a rectangle 8 m long and 5 m wide?", "2*(8+5)"),
            ("word", "What is the area of a rectangle 9 cm long and 6 cm wide?", "9*6"),
            ("word", "Mum buys a bag for $12.50 and a hat for $8.75. How much does she spend?", "12.50+8.75"),
        ],
        "exams": [[
            ("4-digit adding and subtracting", "4785+3567", "8352"), ("4-digit adding and subtracting", "9204-3678", "5526"),
            ("times tables 6-9", "7*6", "42"), ("times tables 6-9", "8*9", "72"), ("times tables 6-9", "9*7", "63"),
            ("multiplying and dividing", "248*6", "1488"), ("multiplying and dividing", "852/6", "142"),
            ("division with remainder", "47 ÷ 6 with remainder", "7 R 5"),
            ("division with remainder", "what is the remainder when 65 is divided by 8?", "1"),
            ("fractions", "simplest form of 6/9", "2/3"), ("fractions", "3/4 = ?/12", "9"),
            ("fractions", "which is bigger, 3/4 or 5/8?", "3/4"), ("fractions", "1/2+1/4", "3/4"),
            ("money", "$6.45 + $2.80", "9.25"),
            ("measurement", "A path is 2 km 400 m long. How many metres is that?", "2400"),
            ("area and perimeter", "What is the perimeter of a rectangle 7 cm long and 3 cm wide?", "20"),
            ("area and perimeter", "What is the area of a square with sides of 6 cm?", "36"),
            ("time", "A show starts at 2:40 and ends at 4:10. How long is the show in minutes?", "90"),
            ("remainders in word problems", "A van can carry 9 boxes. How many trips are needed to move 50 boxes?", "6"),
            ("remainders in word problems", "Ali has 58 stamps and puts 8 on each page. How many full pages does he have?", "7"),
        ], [
            ("4-digit adding and subtracting", "5694+2738", "8432"), ("4-digit adding and subtracting", "8003-4567", "3436"),
            ("times tables 6-9", "6*8", "48"), ("times tables 6-9", "9*9", "81"), ("times tables 6-9", "7*8", "56"),
            ("multiplying and dividing", "367*7", "2569"), ("multiplying and dividing", "936/8", "117"),
            ("division with remainder", "59 ÷ 7 with remainder", "8 R 3"),
            ("division with remainder", "what is the remainder when 83 is divided by 9?", "2"),
            ("fractions", "simplest form of 8/12", "2/3"), ("fractions", "2/5 = ?/20", "8"),
            ("fractions", "which is smaller, 2/3 or 3/5?", "3/5"), ("fractions", "1/3+1/6", "1/2"),
            ("money", "$9.30 - $4.75", "4.55"),
            ("measurement", "A race is 5 km 50 m long. How many metres is that?", "5050"),
            ("area and perimeter", "What is the perimeter of a square with sides of 9 m?", "36"),
            ("area and perimeter", "What is the area of a rectangle 8 cm long and 7 cm wide?", "56"),
            ("time", "A bus leaves at 7:35 and arrives at 8:20. How long is the trip in minutes?", "45"),
            ("remainders in word problems", "A lift can take 8 people. How many trips are needed for 30 people?", "4"),
            ("remainders in word problems", "70 cookies are put into bags of 9. How many cookies are left over?", "7"),
        ]],
    },
    "english": {
        "about": "comparing: -er/-est and more/most, better/best; adverbs (-ly); opposites with un- and dis-; "
                 "past continuous (was reading) and future (will go); agreement with nouns (the dog barks / the dogs bark); "
                 "word endings that show the word class (-ful, -ly, -ness)",
        "lessons": [
            *[("teach", f"comparative of {w}", KEY["comparative"][w]) for w in
              ["tall", "short", "fast", "small", "old", "cold", "strong", "quick", "nice", "large", "wide", "safe",
               "happy", "easy", "busy", "heavy", "big", "hot", "thin", "fat", "beautiful", "expensive", "dangerous",
               "important", "famous", "careful", "good", "bad", "far"]],
            *[("teach", f"superlative of {w}", KEY["superlative"][w]) for w in
              ["tall", "short", "fast", "small", "old", "nice", "large", "wide", "happy", "easy", "busy", "big", "hot",
               "thin", "beautiful", "expensive", "dangerous", "famous", "good", "bad", "far"]],
            *[("teach", f"adverb of {w}", KEY["adverb"][w]) for w in
              ["quick", "slow", "loud", "quiet", "careful", "sad", "kind", "brave", "nice", "happy", "easy", "angry",
               "busy", "gentle", "simple", "terrible", "good", "fast", "hard"]],
            *[("teach", f"negative of {w}", KEY["negative"][w]) for w in
              ["happy", "kind", "fair", "safe", "tidy", "well", "friendly", "known", "agree", "like", "honest", "obey", "appear"]],
            ("teach", "She (read) a book while it was raining.", "was reading"),
            ("teach", "They (play) while the baby slept.", "were playing"),
            ("teach", "I (cook) while you watched TV.", "was cooking"),
            ("teach", "We (walk) home when the storm came.", "were walking"),
            ("teach", "He (sleep) when the phone rang.", "was sleeping"),
            ("teach", "Tomorrow we (visit) grandma.", "will visit"), ("teach", "Tomorrow she (fly) to Japan.", "will fly"),
            ("teach", "Next week I (start) a new book.", "will start"), ("teach", "Next week they (move) house.", "will move"),
            ("teach", "The dog (bark) every night.", "barks"), ("teach", "The dogs (bark) every night.", "bark"),
            ("teach", "My cat (sleep) on the sofa every day.", "sleeps"), ("teach", "The cats (sleep) every day.", "sleep"),
            ("teach", "The baby (cry) every night.", "cries"), ("teach", "The babies (cry) every night.", "cry"),
            ("teach", "The boy (eat) rice every day.", "eats"), ("teach", "The boys (eat) rice every day.", "eat"),
            *[("teach", f"word class of {w}", c) for w, c in
              [("careful", "adjective"), ("useful", "adjective"), ("helpful", "adjective"), ("playful", "adjective"),
               ("quickly", "adverb"), ("slowly", "adverb"), ("happily", "adverb"), ("loudly", "adverb"),
               ("kindness", "noun"), ("darkness", "noun"), ("sadness", "noun"), ("goodness", "noun")]],
            *[("teach", f"synonym of {a}", b) for a, b in
              [("angry", "cross"), ("smart", "clever"), ("scared", "afraid"), ("tired", "sleepy"), ("silent", "quiet")]],
            *[("teach", f"opposite of {a}", b) for a, b in
              [("noisy", "quiet"), ("strong", "weak"), ("brave", "afraid"), ("cheap", "expensive"), ("easy", "difficult")]],
        ],
        "exams": [[
            ("comparing: -er", "comparative of long", "longer"), ("comparing: -er", "comparative of pretty", "prettier"),
            ("comparing: -er", "comparative of sad", "sadder"), ("comparing: -er", "comparative of cute", "cuter"),
            ("comparing: -er", "comparative of blick", "blicker"),
            ("comparing: more/most", "comparative of modern", "more modern"),
            ("comparing: more/most", "comparative of delicious", "more delicious"),
            ("superlatives", "superlative of strong", "strongest"), ("superlatives", "superlative of heavy", "heaviest"),
            ("superlatives", "superlative of fat", "fattest"), ("superlatives", "superlative of important", "most important"),
            ("irregular", "comparative of good", "better"), ("irregular", "superlative of bad", "worst"),
            ("adverbs", "adverb of soft", "softly"), ("adverbs", "adverb of noisy", "noisily"), ("adverbs", "adverb of humble", "humbly"),
            ("prefixes", "negative of lucky", "unlucky"), ("prefixes", "negative of clear", "unclear"),
            ("prefixes", "negative of agree", "disagree"),
            ("past continuous", "Tom (run) while it was snowing.", "was running"),
            ("past continuous", "We (sing) when the teacher came in.", "were singing"),
            ("future", "Tomorrow he (paint) the fence.", "will paint"),
            ("agreement", "The horse (jump) every day.", "jumps"), ("agreement", "The horses (jump) every day.", "jump"),
            ("word classes", "word class of thankful", "adjective"), ("word classes", "word class of brightly", "adverb"),
            ("word classes", "word class of weakness", "noun"),
            ("vocabulary", "synonym of clever", "smart"), ("vocabulary", "opposite of weak", "strong"),
        ], [
            ("comparing: -er", "comparative of strong", "stronger"), ("comparing: -er", "comparative of funny", "funnier"),
            ("comparing: -er", "comparative of wet", "wetter"), ("comparing: -er", "comparative of late", "later"),
            ("comparing: -er", "comparative of zatch", "zatcher"),
            ("comparing: more/most", "comparative of colourful", "more colourful"),
            ("comparing: more/most", "comparative of difficult", "more difficult"),
            ("superlatives", "superlative of long", "longest"), ("superlatives", "superlative of pretty", "prettiest"),
            ("superlatives", "superlative of sad", "saddest"), ("superlatives", "superlative of careful", "most careful"),
            ("irregular", "comparative of bad", "worse"), ("irregular", "superlative of good", "best"),
            ("adverbs", "adverb of brave", "bravely"), ("adverbs", "adverb of lucky", "luckily"), ("adverbs", "adverb of polite", "politely"),
            ("prefixes", "negative of able", "unable"), ("prefixes", "negative of fair", "unfair"),
            ("prefixes", "negative of honest", "dishonest"),
            ("past continuous", "She (swim) while the sun was shining.", "was swimming"),
            ("past continuous", "They (talk) when the bell rang.", "were talking"),
            ("future", "Next week we (paint) the room.", "will paint"),
            ("agreement", "The bird (sing) every morning.", "sings"), ("agreement", "The birds (sing) every morning.", "sing"),
            ("word classes", "word class of joyful", "adjective"), ("word classes", "word class of softly", "adverb"),
            ("word classes", "word class of illness", "noun"),
            ("vocabulary", "synonym of afraid", "scared"), ("vocabulary", "opposite of difficult", "easy"),
        ]],
    },
    "integrated": {
        "about": "real-life problems in English: change with dollars and cents, remainders that must be interpreted, "
                 "lengths, durations and areas (several steps)",
        "lessons": [
            ("word", "A book costs $7.85. Sara pays with a $10 note. How much change does she get?", "10-7.85"),
            ("word", "A class of 31 children goes on a trip. Each car takes 4 children. How many cars are needed?", "31 divup 4"),
            ("word", "A garden is 12 m long and 8 m wide. A fence goes all the way round. How long is the fence?", "2*(12+8)"),
        ],
        "exams": [[
            ("money", "A toy costs $13.60. Ben pays with a $20 note. How much change does he get?", "6.4"),
            ("remainders", "There are 45 children. Each boat takes 6 children. How many boats are needed?", "8"),
            ("measurement", "A room is 9 m long and 6 m wide. A border goes all the way round the floor. How long is the border?", "30"),
            ("area", "A carpet is 4 m long and 3 m wide. What is its area in square metres?", "12"),
            ("time", "A train leaves at 10:45 and arrives at 12:10. How long is the journey in minutes?", "85"),
        ], [
            ("money", "A bag costs $26.35. Mia pays with a $30 note. How much change does she get?", "3.65"),
            ("remainders", "There are 38 players. Each team has 5 players. How many full teams can be made?", "7"),
            ("measurement", "A field is 50 m long and 30 m wide. A path goes all the way round. How long is the path?", "160"),
            ("area", "A table top is 2 m long and 1 m wide. What is its area in square metres?", "2"),
            ("time", "A film starts at 6:50 and ends at 8:35. How long is the film in minutes?", "105"),
        ]],
    },
}
