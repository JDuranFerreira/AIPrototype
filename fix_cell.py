import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = '''def cell(self, label):
        m = re.fullmatch(r"P(\\d)\\.T(\\d)(?:@D(\\d))?", label.replace("F:", ""))
        i, j, k = int(m[1]) - 1, int(m[2]) - 1, m[3]
        if i >= len(self.P) or j >= len(self.T) or (k and int(k) - 1 >= len(self.D)):
            return None
        noun, adjs = self.T[j]
        adjs = set(adjs)
        # The "F:" prefix in the frame target indicates first-value; we don't add "first" to adjs here
        # because the cell key for first-value uses a special key format handled by write_first
        if k:
            adjs = adjs | {self.D[int(k) - 1]}
        return self.P[i], noun, frozenset(adjs)'''

new_block = '''def cell(self, label):
        m = re.fullmatch(r"(F:)?P(\\d)\\.T(\\d)(?:@D(\\d))?", label)
        is_first = m.group(1) == "F:"
        i, j, k = int(m.group(2)) - 1, int(m.group(3)) - 1, m.group(4)
        if i >= len(self.P) or j >= len(self.T) or (k and int(k) - 1 >= len(self.D)):
            return None
        noun, adjs = self.T[j]
        adjs = set(adjs)
        if is_first:
            adjs = adjs | {"first"}
        if k:
            adjs = adjs | {self.D[int(k) - 1]}
        return self.P[i], noun, frozenset(adjs)'''

with open('brainlike/storyreader.py', 'w') as f:
    f.write(content.replace(old_block, new_block))

print("Fix applied!")