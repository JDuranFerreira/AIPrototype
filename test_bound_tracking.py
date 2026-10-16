import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.storyreader import Situation

# Wrap the bound dict to track modifications
class TrackingDict(dict):
    def __setitem__(self, key, value):
        import traceback
        print(f'DEBUG bound[{key}] = {value}')
        traceback.print_stack(limit=10)
        super().__setitem__(key, value)
    
    def __delitem__(self, key):
        import traceback
        print(f'DEBUG bound del {key}')
        traceback.print_stack(limit=10)
        super().__delitem__(key)

original_init = Situation.__init__

def debug_init(self):
    original_init(self)
    self.bound = TrackingDict()

Situation.__init__ = debug_init

from brainlike.regions import Mind

mind = Mind.load('brain_state')
reader = mind.language.reading.reader()

text = 'Kim wins some apples on friday. She wins 2 more apples on monday. If she wins a total of 15 apples, how many apples did Kim win on friday?'
print('Text:', text)

got, how, trace = reader.solve(text)
print('Answer:', got)