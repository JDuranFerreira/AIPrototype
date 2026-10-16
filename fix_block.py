# Given total question: if we have a given total (N1) and a known day cell,
        # and the question asks about another day, offer N1 - known_day
        if thing and "N1" in atoms and atoms["N1"].known:
            # Find known day cells for this thing from atoms
            for atom in atoms:
                if re.fullmatch(r"P\d+\.T\d+@D\d+", atom) and atoms[atom].known:
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
                                             "target": "ANS", "expr": expr})