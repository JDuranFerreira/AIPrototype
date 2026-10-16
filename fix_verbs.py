with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Replace the _VERB_WORDS, _OUT_VERBS, _IN_VERBS sections
old = """_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
               "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
               "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
               "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
               "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
               "flew", "added", "gained", "read"}
_OUT_VERBS = {"sold", "gave", "gaveaway", "lost", "ate", "used", "spent", "removed", "deleted",
              "finished", "read", "filled", "threw", "took", "taken", "eaten"}
_IN_VERBS = {"bought", "got", "received", "collected", "picked", "found", "brought"}"""

new = """_VERB_WORDS = {"is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got",
               "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken",
               "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown",
               "gave", "given", "took", "received", "collected", "gets", "has", "have", "had",
               "does", "did", "do", "filled", "gaveaway", "deleted", "finished", "cooked", "grew",
               "flew", "added", "gained", "read", "board"}
_OUT_VERBS = {"sold", "gave", "gaveaway", "lost", "ate", "used", "spent", "removed", "deleted",
              "finished", "read", "filled", "threw", "took", "taken", "eaten"}
_IN_VERBS = {"bought", "got", "received", "collected", "picked", "found", "brought", "board"}"""

if old in content:
    content = content.replace(old, new)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print('Replacement done')
else:
    print('Old text not found')
    # Let's find what's there
    idx = content.find('_VERB_WORDS')
    if idx >= 0:
        print('Found at:', idx)
        print(content[idx:idx+500])