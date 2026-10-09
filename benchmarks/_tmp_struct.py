import sys
sys.path.insert(0, r'C:\AIAccess\Projects\AIPrototype')
from brainlike.regions import Mind
from brainlike import coding
from brainlike.storyreader import Clause, Situation, clauses, perceive, sentences
mind = Mind.load(r'C:\AIAccess\Projects\AIPrototype\brain_state')
coding.teach(mind, lambda *_: None)
reader = mind.language.reading.reader()
lex, frames = reader.lex, reader.frames
sit = Situation(); sit.units = frames.units
s0 = sentences("There are 253 people.")[0]
for items in clauses(perceive(s0, lex, sit)):
    frames.apply(Clause(items, sit), sit)
print("cells:", {k: str(v[0]) for k, v in sit.cells.items()})
sents = sentences("Each car holds 5 people.")
if getattr(lex, 'CONTEXT', False): lex.read_context(sentences("There are 253 people. Each car holds 5 people."))
for toks in sents:
    for items in clauses(perceive(toks, lex, sit)):
        print("items:", items)
        c = Clause(items, sit)
        print("P:", c.P, "T:", c.T, "nums:", c.nums)
        for lb in c.labels():
            print(f"  {lb} -> cell={c.cell(lb)} sit.read={sit.read(*c.cell(lb))}")
        print("atoms:", {k: str(v) for k, v in c.atoms(sit).items()})
