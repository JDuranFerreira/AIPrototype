import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'Kim had some pears'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), Situation())

for ci in clauses(items, mind.language.reading.lexicon(), Situation()):
    c = Clause(ci, Situation())
    atoms = c.atoms(Situation())
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    done = frames.apply(c, Situation())
    print('Done:', done)
    if done:
        print('  done[0][value]:', done[0]['value'])
        if hasattr(done[0]['value'], 'known'):
            print('  done[0][value].known:', done[0]['value'].known)