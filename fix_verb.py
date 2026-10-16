import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = '''_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
               "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
               "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
               "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
               "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
               "flew", "added", "gained", "read", "fly", "flies", "flew", "flown", "flying"}'''

new_block = '''_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
                "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
                "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
                "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
                "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
                "flew", "added", "gained", "read", "fly", "flies", "flew", "flown", "flying",
                "get"}'''

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fix applied!")
else:
    print("Old block not found!")