import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = '''        # Given total question: if we have a given total (N1) and a known day cell,
        # and the question asks about another day, offer N1 - known_day
        if thing and "N1" in atoms and atoms["N1"].known:
            # Find known day cells for this thing from atoms
            for atom in atoms:
                if re.fullmatch(r"P\\d+\\.T\\d+@D\\d+", atom) and atoms[atom].known:
                    expr = f"N1-{atom}"
                    if counts_thing(clause, expr, thing):
                        cands = [x for x in cands if x["expr"] != expr]
                        cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",
                                         "target": "ANS", "expr": expr})
            # Also check situation cells for known day cells of this thing not in atoms
            for key, (curr, first) in sit.cells.items():
                if key[1] == thing and key[2] and curr.known:
                    # This is a known day cell for the thing
                    # Create a synthetic atom label for it based on day order
                    day_names = list(key[2])
                    day_idx = len(clause.D) + 1
                    for day_name in key[2]:
                        if day_name in clause.D:
                            day_idx = clause.D.index(day_name) + 1
                            break
                    atom = f"P1.T1@D{day_idx}"
                    if atom not in atoms:
                        expr = f"N1-{atom}"
                        if counts_thing(clause, expr, thing):
                            cands = [x for x in cands if x["expr"] != expr]
                            cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",
                                             "target": "ANS", "expr": expr})'''

new_block = '''        # Given total question: if we have a given total (N1) and a known day cell,
        # and the question asks about another day, offer N1 - known_day
        if thing and "N1" in atoms and atoms["N1"].known:
            # Find known day cells for this thing from atoms
            for atom in atoms:
                if re.fullmatch(r"P\\d+\\.T\\d+@D\\d+", atom) and atoms[atom].known:
                    expr = f"N1-{atom}"
                    if counts_thing(clause, expr, thing):
                        cands = [x for x in cands if x["expr"] != expr]
                        cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",
                                         "target": "ANS", "expr": expr})
            # Also check situation cells for known day cells of this thing not in atoms
            for key, (curr, first) in sit.cells.items():
                if key[1] == thing and key[2] and curr.known:
                    # Create a synthetic atom label for it based on day order
                    day_names = list(key[2])
                    day_idx = len(clause.D) + 1
                    for day_name in key[2]:
                        if day_name in clause.D:
                            day_idx = clause.D.index(day_name) + 1
                            break
                    atom = f"P1.T1@D{day_idx}"
                    if atom not in atoms:
                        expr = f"N1-{atom}"
                        if counts_thing(clause, expr, thing):
                            cands = [x for x in cands if x["expr"] != expr]
                            cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",
                                             "target": "ANS", "expr": expr})
        # Direct computation for "total X, known day Y = Z, find day W" pattern:
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
                                         "target": "ANS", "expr": expr, "value": Lin(answer_val)})'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fix applied successfully!")
else:
    print("Old block not found!")
    idx = content.find("Direct computation for")
    if idx >= 0:
        print("Found at index:", content[idx:idx+200])