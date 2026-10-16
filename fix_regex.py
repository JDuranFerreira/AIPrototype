#!/usr/bin/env python3
"""Fix using regex."""

import re

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Fix the owners logic - use regex to handle whitespace variations
old_pattern = r'(is_counted = len\(it\) == 4 and it\[3\]\n\s+# Only uncounted things can be owners \(e\.g\., \'a pen costs 3 dollars\' - pen owns cost\)\n\s+# Counted things are the things being counted, not owners\n\s+if not is_counted:\n\s+self\.owners\.append\(it\[1\]\))'

new = '''is_counted = len(it) == 4 and it[3]
                # Only uncounted things in non-WORDLESS clauses can be owners
                # (e.g., 'a pen costs 3 dollars' - pen owns cost). 
                # In WORDLESS clauses (no numbers), things are typically subjects, not owners.
                if not is_counted and not self.WORDLESS:
                    self.owners.append(it[1])'''

content = re.sub(old_pattern, new, content)

# Also fix the Clause constructor - add self.WORDLESS initialization
# Find the Clause __init__ and add self.WORDLESS = True after self.owners initialization
old_init = r'(self\.persons, self\.things, self\.days, self\.nums, self\.owners = \[\], \[\], \[\], \[\], \[\])'
new_init = r'\1\n        self.WORDLESS = True'

content = re.sub(old_init, new_init, content)

with open('brainlike/storyreader.py', 'w') as f:
    f.write(content)

print("Regex fixes applied!")