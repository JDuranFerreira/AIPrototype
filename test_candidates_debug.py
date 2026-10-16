import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'She had 10 candies at first'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), sit)

for ci in clauses(items, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    print('Clause:', c.text())
    print('  sig:', c.sig)
    print('  keys:', c.keys())
    
    atoms = c.atoms(sit)
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    cands = frames.candidates('S', c, atoms, sit)
    print('Total candidates:', len(cands))
    for cand in cands:
        print('  Candidate:', cand)