import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin, _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY, _self_owned, _scales_content_total

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
    for i, cand in enumerate(cands):
        print('  Candidate {}: key={}, rank={}, c={}, target={}, expr={}'.format(i, cand['key'], cand['rank'], cand['c'], cand['target'], cand['expr']))
    
    # Now trace through apply step by step
    atoms = c.atoms(Situation())
    cands = frames.candidates('S', c, atoms, Situation())
    print('Initial cands:', len(cands))
    
    # Check _CHANGE_EVENT block
    if True and [1]:
        print('_CHANGE_EVENT branch')
        evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in _OUT_VERBS or it[1] in _IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
        print('evverb2:', evverb2)
        cands = frames.candidates('S', c, atoms, Situation())
        print('cands before CHANGE_EVENT:', len(cands))
        if cands:
            evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in _OUT_VERBS or it[1] in _IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
            if evverb2 and (evverb2 in _OUT_VERBS or evverb2 in _IN_VERBS or (True and evverb2 in {'fly', 'flies', 'flown', 'flew', 'flying'})) and cands[0]:
                print('CHANGE_EVENT inner branch taken')
                evcell2 = cands[0]['target'].replace('F:', '')
                print('evcell2:', evcell2)
                evkey2 = c.cell(evcell2) if not evcell2.startswith('F:') else None
                print('evkey2:', evkey2)
                if evkey2 in {}:  # sit.events
                    print('evkey2 in sit.events')
                else:
                    print('evkey2 NOT in sit.events')
                    evacc = evcell2 + '+N1'
                    print('evacc:', evacc)
                    evhave = next((i for i, x in enumerate(cands) if x['expr'] == evacc and x['target'] == cands[0]['target']), None)
                    print('evhave:', evhave)
                    if evhave is None:
                        print('Would insert new candidate at front')
    
    # Check cands after CHANGE_EVENT
    cands = frames.candidates('S', c, atoms, Situation())
    print('cands after CHANGE_EVENT:', len(cands))
    
    # Check _CHANGE_FIX block
    if (True or False) and [1]:  # _CHANGE_FIX or _CHANGE_FIX_VERB
        print('_CHANGE_FIX block')
        verb = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in _OUT_VERBS or it[1] in _IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
        print('verb:', verb)
        if verb and cands[0] and True:  # re.fullmatch(r"N\d+", cands[0]["expr"])
            sign = "-" if verb in _OUT_VERBS or (True and verb in {'fly', 'flies', 'flown', 'flew', 'flying'}) else "+"
            print('sign:', sign)
            cell = cands[0]['target'].replace('F:', '')
            print('cell:', cell)
            expr = '{}N1'.format(cell)
            print('expr:', expr)
    
    # Check self_owned filter
    print('\\nFiltering by _self_owned and _scales_content_total:')
    filtered = [x for x in frames.candidates('S', Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), atoms, Situation()) if not _self_owned(Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), x["target"]) and not _scales_content_total(Clause(clauses(perceive('She ate 1 pear'.split(), mind.language.reading.lexicon(), Situation()), mind.language.reading.lexicon(), Situation())[0], Situation()), x["target"], x["expr"])]
    print('Filtered candidates:', len(filtered))
    for cand in filtered:
        print('  Candidate:', filtered)