"""List-fix narrowing: cells for the balloon winner and a kg-style 'each' total row."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Situation, sentences, split_question,   # noqa: E402
                                   perceive, Clause, clauses)
import brainlike.storyreader as sr                              # noqa: E402

ROWS = [
    ("farm(break?)", "Daniel and his brother Ben went to their grandfather's farm for a few weeks "
     "of vacation. During their stay at the farm, they were asked to take care of the animals. "
     "One day, his grandfather asked if he could count the total number of sheep that they have. "
     "If there are 3 herds of sheep and each herd has 20 sheep,",
     "how many sheep do they have in total?"),
    ("butterflies(break?)", "There are 397 butterflies. Each butterfly has 12 black dots and 17 "
     "yellow dots.", "How many black dots are there in all?"),
]


def run(story, qtext, fix):
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    sr._LIST_FIX = fix
    sit = Situation()
    sents = sentences(story + " " + qtext)
    q = split_question(sents[-1])
    body = list(sents[:-1]) + ([q[0]] if q and q[0] else [])
    if q and not q[0]:
        body = list(sents)
    for toks in body:
        for items in clauses(perceive(toks, reader.lex, sit), reader.lex, sit):
            reader.frames.apply(Clause(items, sit), sit)
    cells = {k: (str(v[0]), str(v[1])) for k, v in sit.cells.items()}
    c = Clause(perceive(q[1] if q and q[1] else qtext, reader.lex, sit), sit)
    val, said = reader.frames.answer(c, sit)
    return cells, val, (said["expr"] if said else None)


def main():
    for name, story, qtext in ROWS:
        print(f"--- {name}")
        for fix in (False, True):
            cells, val, expr = run(story, qtext, fix)
            print(f"    fix={fix}: answer {val} via {expr}")
            for k, pair in cells.items():
                print(f"        cell {k!s:<46} first={pair[0]} now={pair[1]}")


if __name__ == "__main__":
    main()
