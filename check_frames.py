import sys
sys.stdout.reconfigure(encoding='utf-8')
from brainlike.regions import Mind

mind = Mind.load('brain_state')
frames = mind.language.reading.frames

# Check frames for verbs that are failing
verbs = ['ate', 'made', 'received', 'dropped', 'broke', 'boarded', 'collected', 'subtracts']
for verb in verbs:
    found = False
    for k, v in mind.language.reading.frames.table.get('S', {}).items():
        if verb in k:
            print(verb + ' in ' + k + ': n=' + str(v['n']))
            for expr, count in v['m'].items():
                print('  ' + expr + ': ' + str(count))
            break
    else:
        print(verb + ': NOT FOUND in frames')
    print()