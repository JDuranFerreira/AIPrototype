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
    
    cands = mind.language.reading.frames.candidates('S', c, atoms, Situation())
    print('Total candidates:', len(cands))
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Simulate the _CHANGE_EVENT block
    if _CHANGE_EVENT and c.nums:
        print('_CHANGE_EVENT branch taken')
        evverb2 = next((it[1] for it in c.items if it[1] in mind.language.reading.storyreader._OUT_VERBS or it[1] in mind.language.reading.storyreader._IN_VERBS or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
        print('evverb2:', evverb2)
        if evverb2 and (evverb2 in mind.language.reading.storyreader._OUT_VERBS or evverb2 in mind.language.reading.storyreader._IN_VERBS or (_FLY_FIX and evverb2 in _FLY_AWAY)):
            print('CHANGE_EVENT branch taken')
            # Check cands[0]
            cands = mind.language.reading.frames.candidates('S', c, {}, Situation())
            print('cands:', cands)
            if cands:
                print('cands[0]:', cands[0])
                evcell2 = cands[0]['target'].replace('F:', '')
                print('evcell2:', evcell2)
                evkey2 = c.cell(evcell2) if not evcell2.startswith('F:') else None
                print('evkey2:', evkey2)
                if evkey2 in {}:  # sit.events is empty
                    print('evkey2 not in sit.events')
                    evacc = evcell2 + '+N1'
                    print('evacc:', evacc)
                    evhave = next((i for i, x in enumerate(cands) if x['expr'] == evacc and x['target'] == cands[0]['target']), None)
                    print('evhave:', evhave)
                    if evhave is None:
                        print('Would insert new candidate at front')