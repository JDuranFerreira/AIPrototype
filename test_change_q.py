import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.stories import Storyteller
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin, _DELTA_Q, _NO_DELTA_Q, _CHANGE_FIX, _CHANGE_FIX_DELTA
import re

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
    for ci in clauses(items, lex, sit):
        c = Clause(ci, sit)
        if c.nums:
            done = frames.apply(c, sit)

q_sent = t.text().split('. ')[-1].strip()
q_toks = q_sent.split()
from brainlike.storyreader import split_question
q = split_question(q_toks)

items = perceive(q[1], mind.language.reading.lexicon(), sit)
for ci in clauses(items, lex, sit):
    c = Clause(ci, sit)
    atoms = c.atoms(sit, question=True)
    print('Atoms:', {k: str(v) for k, v in atoms.items()})
    
    # Check the change question logic
    words = set(re.findall(r'[a-z]+', c.text().lower()))
    print('words:', words)
    print('_DELTA_Q intersection:', words & _DELTA_Q)
    print('_NO_DELTA_Q intersection:', words & _NO_DELTA_Q)
    
    if (_CHANGE_FIX or _CHANGE_FIX_DELTA) and re.search(r'[a-z]+', c.text()):
        words = set(re.findall(r'[a-z]+', c.text().lower()))
        if words & _DELTA_Q and not words & _NO_DELTA_Q:
            print('CHANGE QUESTION TRIGGERED!')
        else:
            print('CHANGE QUESTION NOT triggered')