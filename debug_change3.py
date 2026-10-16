import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin
from brainlike.storyreader import _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY

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
    
    # Get candidates
    cands = mind.language.reading.frames.candidates('S', c, atoms, Situation())
    print('Total candidates:', len(cands))
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Now simulate the apply function
    atoms = c.atoms(Situation())
    cands = mind.language.reading.frames.candidates('S', c, atoms, Situation())
    print('Total candidates from frames.candidates:', len(cands))
    
    # Simulate the _CHANGE_EVENT block
    if True and [1]:  # _CHANGE_EVENT and c.nums
        print('_CHANGE_EVENT branch taken')
        evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in mind.language.reading.storyreader._OUT_VERBS or it[1] in mind.language.reading.storyreader._IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
        print('evverb2:', evverb2)
        if evverb2 and (evverb2 in mind.language.reading.storyreader._OUT_VERBS or evverb2 in mind.language.reading.storyreader._IN_VERBS or (True and evverb2 in {'fly', 'flies', 'flown', 'flew', 'flying'})):
            print('CHANGE_EVENT branch would be taken')
            # Check cands[0]
            cands = mind.language.reading.frames.candidates('S', Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), Situation().atoms(Situation()), Situation())
            print('cands[0]:', cands[0] if cands else 'None')
            
            # Check the evcell2 logic
            if cands:
                evcell2 = cands[0]['target'].replace('F:', '')
                print('evcell2:', evcell2)
                # Check clause.cell
                from brainlike.storyreader import Clause, clauses, perceive, Situation
                c = Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation())
                evcell2 = cands[0]['target'].replace('F:', '')
                print('evcell2:', evcell2)
                evkey2 = c.cell(evcell2) if not evcell2.startswith('F:') else None
                print('evkey2:', evkey2)
                print('sit.events:', {})
                if evkey2 in {}:
                    print('evkey2 in sit.events')
                else:
                    print('evkey2 NOT in sit.events')
                    evacc = evcell2 + '+N1'
                    print('evacc:', evacc)
                    evhave = next((i for i, x in enumerate(cands) if x['expr'] == evacc and x['target'] == cands[0]['target']), None)
                    print('evhave:', evhave)
                    if evhave is None:
                        print('Would insert new candidate at front')
                    else:
                        print('evhave:', evhave)