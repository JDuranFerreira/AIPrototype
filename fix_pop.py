import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_code = '''            if len(known_day_cells) == 1:
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
                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})'''

new_code = '''            if len(known_day_cells) == 1:
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
                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fix applied successfully!")
else:
    print("Old code not found!")
    idx = content.find('known_day_cells.append')
    if idx >= 0:
        print("Found at:", idx)
        print(content[idx:idx+500])