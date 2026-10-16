import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind
from brainlike.storyreader import Situation

# Monkey-patch Situation.write to debug bound changes
original_write = Situation.write

def debug_write(self, owner, thing, desc, new):
    print(f'DEBUG write: owner={owner}, thing={thing}, desc={desc}, new={new}')
    print(f'  bound before: {self.bound}')
    result = original_write(self, owner, thing, desc, new)
    print(f'  bound after: {self.bound}')
    return result

Situation.write = debug_write

from brainlike.regions import Mind

mind = Mind.load('brain_state')
reader = mind.language.reading.reader()

text = 'Kim wins some apples on friday. She wins 2 more apples on monday. If she wins a total of 15 apples, how many apples did Kim win on friday?'
print('Text:', text)

got, how, trace = reader.solve(text)
print('Answer:', got)
print('How:', how)