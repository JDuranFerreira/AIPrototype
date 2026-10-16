import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.stories import Storyteller
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

teller = Storyteller(seed=99)
t = teller.tale('unknown')
print('Story:', t.text())

sit = Situation()
sit.units = frames.units

for sent in t.text().split('. '):
    sent = sent.strip()
    if not sent:
        continue
    toks = sent.split()
    items = perceive(toks, mind.language.reading.lexicon(), sit)
    print('Sentence:', sent)
    print('Items:', items)
    for ci in clauses(items, mind.language.reading.lexicon(), sit):
        c = Clause(ci, sit)
        print('  Clause:', c.text())
        print('  nums:', c.nums)
        if c.nums:
            done = frames.apply(c, sit)
            print('  done:', done)
        print('  sit.cells:', sit.cells)
        print('  sit.bound:', sit.bound)
        print()

# Question
q_sent = t.text().split('. ')[-1].strip()
q_toks = q_sent.split()
from brainlike.storyreader import split_question
q = split_question(q_toks)
print('q:', q)

items = perceive(q[1], mind.language.reading.lexicon(), sit)
for ci in clauses(items, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    print('Question clause:', c.text())
    print('  nums:', c.nums)
    print('  sig:', c.sig)
    
    atoms = c.atoms(sit, question=True)
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    cands = frames.candidates('Q', c, atoms, sit)
    print('Total candidates:', len(cands))
    for cand in cands:
        print('  Candidate:', cand)