import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import coding
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
coding.teach(mind, lambda *_: None)
reader = mind.language.reading.reader()
cases = [
 ("There are 253 people. Each car holds 5 people. How many people are in one car?", "5"),
 ("Each jar has 12 sandwiches. There are 72 jars. How many jars are there?", "72"),
 ("5 pens cost 15 dollars. How many pens cost 15 dollars?", "5"),
 ("There are 253 people. Each car holds 5 people. How many cars do they need?", "51"),
 ("There are 8 boxes with 7 pencils in each. How many boxes are there?", "8"),
]
for text, want in cases:
    a, how, trace = reader.solve(text)
    print(f"want={want:>4} got={a!s:>6}  how={how[:60]}")
    print(f"   {text}")
