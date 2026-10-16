import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind

mind = Mind.load('brain_state')
frames = mind.language.reading.frames

# Check first frames
for key in ['first|PNT_', 'first|*']:
    e = frames.table['S'].get(key)
    if e:
        print(key + ': n=' + str(e['n']))
        for expr, count in e['m'].items():
            print('  ' + expr + ': ' + str(count))
    else:
        print(key + ': NOT FOUND')