import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin, _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY
from brainlike import storyreader

_OUT_VERBS = storyreader._OUT_VERBS
_IN_VERBS = storyreader._IN_VERBS
_FLY_FIX = storyreader._FLY_FIX
_FLY_AWAY = storyreader._FLY_AWAY

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
    
    cands = frames.candidates('S', c, atoms, Situation())
    print('Total candidates:', len(cands))
    
    # Simulate the apply function logic
    # In apply(), atoms = clause.atoms(sit) - this should have N1=1
    atoms = c.atoms(Situation())
    print('Atoms in apply:', {k: str(v) for k, v in atoms.items()})
    
    cands = frames.candidates('S', c, atoms, Situation())
    print('cands from frames.candidates:', len(cands))
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Simulate apply logic
    if True and [1]:  # _CHANGE_EVENT and c.nums
        print('_CHANGE_EVENT branch taken')
        evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in storyreader._OUT_VERBS or it[1] in storyreader._IN_VERBS or (storyreader._FLY_FIX and it[1] in storyreader._FLY_AWAY)), None)
        print('evverb2:', evverb2)
        if evverb2 and (evverb2 in storyreader._OUT_VERBS or evverb2 in storyreader._IN_VERBS or (storyreader._FLY_FIX and evverb2 in storyreader._FLY_AWAY)):
            print('CHANGE_EVENT branch taken')
            cands = frames.candidates('S', Clause(clauses(perceive('She ate 1 pear'.split(), storyreader.lexicon, Situation()), storyreader.lexicon, Situation())[0], Situation()), {}, Situation())
            print('cands:', cands)