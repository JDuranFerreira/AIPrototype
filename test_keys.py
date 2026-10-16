import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'Ema received 5 flowers after lunch'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), sit)

for ci in clauses(items, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    print('Clause keys:', c.keys())
    
    # Check each key
    for rank, k in c.keys():
        e = frames.table['S'].get(k)
        if e:
            print('Key ' + k + ' (rank ' + str(rank) + '): n=' + str(e['n']))
            for expr, count in e['m'].items():
                print('  ' + expr + ': ' + str(count))
        else:
            print('Key ' + k + ' (rank ' + str(rank) + '): NOT FOUND')