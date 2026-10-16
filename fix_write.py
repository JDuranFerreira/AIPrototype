#!/usr/bin/env python3
"""Fix the write function to ensure v is always a Lin."""

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old = '''def write(sit, clause, target, v):
    if target.startswith("F:"):
        sit.write_first(*clause.cell(target[2:]), v)
    else:
        sit.write(*clause.cell(target), v)'''

new = '''def write(sit, clause, target, v):
    if not isinstance(v, Lin):
        v = Lin(v)
    if target.startswith("F:"):
        sit.write_first(*clause.cell(target[2:]), v)
    else:
        sit.write(*clause.cell(target), v)'''

if old in content:
    content = content.replace(old, new)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fixed write function!")
else:
    print("Pattern not found")
    # Debug: find the write function
    idx = content.find('def write(sit, clause, target, v):')
    if idx >= 0:
        print(content[idx:idx+200])