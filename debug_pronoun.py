import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind

mind = Mind.load('brain_state')
frames = mind.language.reading.frames

w = 'him'
p = frames.pron.get(w)
print('p:', p)

if p:
    n = p['n']
    for g in ('boy', 'girl', 'thing'):
        val = p.get(g, 0)
        ratio = val / n if n > 0 else 0
        threshold = 0.9 if g != 'thing' else 0.85
        others_ok = all(p.get(o, 0) / n <= 0.5 for o in ('boy', 'girl', 'thing') if o != g)
        print(g + ': ' + str(val) + '/' + str(n) + '=' + str(val/n) + ' >= ' + str(threshold) + '=' + str(ratio >= threshold) + ', others_ok=' + str(others_ok))
        if ratio >= threshold and others_ok:
            print('  -> returns ' + g)
            break