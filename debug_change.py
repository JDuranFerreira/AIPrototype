import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin, _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY

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
    
    # Check candidates
    from brainlike.regions import Mind
    mind = Mind.load('brain_state')
    frames = mind.language.reading.frames
    cands = frames.candidates('S', Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), atoms, Situation())
    print('Total candidates:', len(cands))
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Now simulate the apply function logic
    # Check _CHANGE_EVENT block
    cands = mind.language.reading.frames.candidates('S', Clause(mind.language.reading.storyreader.clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), atoms, Situation())
    print('cands:', cands)
    
    # Check _CHANGE_EVENT block
    print('_CHANGE_EVENT:', _CHANGE_EVENT)
    print('c.nums:', [1])
    if True and [1]:
        print('CHANGE_EVENT branch taken')
        evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in _OUT_VERBS or it[1] in _IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
        print('evverb2:', evverb2)
        if evverb2 and (evverb2 in _OUT_VERBS or evverb2 in _IN_VERBS or (True and evverb2 in {'fly', 'flies', 'flown', 'flew', 'flying'})):
            print('CHANGE_EVENT branch would be taken')
        else:
            print('CHANGE_EVENT branch NOT taken')