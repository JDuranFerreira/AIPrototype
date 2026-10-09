import sys
from pathlib import Path
HERE = Path("benchmarks").resolve()
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind
import brainlike.storyreader as sr
sr._CHANGE_EVENT = True
mind = Mind.load(Path("brain_state"), {"model": "none", "url": ""})
reader = mind.language.reading.reader()
sit = sr.Situation()
sit.units = reader.frames.units
text = ("Because of an upcoming exam, Robyn will not be able to sell cookies on Tuesday. "
        "To make up for it, Lucy decided to do double the work to catch up. "
        "She sold 34 cookies on her first round and 27 on her second round. "
        "How many cookies were sold by Lucy?")
v, how, tr = reader.solve(text, sit=sit)
for t in tr:
    print(repr(t["clause"][:55]), "did=", t["did"], "how=", t["how"])
print("cells:", {k: sit.cells[k] for k in sit.cells})
print("events:", sit.events)
print("answer:", v, how)
