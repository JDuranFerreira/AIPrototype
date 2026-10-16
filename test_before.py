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
# Find the 'beginning' story
for i in range(40):
    t = teller.tale('unknown')
    if 'Kim had some pears' in t.text():
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
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    # Check before question logic
    from brainlike.storyreader import _BEFORE_FIX, _BEFORE_Q, _NO_BEFORE_Q, counts_thing
    import re
    if _BEFORE_FIX and re.search(r'[a-z]+', c.text()):
        words = set(re.findall(r'[a-z]+', c.text().lower()))
        print('words:', words)
        print('_BEFORE_Q intersection:', words & _BEFORE_Q)
        print('_NO_BEFORE_Q intersection:', words & _NO_BEFORE_Q)
        if words & _BEFORE_Q and not words & _NO_BEFORE_Q:
            print('BEFORE QUESTION TRIGGERED')
            for name in atoms:
                if name.startswith('F:') and name[2:] in atoms:
                    base = name[2:]
                    print('  Found F: name=' + name + ', base=' + base)
                    print('  base.startswith(N,K): ' + str(base.startswith(('N', 'K'))))
                    a, b = atoms[base], atoms[name]
                    print('  a=' + str(a) + ', b=' + str(b))
                    print('  a.known=' + str(a.known) + ', b.known=' + str(b.known))
                    print('  a.c=' + str(a.c) + ', b.c=' + str(b.c))
                    print('  a.c == b.c: ' + str(a.c == b.c))
                    
                    from brainlike.storyreader import counts_thing
                    thing = 'pear'
                    print('  counts_thing(name): ' + str(counts_thing(c, name, 'pear')))
                    
                    # Check if candidate would be added
                    print('Would add candidate with expr=' + name)