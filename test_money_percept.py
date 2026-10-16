import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import perceive, Situation

mind = Mind.load('brain_state')
lex = mind.language.reading.lexicon()

sit = Situation()

# Test money perception
toks = ['Raj', 'had', '$17', 'in', 'his', 'wallet']
items = perceive(toks, mind.language.reading.lexicon(), sit)
print('Items:', items)

# Test with space
toks2 = ['Raj', 'had', '$', '17', 'in', 'his', 'wallet']
items2 = perceive(toks2, mind.language.reading.lexicon(), sit)
print('Items2:', items2)

# Test 'spent'
toks3 = ['spent', '$36', 'on', 'apples']
items3 = perceive(toks3, mind.language.reading.lexicon(), sit)
print('Items3:', items3)

# Test 'got'
toks4 = ['got', '$14']
items4 = perceive(toks4, mind.language.reading.lexicon(), sit)
print('Items4:', items4)

# Test how $ is perceived
print('lex.known($):', lex.known('$'))
print('lex.known($17):', lex.known('$17'))
print('lex.number($17):', lex.number('$17'))
print('lex.number($):', lex.number('$'))