import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind

mind = Mind.load('brain_state')
reader = mind.language.reading.reader()

text = 'Kim wins some apples on friday. She wins 2 more apples on monday. If she wins a total of 15 apples, how many apples did Kim win on friday?'
print('Text:', text)

# Monkey-patch solve to add debug
original_solve = reader.__class__.solve

def debug_solve(self, text, sit=None, override=None):
    from brainlike.storyreader import sentences, split_question, perceive, Clause, clauses, Situation
    sit = sit or Situation()
    sit.units = self.frames.units
    sents = sentences(text)
    print(f'DEBUG: sents = {sents}')
    q = split_question(sents[-1])
    print(f'DEBUG: q = {q}')
    body = sents[:-1] if q else sents
    print(f'DEBUG: body = {body}')
    return original_solve(self, text, sit, override)

reader.__class__.solve = debug_solve

# Call solve
got, how, trace = reader.solve('Kim wins some apples on friday. She wins 2 more apples on monday. If she wins a total of 15 apples, how many apples did Kim win on friday?')
print('Answer:', got)
print('How:', how)
for t in trace:
    print(' ', t)