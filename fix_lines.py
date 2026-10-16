import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    lines = f.readlines()

# Replace lines 2309-2337 (0-indexed: 2308-2336)
new_lines = [
    '        # Given total question: if we have a given total (N1) and a known day cell,\n',
    '        # and the question asks about another day, offer N1 - known_day\n',
    '        if thing and "N1" in atoms and atoms["N1"].known:\n',
    '            # Find known day cells for this thing from atoms\n',
    '            for atom in atoms:\n',
    '                if re.fullmatch(r"P\\\\d+\\\\.T\\\\d+@D\\\\d+", atom) and atoms[atom].known:\n',
    '                    expr = f"N1-{atom}"\n',
    '                    if counts_thing(clause, expr, thing):\n',
    '                        cands = [x for x in cands if x["expr"] != expr]\n',
    '                        cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",\n',
    '                                         "target": "ANS", "expr": expr})\n',
    '            # Also check situation cells for known day cells of this thing not in atoms\n',
    '            for key, (curr, first) in sit.cells.items():\n',
    '                if key[1] == thing and key[2] and curr.known:\n',
    '                    # This is a known day cell for the thing\n',
    '                    # Create a synthetic atom label for it based on day order\n',
    '                    day_names = list(key[2])\n',
    '                    day_idx = len(clause.D) + 1\n',
    '                    for day_name in key[2]:\n',
    '                        if day_name in clause.D:\n',
    '                            day_idx = clause.D.index(day_name) + 1\n',
    '                            break\n',
    '                    atom = f"P1.T1@D{day_idx}"\n',
    '                    if atom not in atoms:\n',
    '                        expr = f"N1-{atom}"\n',
    '                        if counts_thing(clause, expr, thing):\n',
    '                            cands = [x for x in cands if x["expr"] != expr]\n',
    '                            cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total_minus_day",\n',
    '                                             "target": "ANS", "expr": expr})\n',
]

# Replace lines 2309-2337 (0-indexed 2308-2336)
lines[2309:2337] = new_lines

with open('brainlike/storyreader.py', 'w') as f:
    f.writelines(lines)

print("Fix applied successfully!")