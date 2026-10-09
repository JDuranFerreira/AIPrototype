import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import coding
from brainlike.storyreader import Clause, Situation, clauses, perceive, sentences, evaluate
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
coding.teach(mind, lambda *_: None)
reader = mind.language.reading.reader()
lex, frames = reader.lex, reader.frames

def dump(body, stmt):
    sit = Situation(); sit.units = frames.units
    sents = sentences(body + " " + stmt)
    if getattr(lex, 'CONTEXT', False): lex.read_context(sents)
    for toks in sents[:-1]:
        for items in clauses(perceive(toks, lex, sit)):
            frames.apply(Clause(items, sit), sit)
    print('cells before:', {k: str(v[0]) for k, v in sit.cells.items()})
    s = sentences(stmt)[0]
    for items in clauses(perceive(s, lex, sit)):
        c = Clause(items, sit)
        atoms = c.atoms(sit)
        print('clause:', c.text(), 'owners:', c.owners, 'atoms:', {k: str(v) for k,v in atoms.items()})
        for lb in c.labels():
            print('  ', lb, '->', c.cell(lb))
        for x in frames.candidates('S', c, atoms)[:12]:
            v = evaluate(x['expr'], atoms)
            print(f"  c={x['c']:.2f} r={x['rank']} key={x['key']:<10} tgt={x['target']:<8} expr={x['expr']:<14} v={v} cell={c.cell(x['target'].replace('F:',''))}")

print('### A: total people known, per-car rate stated')
dump("There are 253 people.", "Each car holds 5 people.")
print()
print('### B: num boxes known, per-box rate stated')
dump("There are 8 boxes.", "Each box holds 7 pencils.")
print()
print('### C: rate first, then total (order swapped)')
dump("Each car holds 5 people.", "There are 253 people.")
