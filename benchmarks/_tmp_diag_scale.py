import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import storyreader as sr
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
reader = mind.language.reading.reader()
lex, frames = reader.lex, reader.frames
sit = sr.Situation(); sit.units = frames.units
sents = sr.sentences("There are 253 people.")
if getattr(lex,'CONTEXT',False): lex.read_context(sents)
for toks in sents:
    for items in sr.clauses(sr.perceive(toks, lex, sit)):
        frames.apply(sr.Clause(items, sit), sit)
print('cells after first:', {k: str(v[0]) for k,v in sit.cells.items()})
print('P persons:', sit.people, 'subject:', sit.subject, 'thing:', sit.thing)
s2 = sr.sentences("Each car holds 5 people.")
if getattr(lex,'CONTEXT',False): lex.read_context(sr.sentences("There are 253 people. Each car holds 5 people."))
for toks in s2:
    for items in sr.clauses(sr.perceive(toks, lex, sit)):
        print('items:', items)
        c = sr.Clause(items, sit)
        print('P:', c.P, 'T:', c.T, 'things:', c.things, 'persons:', c.persons, 'nums:', [str(n) for n in c.nums])
        print('labels->cell:')
        for lb in c.labels():
            print('  ', lb, c.cell(lb))
        atoms = c.atoms(sit)
        print('atoms:', {k: str(v) for k,v in atoms.items()})
        for x in frames.candidates('S', c, atoms)[:8]:
            tgt = x['target']; expr = x['expr']
            print(f"  key={x['key']} tgt={tgt} expr={expr} self_owned={sr._self_owned(c,tgt)} scales={sr._scales_content_total(c,tgt,expr)}")
            # manual breakdown
            import re
            m = sr._EXPR.match(expr)
            if m and m[3]=='*':
                lab = tgt.replace('F:','')
                cell = c.cell(lab) if re.fullmatch(r'P\d\.T\d(?:@D\d)?', lab) else None
                print('     target cell:', cell)
                others=[a for a in sr.uses(expr) if not re.fullmatch(r'N\d+', a)]
                print('     others:', others, [c.cell(o.replace('F:','')) if re.fullmatch(r'(?:F:)?P\d\.T\d(?:@D\d)?', o) else None for o in others])
                owner = cell[1] if cell and cell[0] is None else None
                if owner:
                    contents={cc[1] for lb2 in c.labels() for cc in (c.cell(lb2),) if cc and cc[0]==owner and cc[1]!=owner}
                    print('     owner:', owner, 'contents:', contents)
