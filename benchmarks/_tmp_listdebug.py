"""Debug the list-fix injection on the muffins row: thing, marker, cell reads, answer."""
import sys, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Situation, sentences, split_question,   # noqa: E402
                                   perceive, Clause, clauses, what_is_asked)
import brainlike.storyreader as sr                              # noqa: E402

sr._LIST_FIX = True

story = ("Mrs. Hilt's favorite first grade classes are baking muffins. Mrs. Brier's class bakes "
         "18 muffins, Mrs. MacAdams's class bakes 20 muffins, and Mrs. Flannery's class bakes 17 "
         "muffins.")
qtext = "How many muffins does first grade bake in all?"

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
r = mind.language.reading.reader()
sit = Situation()
sents = sentences(story + " " + qtext)
q = split_question(sents[-1])
for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
    for items in clauses(perceive(toks, r.lex, sit), r.lex, sit):
        r.frames.apply(Clause(items, sit), sit)
c = Clause(perceive(q[1], r.lex, sit), sit)
print("asked:", what_is_asked(c.text()))
joined = " ".join(re.findall(r"[a-z]+", c.text().lower()))
print("joined:", joined)
print("TOTAL_Q:", sr._TOTAL_Q.search(joined))
for k in sit.cells:
    print("cell", k, "read=", sit.read(*k))
val, said = r.frames.answer(c, sit)
print("answer", val, said["expr"] if said else None)
from brainlike.storyreader import evaluate
atoms2 = {"Z0": sit.read("brier", "muffin", frozenset()),
          "Z1": sit.read("macadams", "muffin", frozenset()),
          "Z2": sit.read("flannery", "muffin", frozenset())}
print("Z types:", [type(v).__name__ for v in atoms2.values()])
print("evaluate:", evaluate("Z0+Z1+Z2", atoms2))
cands = r.frames.candidates("Q", c, c.atoms(sit, question=True))
print("cands0:", cands[0])
