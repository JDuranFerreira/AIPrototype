"""The strategy chooser (like the basal ganglia, with dopamine as the reward).

For a single-digit fact it hasn't learned, the brain has more than one way
to answer:
  guess   ask the section: cheap (one section), but maybe wrong
  derive  work it out with a rule that explains it: more steps, but reliable

Every time the teacher says right or wrong, the chosen strategy gets the
reward, so the brain learns per section which one pays off: right answers
are worth a lot, every step costs a little. Now and then it tries the other
strategy anyway (exploring), so it can change its mind as it learns.
"""
import random

STEP_COST = 0.02          # each step of work costs a little; a right answer is worth 1
EXPLORE = 0.1             # how often it tries a strategy that isn't its favourite


class Strategy:
    def __init__(self, stats=None, seed=None):
        self.stats = stats or {}          # "multiplication:derive" -> {"tries", "right", "steps"}
        self._rng = random.Random(seed)

    def _value(self, section, name):
        s = self.stats.get(f"{section}:{name}", {"tries": 0, "right": 0, "steps": 0})
        tries = s["tries"]
        success = (s["right"] + 1) / (tries + 2)          # starts at 50%, then follows the evidence
        cost = s["steps"] / tries if tries else 1
        return success - STEP_COST * cost

    def choose(self, section, options):
        """-> (chosen strategy, why)."""
        if len(options) == 1:
            return options[0], "the only way it has"
        if self._rng.random() < EXPLORE:
            return self._rng.choice(options), "exploring"
        best = max(options, key=lambda o: self._value(section, o))
        return best, "it has paid off best so far"

    def reward(self, section, name, correct, steps):
        s = self.stats.setdefault(f"{section}:{name}", {"tries": 0, "right": 0, "steps": 0})
        s["tries"] += 1
        s["right"] += int(bool(correct))
        s["steps"] += steps

    def summary(self):
        out = []
        for k, s in sorted(self.stats.items()):
            section, name = k.split(":", 1)
            out.append({"section": section, "strategy": name, "tries": s["tries"], "right": s["right"],
                        "avg_steps": round(s["steps"] / s["tries"], 1) if s["tries"] else 0,
                        "value": round(self._value(section, name), 2)})
        return out
