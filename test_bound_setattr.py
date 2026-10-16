import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.storyreader import Situation

# Monkey-patch Situation.__setattr__ to track bound changes
original_setattr = Situation.__setattr__

def debug_setattr(self, name, value):
    if name == 'bound':
        import traceback
        print(f'DEBUG bound set: {value}')
        traceback.print_stack(limit=10)
    original_setattr(self, name, value)

Situation.__setattr__ = debug_setattr

from brainlike.regions import Mind

mind = Mind.load('brain_state')
reader = mind.language.reading.reader()

text = 'Kim wins some apples on friday. She wins 2 more apples on monday. If she wins a total of 15 apples, how many apples did Kim win on friday?'
print('Text:', text)

got, how, trace = reader.solve(text)
print('Answer:', got)