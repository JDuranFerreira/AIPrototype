import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import coding
from brainlike.storyreader import Clause, Situation, clauses, perceive, sentences, split_question, singular
from brainlike.request import what_is_asked
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
coding.teach(mind, lambda *_: None)
reader = mind.language.reading.reader()
lex, frames = reader.lex, reader.frames
text = "There are 253 people. Each car holds 5 people. How many cars do they need?"
sit = Situation(); sit.units = frames.units
sents = sentences(text)
if getattr(lex, 'CONTEXT', False): lex.read_context(sents)
q = split_question(sents[-1])
for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
    for items in clauses(perceive(toks, lex, sit)):
        frames.apply(Clause(items, sit), sit)
print('sit cells:', {k: str(v[0]) for k, v in sit.cells.items()})
c = Clause(perceive(q[1], lex, sit), sit)
print('q text:', c.text())
print('items:', c.items)
print('P:', c.P, 'T:', c.T)
print('persons:', c.persons, 'things:', c.things, 'nums:', c.nums, 'owners:', c.owners)
atoms = c.atoms(sit, question=True)
print('atoms:', {k: str(v) for k, v in atoms.items()})
for lab in sorted(atoms):
    try:
        print(f'  {lab} -> cell={c.cell(lab.replace("F:",""))} value={atoms[lab]}')
    except Exception as e:
        print(f'  {lab} -> ERROR {e}')
asked = what_is_asked(c.text())
print('asked:', asked)
