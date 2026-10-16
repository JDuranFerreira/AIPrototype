#!/usr/bin/env python3
"""Fix the owners logic in Clause constructor."""

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Fix the owners logic in Clause constructor
old = '''                is_counted = len(it) == 4 and it[3]
                # Only uncounted things can be owners (e.g., 'a pen costs 3 dollars' - pen owns cost)
                # Counted things are the things being counted, not owners
                if not is_counted:
                    self.owners.append(it[1])
                if it is first_slot and not is_counted and \\
                        not any(x[0] == "L" and x[1] in ("each", "every", "there") for x in items[:3]):
                    sit.mention(it[1], "thing")
                    self.thing_subject = it[1]'''

new = '''                is_counted = len(it) == 4 and it[3]
                # Only uncounted things in non-WORDLESS clauses can be owners
                # (e.g., 'a pen costs 3 dollars' - pen owns cost). 
                # In WORDLESS clauses (no numbers), things are typically subjects, not owners.
                if not is_counted and not self.WORDLESS:
                    self.owners.append(it[1])
                if it is first_slot and not is_counted and \\
                        not any(x[0] == "L" and x[1] in ("each", "every", "there") for x in items[:3]):
                    sit.mention(it[1], "thing")
                    self.thing_subject = it[1]'''

if old in content:
    content = content.replace(old, new)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fixed owners logic!")
else:
    print("Old text not found")