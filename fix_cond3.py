import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('brainlike/storyreader.py', 'r') as f:
    content = f.read()

old_block = """            # Also apply the condition part (q[0]) as a statement if it contains numbers
            # (e.g., "If she had 11 coins initially" sets the initial amount)
            cond_text = " ".join(q[0])
            import re
            # Check if the condition part contains numbers (factual condition, not hypothetical question)
            if re.search(r"\d", cond_text) or any(self.lex.number(w) for w in q[0]):
                # Check if it looks like a factual condition (not a question)
                if not any(w.lower() in ("how", "what", "when", "where", "why", "which", "who") for w in q[0]):
                    # Process the entire condition part as a statement
                    cond_items = perceive(q[0], self.lex, sit)
                    for items in clauses(cond_items, self.lex, sit):
                        c = Clause(items, sit)
                        if override and idx in override:
                            done = self._force(c, sit, override[idx])
                        else:
                            done = self.frames.apply(c, sit, asked)
                        sure = self._sure(c, done)
                        trace.append({"clause": c.text(), "did": [self._say(c, d) for d in done or []],
                                      "how": done[0]["key"] if done else None, "sure": sure,
                                      "unknown": unfamiliar(c, self.lex) if c.nums else []})
                        if c.nums and not done:
                            unsure.append(c.text())
                        elif c.nums and not sure:
                            guessed.append(c.text())
                        idx += 1
        parts = [s for s in body]"""

new_block = """            # Also apply the condition part (q[0]) as a statement if it contains numbers
            # (e.g., "If she had 11 coins initially" sets the initial amount)
            cond_text = " ".join(q[0])
            import re
            # Check if the condition part contains numbers (factual condition, not hypothetical question)
            if re.search(r"\d", cond_text) or any(self.lex.number(w) for w in q[0]):
                # Check if it looks like a factual condition (not a question)
                if not any(w.lower() in ("how", "what", "when", "where", "why", "which", "who") for w in q[0]):
                    # Add the condition tokens to the body for later processing
                    body.append(q[0])

        parts = [s for s in body]"""

with open('brainlike/storyreader.py', 'w') as f:
    f.write(content.replace(old_block, new_block))

print("Fix applied!")