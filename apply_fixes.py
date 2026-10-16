#!/usr/bin/env python3
"""Apply all fixes to storyreader.py for migration story support."""

import re

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Fix 1: T tuple creation in perceive - add 4th element False for uncounted nouns
content = content.replace(
    'out.append(("T", singular(w), tuple(sorted(adjs))))',
    'out.append(("T", singular(w), tuple(sorted(adjs)), False))'
)

# Fix 2: Clause constructor - fix owners logic (use is_counted instead of len < 4)
old_clause_t = '''            elif it[0] == "T" and (it[1], it[2]) not in self.things:
                self.things.append((it[1], it[2]))
                if len(it) < 4:                              # a thing not counted here can own things
                    self.owners.append(it[1])
                if it is first_slot and len(it) < 4 and \\
                        not any(x[0] == "L" and x[1] in ("each", "every", "there") for x in items[:3]):
                    sit.mention(it[1], "thing")              # 'the game starts ...': a thing the story is about
                    self.thing_subject = it[1]'''

new_clause_t = '''            elif it[0] == "T" and (it[1], it[2]) not in self.things:
                self.things.append((it[1], it[2]))
                is_counted = len(it) == 4 and it[3]
                # Only uncounted things can be owners (e.g., 'a pen costs 3 dollars' - pen owns cost)
                # Counted things are the things being counted, not owners
                if not is_counted:
                    self.owners.append(it[1])
                if it is first_slot and not is_counted and \\
                        not any(x[0] == "L" and x[1] in ("each", "every", "there") for x in items[:3]):
                    sit.mention(it[1], "thing")              # 'the game starts ...': a thing the story is about
                    self.thing_subject = it[1]'''

content = content.replace(old_clause_t, new_clause_t)

# Fix 3: Clause constructor - fix P construction for no persons (don't add thing as subject)
old_p_construction = '''        # owners: the people in the clause, then the things it names (things can own things: 'a pen costs 3
        # dollars'); with no people, the one the story is about comes last ('each bag has 4 apples' -> Tom's)
        if self.persons:
            self.P = (self.persons[:2] + [n for n in self.owners if n not in self.persons])[:4]
        else:
            self.P = self.owners[:3] + ([sit.subject] if sit.subject not in self.owners else [])'''

new_p_construction = '''        # owners: the people in the clause, then the things it names (things can own things: 'a pen costs 3
        # dollars'); with no people, the one the story is about comes last ('each bag has 4 apples' -> Tom's)
        if self.persons:
            self.P = (self.persons[:2] + [n for n in self.owners if n not in self.persons])[:4]
        else:
            # Don't add sit.subject if it's a thing (not a person)
            subj = sit.subject
            if subj and sit.gender.get(subj) != "thing":
                self.P = self.owners[:3] + ([subj] if subj not in self.owners else [])
            else:
                self.P = self.owners[:3]'''

content = content.replace(old_p_construction, new_p_construction)

# Fix 4: Add None for ownerless statements when there are counted things but no owners
old_none_add = '''        if None not in self.P and len(self.P) < 4 and \\
                any(o is None and t in [n for n, _ in self.things] for o, t, _ in sit.cells):
            self.P = self.P + [None]                   # 'how many days does she need?': and the apples lying there
        holders = [n for n, _ in self.things if n not in self.P and any(o == n for o, _, _ in sit.cells)]
        if holders and len(self.P) < 4:                # 'how many tables?': and what each table holds
            self.P = self.P + holders[:4 - len(self.P)]
        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

new_none_add = '''        # If there are counted things but no owners and no None owner, add None for ownerless statements
        if self.nums and not self.owners and None not in self.P:
            self.P = [None] + self.P
        if None not in self.P and len(self.P) < 4 and \\
                any(o is None and t in [n for n, _ in self.things] for o, t, _ in sit.cells):
            self.P = self.P + [None]                   # 'how many days does she need?': and the apples lying there
        holders = [n for n, _ in self.things if n not in self.P and any(o == n for o, _, _ in sit.cells)]
        if holders and len(self.P) < 4:                # 'how many tables?': and what each table holds
            self.P = self.P + holders[:4 - len(self.P)]
        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4 and self.nums:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

content = content.replace(old_none_add, new_none_add)

# Fix 4: observe_statement - allow learning stative frames
old_observe = '''            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            if same:                                          # it says nothing new about now: maybe about the start'''

new_observe = '''            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            # Stative sentences (no numbers, WORDLESS): allow learning "no change" frames
            # e.g., "the birds are migrating" -> birds stay the same
            if same and not clause.nums and self.WORDLESS:
                # Allow "no change" frame for stative sentences: label = label
                if label in atoms and atoms[label].c == v.c:
                    pairs.append(f"{label}={label}")
            if same:                                          # it says nothing new about now: maybe about the start'''

content = content.replace(old_observe, new_observe)

# Fix 5: last_thing only added when self.nums (not WORDLESS)
old_last_thing = '''        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

new_last_thing = '''        last_thing = next((p for p in reversed(sit.people) if sit.gender.get(p) == "thing"), None)
        if last_thing and last_thing not in self.P and len(self.P) < 4 and self.nums:
            self.P = self.P + [last_thing]                   # the thing just talked about ('pays with 50 dollars')'''

content = content.replace(old_last_thing, new_last_thing)

# Fix 6: observe_statement - allow learning "no change" frames for stative sentences
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

# Fix 6: T tuple creation in perceive - add 4th element False for uncounted nouns (already done above)

# Fix 7: setting function - handle WHERE + D (day/time)
old_setting = '''        for i, it in enumerate(items[:-1]):
            nxt = items[i + 1]
            after = items[i + 2] if i + 2 < len(items) else None
            if it[0] == "L" and it[1] in _WHERE and nxt[0] == "L" and nxt[1] in _DET - {"each", "every"} and \\
                    not (after and after[0] == "L" and after[1] in _NOT_NOUNS):
                j = i
                while j < len(items) and items[j][0] == "L":
                    out.add(j)
                    j += 1
            return out'''

new_setting = '''        for i, it in enumerate(items[:-1]):
            nxt = items[i + 1]
            after = items[i + 2] if i + 2 < len(items) else None
            # WHERE + DET + thing ('at the park', 'for his birthday')
            if it[0] == "L" and it[1] in _WHERE and nxt[0] == "L" and nxt[1] in _DET - {"each", "every"} and \\
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

# Fix 8: Clause constructor - fix owners logic (already done above but need to check)
# Fix 9: Clause constructor - don't add things as persons
old_persons = '''                    if name and name not in self.persons:
                        self.persons.append(name)'''

new_persons = '''                    if name and name not in self.persons and (it[3] or it[2] != "thing"):
                        self.persons.append(name)'''

content = content.replace(old_persons, new_persons)

# Fix 10: Clause constructor - owners logic (already done above)
# Fix 11: observe_statement - allow stative frames (already done above)

# Write the modified content
with open('brainlike/storyreader.py', 'w') as f:
    f.write(content)

print("All fixes applied!")