import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    lines = f.readlines()

# Remove the duplicate line at index 2337 (0-indexed)
del lines[2337]

with open('brainlike/storyreader.py', 'w') as f:
    f.writelines(lines)

print("Fixed duplicate line!")