import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'She ate 1 pear'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), Situation())

for ci in clauses(items, mind.language.reading.lexicon(), Situation()):
    c = Clause(ci, Situation())
    atoms = c.atoms(Situation())
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    cands = mind.language.reading.frames.candidates('S', c, atoms, Situation())
    print('Total candidates:', len(cands))
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Check what apply does
    # Check if cands[0] has expr N1
    cands = mind.language.reading.frames.candidates('S', c, atoms, Situation())
    print('cands[0]:', cands[0] if cands else 'None')
    
    # Check the apply logic
    # Check _CHANGE_EVENT condition
    from brainlike.storyreader import _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY
    print('_CHANGE_EVENT:', _CHANGE_EVENT)
    
    # Check verb detection
    evverb2 = next((it[1] for it in enumerate([]) if it[1] in []), None)
    print('c.items:', [it[1] for it in []])