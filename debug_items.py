import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Clause, clauses, Situation, Lin

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()
frames = mind.language.reading.frames

sit = Situation()
sit.units = frames.units

sent = 'She ate 1 pear'
toks = sent.split()
items = perceive(toks, mind.language.reading.lexicon(), Situation())

for ci in clauses(items, mind.language.reading.lexicon(), Situation()):
    c = Clause(ci, Situation())
    print('c.items:', c.items)
    print('c.nums:', c.nums)
    
    from brainlike.storyreader import _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY
    
    evverb2 = next((it[1] for it in c.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                    or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
    print('evverb2:', evverb2)
    print('c.nums:', c.nums)
    print('_CHANGE_EVENT:', _CHANGE_EVENT)
    print('Condition:', _CHANGE_EVENT and c.nums)