import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = '''# Given total question: if we have a given total (N1) and a known day cell,
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
                    # Find the corresponding atom label
                    for label in clause.labels():
                        if label.endswith("@D") and clause.cell(label) == key:
                            atom = label
                            break
                    else:
                        continue
                    if atom not in atoms:
                        expr = f"N1-{atom}"
                        if counts_thing(clause, expr, thing):
                            cands = [x for x in cands if x["expr"] != expr]
                            cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",
                                             "target": "ANS", "expr": expr})'''

new_block = '''# Given total question: if we have a given total (N1) and a known day cell,
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

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('brainlike/storyreader.py', 'w') as f:
        f.write(content)
    print("Fix applied successfully!")
else:
    print("Old block not found!")
    # Try to find it
    idx = content.find("Given total question")
    if idx >= 0:
        print("Found at index:", content[content.find("Given total question"):content.find("Given total question")+500])