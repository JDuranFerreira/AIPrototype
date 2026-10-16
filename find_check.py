with open('brainlike/coordination.py', 'r') as f:
    content = f.read()

# Find the exact section
idx = content.index('if op == "i":')
print('Found at:', idx)
print('Content:')
print(repr(content[idx:idx+400]))