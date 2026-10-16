import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.stories import Storyteller
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

teller = Storyteller(seed=99)
for i in range(40):
    t = teller.tale('days')
    if 'Kim wins some apples on friday' in t.text():
        print('Story:', t.text())
        break

sit = Situation()
sit.units = frames.units

# Sentence 1
sent1 = 'Kim wins some apples on friday'
toks1 = sent1.split()
items1 = perceive(toks1, mind.language.reading.lexicon(), sit)
print('Sentence 1:', sent1)
for ci in clauses(items1, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    if c.nums:
        done = frames.apply(c, sit)
    print(f'  sit.bound: {sit.bound}')

print()

# Sentence 2
sent2 = 'She wins 2 more apples on monday'
toks2 = sent2.split()
items2 = perceive(toks2, mind.language.reading.lexicon(), sit)
print('Sentence 2:', sent2)
for ci in clauses(items2, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    if c.nums:
        done = frames.apply(c, sit)
    print(f'  sit.bound: {sit.bound}')

print()
print('Final sit.bound:', sit.bound)
print('sit.cells:', sit.cells)