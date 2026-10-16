#!/usr/bin/env python3
"""Fix the candidates method to add stative candidates before sorting."""

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old = '''            out.append({"rank": rank, "c": c, "n": chances, "key": k, "target": target, "expr": expr})
        plain = lambda x: len(uses(x["expr"])) + x["expr"].startswith("(") + ("2" in x["expr"].replace("N2", "")) + ("~" in x["expr"]) + \
            any(o in x["expr"] for o in _RULED) + (len(set(uses(x["expr"]))) < len(uses(x["expr"])))
        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
        if not clause.nums and self.WORDLESS:
            for label in labels:
                if label in atoms and atoms[label].known:
                    out.append({"rank": 1, "c": 0.5, "n": 0, "key": "stative", "target": label, "expr": label})
        return out'''

new = '''        out.append({"rank": rank, "c": c, "n": chances, "key": k, "target": target, "expr": expr})
        plain = lambda x: len(uses(x["expr"])) + x["expr"].startswith("(") + ("2" in x["expr"].replace("N2", "")) + ("~" in x["expr"]) + \
            any(o in x["expr"] for o in _RULED) + (len(set(uses(x["expr"]))) < len(uses(x["expr"])))
        # For WORDLESS clauses (no numbers): add "no change" candidate if the label value matches
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