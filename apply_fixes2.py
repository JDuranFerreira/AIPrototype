#!/usr/bin/env python3
"""Apply remaining fixes to storyreader.py"""

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Fix 1: setting function - add WHERE + D (day/time) handling
old_setting = '''    def setting(self):
        """Positions of where/when phrases ('at the park', 'for his birthday', 'in the garden'): they say where
        it happened, not what happened, so they carry no meaning of their own."""
        out, items = set(), self.items
        for i, it in enumerate(items[:-1]):
            nxt = items[i + 1]
            after = items[i + 2] if i + 2 < len(items) else None
            if it[0] == "L" and it[1] in _WHERE and nxt[0] == "L" and nxt[1] in _DET - {"each", "every"} and \
                    not (after and after[0] == "L" and after[1] in _NOT_NOUNS):
                j = i
                while j < len(items) and items[j][0] == "L":
                    out.add(j)
                    j += 1
        return out'''

new_setting = '''    def setting(self):
        """Positions of where/when phrases ('at the park', 'for his birthday', 'in the garden'): they say where
        it happened, not what happened, so they carry no meaning of their own."""
        out, items = set(), self.items
        for i, it in enumerate(items[:-1]):
            nxt = items[i + 1]
            after = items[i + 2] if i + 2 < len(items) else None
            # WHERE + DET + thing ('at the park', 'for his birthday')
            if it[0] == "L" and it[1] in _WHERE and nxt[0] == "L" and nxt[1] in _DET - {"each", "every"} and \
                    not (after and after[0] == "L" and after[1] in _NOT_NOUNS):
                j = i
                while j < len(items) and items[j][0] == "L":
                    out.add(j)
                    j += 1
            # WHERE + day/time ('for winter', 'in summer', 'on monday')
            elif it[0] == "L" and it[1] in _WHERE and nxt[0] == "D":
                j = i
                while j < len(items) and items[j][0] in ("L", "D"):
                    out.add(j)
                    j += 1
        return out'''

content = content.replace(old_setting, new_setting)

# Fix 2: Clause constructor - persons logic (don't add things as persons)
old_persons = '''                    if name and name not in self.persons:
                        self.persons.append(name)'''

new_persons = '''                    if name and name not in self.persons and (it[3] or it[2] != "thing"):
                        self.persons.append(name)'''

content = content.replace(old_persons, new_persons)

# Fix 2b: Clause constructor - owners logic (already done but verify)
# The owners logic at line 920 should be: if not is_counted (already done)

# Fix 3: Clause constructor - P construction for no persons (already done)

# Fix 4: Add None for ownerless statements when there are counted things but no owners
old_none_add = '''        if None not in self.P and len(self.P) < 4 and \\
                any(o is None and t in [n for n, _ in self.things] for o, t, _ in sit.cells):
            self.P = self.P + [None]                   # 'how many days does she need?': and the apples lying there'''

new_none_add = '''        # If there are counted things but no owners and no None owner, add None for ownerless statements
        if self.nums and not self.owners and None not in self.P:
            self.P = [None] + self.P
        if None not in self.P and len(self.P) < 4 and \\
                any(o is None and t in [n for n, _ in self.things] for o, t, _ in sit.cells):
            self.P = self.P + [None]                   # 'how many days does she need?': and the apples lying there'''

content = content.replace(old_none_add, new_none_add)

# Fix 4: last_thing only added when self.nums (not WORDLESS)
old_last_thing = '''        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

new_last_thing = '''        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4 and self.nums:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

content = content.replace(old_last_thing, new_last_thing)

# Fix 4: observe_statement - second location (if exists) - check credit function or elsewhere
# The fix at line 1882 is already applied. Check if there's a second location in credit function.

# Fix 4: observe_statement - second location (in credit function or elsewhere)
# Search for the second occurrence of the stative frames fix
old_observe2 = '''            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            if same:                                          # it says nothing new about now: maybe about the start'''

new_observe2 = '''            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            # Stative sentences (no numbers, WORDLESS): allow learning "no change" frames
            # e.g., "the birds are migrating" -> birds stay the same
            if same and not clause.nums and self.WORDLESS:
                # Allow "no change" frame for stative sentences: label = label
                if label in atoms and atoms[label].c == v.c:
                    pairs.append(f"{label}={label}")
            if same:                                          # it says nothing new about now: maybe about the start'''

content = content.replace(old_observe2, new_observe2)

# Write the modified content
with open('brainlike/storyreader.py', 'w') as f:
    f.write(content)

print("Remaining fixes applied!")