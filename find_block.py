import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

idx = content.find('Direct computation for')
if idx >= 0:
    print('Found at:', idx)
    print(content[idx:idx+500])
else:
    print('Not found')
    for term in ['Direct computation', 'total X', 'known day']:
        idx = content.find(term)
        if idx >= 0:
            print(f'Found "{term}" at {idx}')