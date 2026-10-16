import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units
sit.cells = {(None, 'bird', frozenset()): [10, 10]}
sit.thing = ('bird', ())

toks = ['how', 'many', 'bird', 'are', 'flying', 'south', 'for', 'winter']
items = __import__('brainlike.storyreader', fromlist=['perceive']).perceive(toks, mind.language.reading.lexicon(), Situation())

for ci in __import__('brainlike.storyreader', fromlist=['clauses']).clauses(items, mind.language.reading.lexicon(), Situation()):
    c = Clause(ci, Situation())
    print('Clause:', c.text())
    print('  P:', c.P)
    print('  T:', c.T)
    print('  nums:', c.nums)
    print('  sig:', c.sig)
    print('  labels:', list(c.labels()))
    
    for label in c.labels():
        key = c.cell(label)
        print(f'  label {label} -> cell {key}')
        if key:
            print(f'  in sit.cells: {key in {(None, "bird", frozenset()): [10, 10]}}')
            if key in {(None, 'bird', frozenset()): [10, 10]}:
                val = {(None, 'bird', frozenset()): [10, 10]}[key]
                print(f'  value: {val} (type: {type(val[1]).__name__})')
                if hasattr(val[1], 'known'):
                    print(f'    known: {val[1].known}')