import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Situation

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()

sit = Situation()

# Test 'Sam had $40'
toks = ['Sam', 'had', '$40']
items = perceive(toks, mind.language.reading.lexicon(), sit)
print('Items:', items)

# Debug lex.number
print('lex.number($40):', lex.number('$40'))
print('lex.number($36):', lex.number('$36'))
print('type:', type(lex.number('$40')))