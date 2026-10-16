import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import _CHANGE_EVENT, _IN_VERBS, _OUT_VERBS, _FLY_FIX, _FLY_AWAY

# Check the _CHANGE_EVENT condition
print('_CHANGE_EVENT:', _CHANGE_EVENT)
print('Condition with c.nums=[1]:', True and [1])

# Check verb detection
items = [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)]
evverb2 = next((it[1] for it in [('P', 'She', 'girl', True), ('L', 'ate'), ('N', 1), ('T', 'pear', (), True)] if it[1] in _OUT_VERBS or it[1] in _IN_VERBS or (True and it[1] in {'fly', 'flies', 'flown', 'flew', 'flying'})), None)
print('evverb2:', evverb2)

if evverb2 and (evverb2 in _OUT_VERBS or evverb2 in _IN_VERBS or (True and evverb2 in {'fly', 'flies', 'flown', 'flew', 'flying'})):
    print('CHANGE_EVENT branch would be taken')
else:
    print('CHANGE_EVENT branch NOT taken')