import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    lines = f.readlines()

# Find the block to replace
start = None
end = None
for i, line in enumerate(lines):
    if 'Direct computation for "total X, known day Y = Z, find day W" pattern:' in line:
        start = i
    if start is not None and 'The event question:' in line:
        end = i
        break

print(f'start: {start}, end: {end}')

if start is not None and end is not None:
    new_lines = [
        '        # Direct computation for "total X, known days Y = Z, find day W" pattern:\n',
        '        # If we have a given total (N1), known day cells from context (not in question),\n',
        '        # and the question asks about a specific day, compute directly.\n',
        '        if thing and "N1" in atoms and atoms["N1"].known:\n',
        '            # Find known day cells from context (not in question\'s day list)\n',
        '            known_day_cells = []\n',
        '            question_day_names = set(clause.D)\n',
        '            for key, (curr, first) in sit.cells.items():\n',
        '                if key[1] == thing and key[2] and curr.known:\n',
        '                    day_names = key[2] - question_day_names\n',
        '                    if day_names:\n',
        '                        known_day_cells.append((key, curr.c, next(iter(day_names))))\n',
        '            if len(known_day_cells) >= 1:\n',
        '                # One or more known days from context\n',
        '                total_val = atoms["N1"].c\n',
        '                known_sum = sum(val for _, val, _ in known_day_cells)\n',
        '                answer_val = total_val - sum(v for _, v, _ in known_day_cells)\n',
        '                if answer_val >= 0:\n',
        '                    # The question asks about a day in clause.D\n',
        '                    for day_name in clause.D:\n',
        '                        # Direct computation: total - sum(known) = unknown\n',
        '                        atom = f"P1.T1@D{clause.D.index(day_name) + 1}"\n',
        '                        expr = f"N1-{atom}"\n',
        '                        cands.insert(0, {"rank": 2, "c": 0.99, "n": 1, "key": "total_minus_known_days",\n',
        '                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})\n',
    ]
    
    # Replace lines
    lines[start:end] = new_lines
    
    with open('brainlike/storyreader.py', 'w') as f:
        f.writelines(lines)
    
    print("Fix applied successfully!")
else:
    print("Could not find block boundaries")