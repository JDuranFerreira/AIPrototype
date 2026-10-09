"""Rate + list-sum rows: cells, question atoms, candidates, answer."""
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
    ("apples(rate)", "Mrs. Hilt ate 5 apples every hour.",
     "How many apples had she eaten at the end of 3 hours?"),
    ("muffins(list3)", "Mrs. Hilt's favorite first grade classes are baking muffins. "
     "Mrs. Brier's class bakes 18 muffins, Mrs. MacAdams's class bakes 20 muffins, and "
     "Mrs. Flannery's class bakes 17 muffins.",
     "How many muffins does first grade bake in all?"),
    ("clown(list2)", "A clown gave away eleven balloons to girls and three balloons to boys.",
     "How many balloons did the clown give away?"),
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    sr._LIST_FIX = True
    sr._RATE_FIX = True
    for name, story, qtext in ROWS:
        sit = Situation()
        sents = sentences(story + " " + qtext)
        q = split_question(sents[-1])
        body = list(sents[:-1]) + ([q[0]] if q and q[0] else [])
        for toks in body:
            for items in clauses(perceive(toks, reader.lex, sit), reader.lex, sit):
                reader.frames.apply(Clause(items, sit), sit)
        print(f"--- {name}")
        for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
            print(f"    cell {key!s:<44} first={pair[0]} now={pair[1]}")
        qt = q[1] if q and q[1] else qtext
        c = Clause(perceive(qt, reader.lex, sit), sit)
        atoms = c.atoms(sit, question=True)
        for k, v in sorted(atoms.items()):
            if v.known:
                print(f"    atom {k!r:<40} c={v.c}")
        cands = reader.frames.candidates("Q", c, atoms)
        for x in cands[:6]:
            print(f"    cand rank={x['rank']} c={x['c']:.2f} expr={x['expr']!r} target={x['target']!r}")
        val, said = reader.frames.answer(c, sit)
        print(f"    answer {val} via {said['expr'] if said else None}")


if __name__ == "__main__":
    main()
