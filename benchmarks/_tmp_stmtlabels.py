import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import coding
from brainlike.storyreader import Clause, Situation, clauses, perceive, sentences
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
    print('cells before stmt:', {k: str(v[0]) for k, v in sit.cells.items()})
    s = sentences(stmt)[0]
    for items in clauses(perceive(s, lex, sit)):
        c = Clause(items, sit)
        print('items:', c.items)
        print('P:', c.P, 'T:', c.T, 'nums:', c.nums)
        print('persons:', c.persons, 'things:', c.things, 'owners:', c.owners)
        print('text:', c.text(), 'sig:', c.sig)
        print('keys:', c.keys()[:6])
        for lb in c.labels():
            print('  label', lb, '-> cell', c.cell(lb), 'sit.read=', sit.read(*c.cell(lb)))
        print('atoms:', {k: str(v) for k, v in c.atoms(sit).items()})

print('### case A: each car holds 5 people (total people known)')
dump("There are 253 people.", "Each car holds 5 people.")
print()
print('### case B: 7 pencils in each (num boxes known)')
dump("There are 8 boxes.", "There are 7 pencils in each box.")
