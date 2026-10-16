#!/usr/bin/env python3
"""Fix the candidates method - move stative candidate before sort."""

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old = '''        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
        if not clause.nums and self.WORDLESS:
            for label in labels:
                if label in atoms and atoms[label].known:
                    out.append({"rank": 1, "c": 0.5, "n": 0, "key": "stative", "target": label, "expr": label})
        return out'''

new = '''        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
        if not clause.nums and self.WORDLESS:
            for label in labels:
                if label in atoms and atoms[label].known:
                    out.append({"rank": 1, "c": 0.5, "n": 0, "key": "stative", "target": label, "expr": label})
        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        return out'''

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old = '''        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
        if not clause.nums and self.WORDLESS:
            for label in labels:
                if label in atoms and atoms[label].known:
                    out.append({"rank": 1, "c": 0.5, "n": 0, "key": "stative", "target": label, "expr": label})
        return out'''

new = '''        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
        if not clause.nums and self.WORDLESS:
            for label in labels:
                if label in atoms and atoms[label].known:
                    out.append({"rank": 1, "c": 0.5, "n": 0, "key": "stative", "target": label, "expr": label})
        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        return out'''

if old in content:
    content = content.replace(old, new)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fixed candidates sorting!")
else:
    print("Pattern not found")
    # Debug: show the relevant section
    idx = content.find('out.sort(key=lambda x: (-round(x["c"], 2)')
    if idx >= 0:
        print(content[idx:idx+500])