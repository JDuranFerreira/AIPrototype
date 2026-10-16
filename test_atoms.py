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
# Find the specific failing story
for i in range(40):
    t = teller.tale('unknown')
    if 'boarded some more' in t.text() and 'In the end she has 20' in t.text():
        print('Story:', t.text())
        break

sit = Situation()
sit.units = frames.units

for sent in t.text().split('. '):
    sent = sent.strip()
    if not sent:
        continue
    toks = sent.split()
    items = perceive(toks, mind.language.reading.lexicon(), sit)
    for ci in clauses(items, mind.language.reading.lexicon(), sit):
        c = Clause(ci, sit)
        if c.nums:
            done = frames.apply(c, sit)

q_sent = t.text().split('. ')[-1].strip()
q_toks = q_sent.split()
from brainlike.storyreader import split_question
q = split_question(q_toks)

items = perceive(q[1], mind.language.reading.lexicon(), sit)
for ci in clauses(items, mind.language.reading.lexicon(), sit):
    c = Clause(ci, sit)
    
    atoms = c.atoms(sit, question=True)
    
    # Check the change question logic manually
    for name in atoms:
        if name.startswith('F:') and name[2:] in atoms:
            base = name[2:]
            print('Found F: name=' + name + ', base=' + base)
            print('  base in atoms: ' + str(base in atoms))
            print('  base.startswith(N,K): ' + str(base.startswith(('N', 'K'))))
            
            cell = c.cell(base)
            print('  clause.cell(' + base + ') = ' + str(cell))
            print('  cell in sit.events: ' + str(cell in sit.events if cell else False))
            
            a = atoms[base]
            b = atoms[name]
            print('  a=' + str(a) + ', b=' + str(b))
            print('  a.known=' + str(a.known) + ', b.known=' + str(b.known))
            print('  a.c=' + str(a.c) + ', b.c=' + str(b.c))
            print('  a.c == b.c: ' + str(a.c == b.c))