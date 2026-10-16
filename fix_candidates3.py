import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = """else:
                        # For statements, also allow cell labels that don't exist yet but are valid P#.T# labels
                        # This handles cases like "received 5 flowers" where P1.T1 doesn't exist yet
                        missing_atoms = [a for a in uses(expr) if a not in atoms]
                        cell_atoms = [a for a in missing_atoms if re.fullmatch(r"P\d+\.T\d+(?:@D\d+)?", a)]
                        if missing_atoms and cell_atoms and len(cell_atoms) == len(missing_atoms) and \
                           all(sit is not None and clause.cell(a) is not None and clause.cell(a) in sit.cells for a in cell_atoms):
                            pass  # Allow this candidate
                        else:
                            continue"""

new_block = """else:
                        # For statements, also allow cell labels that don't exist yet but are valid P#.T# labels
                        # This handles cases like "received 5 flowers" where P1.T1 doesn't exist yet
                        missing_atoms = [a for a in uses(expr) if a not in atoms]
                        cell_atoms = [a for a in missing_atoms if re.fullmatch(r"P\d+\.T\d+(?:@D\d+)?", a)]
                        if missing_atoms and cell_atoms and len(cell_atoms) == len(missing_atoms) and \
                           all(sit is not None and clause.cell(a) is not None for a in cell_atoms):
                            pass  # Allow this candidate
                        else:
                            continue"""

with open('brainlike/storyreader.py', 'w') as f:
    f.write(content.replace(old_block, new_block))

print("Fix applied!")