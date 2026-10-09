import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import storyreader as sr
print('storyreader file:', sr.__file__)
print('has scales fn:', hasattr(sr, '_scales_content_total'))
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
reader = mind.language.reading.reader()
lex, frames = reader.lex, reader.frames
sit = sr.Situation(); sit.units = frames.units
sents = sr.sentences("There are 253 people. Each car holds 5 people.")
if getattr(lex, 'CONTEXT', False): lex.read_context(sents)
for toks in sents:
    for items in sr.clauses(sr.perceive(toks, lex, sit)):
        c = sr.Clause(items, sit)
        atoms = c.atoms(sit)
        cands = frames.candidates('S', c, atoms)
        print('clause:', c.text(), 'ncands:', len(cands))
        for x in cands[:6]:
            print('  ', x['key'], x['target'], x['expr'],
                  'self_owned=', sr._self_owned(c, x['target']),
                  'scales=', sr._scales_content_total(c, x['target'], x['expr']))
        kept = [x for x in cands if not sr._self_owned(c, x['target'])
                and not sr._scales_content_total(c, x['target'], x['expr'])]
        print('  kept best:', (kept[0]['key'], kept[0]['target'], kept[0]['expr']) if kept else None)
        done = frames.apply(c, sit)
        print('  done:', [(d['target'], d['expr'], str(d['value'])) for d in done] if done else None)
        print('  cells:', {k: str(v[0]) for k, v in sit.cells.items()})
