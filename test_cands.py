import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'Ema received 5 flowers after lunch'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), Situation())

for ci in clauses(items, mind.language.reading.lexicon(), Situation()):
    c = Clause(ci, Situation())
    atoms = c.atoms(Situation())
    cands = frames.candidates('S', c, atoms, Situation())
    print('Total candidates:', len(cands))
    for i, cand in enumerate(cands[:5]):
        print('  Candidate ' + str(i) + ': key=' + cand['key'] + ', rank=' + str(cand['rank']) + ', c=' + str(cand['c']) + ', target=' + cand['target'] + ', expr=' + cand['expr'])