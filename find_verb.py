with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

idx = content.find('_VERB_WORDS = {"is"')
print(content[idx:idx+500])