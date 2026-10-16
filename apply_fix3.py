import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

# Find the block to replace
start_marker = '# Direct computation for "total X, known day Y = Z, find day W" pattern:'
start_idx = content.find(start_marker)
if start_idx == -1:
    print("Start marker not found!")
    sys.exit(1)

# Find the end of the block (next major comment block)
end_marker = '# The event question:'
end_idx = content.find(end_marker, content.find('# Direct computation for'))
if end_idx == -1:
    print("End marker not found!")
    sys.exit(1)

print(f"Found block from {content.find(start_marker)} to {end_idx}")

old_block = content[content.find(start_marker):end_idx]
print(f"Block length: {len(old_block)}")
print("First 200 chars:", repr(old_block[:200]))

new_block = '''        # Direct computation for "total X, known day Y = Z, find day W" pattern:
        # If we have a given total (N1), exactly one known day cell from context (not in question),
        # and the question asks about a specific day, compute directly.
        if thing and "N1" in atoms and atoms["N1"].known:
            # Find known day cells from context (not in question's day list)
            known_day_cells = []
            question_day_names = set(clause.D)
            for key, (curr, first) in sit.cells.items():
                if key[1] == thing and key[2] and curr.known:
                    day_names = key[2] - question_day_names
                    if day_names:
                        known_day_cells.append((key, curr.c, day_names.pop()))
            if len(known_day_cells) == 1:
                # Exactly one known day from context
                known_key, known_val, known_day = known_day_cells[0]
                # The question asks about a day in clause.D
                for day_name in clause.D:
                    # Direct computation: total - known = unknown
                    total_val = atoms["N1"].c
                    answer_val = total_val - known_val
                    if answer_val >= 0:
                        # Create a synthetic atom for the answer
                        atom = f"P1.T1@D{clause.D.index(day_name) + 1}"
                        expr = f"N1-{atom}"
                        cands.insert(0, {"rank": 2, "c": 0.99, "n": 1, "key": "total_minus_known_day",
                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})
        # The event question: a cell a change statement CREATED with no balance told only tallies'''

# Find the exact old block
old_start = content.find('        # Direct computation for "total X, known day Y = Z, find day W" pattern:')
if old_start == -1:
    print("Old block not found!")
    sys.exit(1)

old_end = content.find('        # The event question:', content.find('Direct computation for'))
if old_end == -1:
    print("End marker not found!")
    sys.exit(1)

old_block = content[old_start:old_end]
print(f"Found old block length: {len(old_block)}")

new_block = '''        # Direct computation for "total X, known day Y = Z, find day W" pattern:
        # If we have a given total (N1), exactly one known day cell from context (not in question),
        # and the question asks about a specific day, compute directly.
        if thing and "N1" in atoms and atoms["N1"].known:
            # Find known day cells from context (not in question's day list)
            known_day_cells = []
            question_day_names = set(clause.D)
            for key, (curr, first) in sit.cells.items():
                if key[1] == thing and key[2] and curr.known:
                    day_names = key[2] - question_day_names
                    if day_names:
                        known_day_cells.append((key, curr.c, day_names.pop()))
            if len(known_day_cells) == 1:
                # Exactly one known day from context
                known_key, known_val, known_day = known_day_cells[0]
                # The question asks about a day in clause.D
                for day_name in clause.D:
                    # Direct computation: total - known = unknown
                    total_val = atoms["N1"].c
                    answer_val = total_val - known_val
                    if answer_val >= 0:
                        # Create a synthetic atom for the answer
                        atom = f"P1.T1@D{clause.D.index(day_name) + 1}"
                        expr = f"N1-{atom}"
                        cands.insert(0, {"rank": 2, "c": 0.99, "n": 1, "key": "total_minus_known_day",
                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})
        # The event question: a cell a change statement CREATED with no balance told only tallies'''

content = content[:content.find('        # Direct computation for')] + new_block + content[content.find('        # The event question:', content.find('Direct computation for')):]

with open('brainlike/storyreader.py', 'w') as f:
    f.write(content)

print("Fix applied successfully!")