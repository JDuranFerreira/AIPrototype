"""Chairs row: why does the -9 count survive the non-negative filter (thing? wrong path?)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Situation, sentences, split_question,   # noqa: E402
                                   perceive, Clause, clauses)
import brainlike.storyreader as sr                              # noqa: E402

STORY = "4 birds are sitting on a branch. 1 flies away."
Q = "How many birds are left on the branch?"


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for flag in (False, True):
        sr._FLY_FIX = (flag)
        sit = Situation()
        sents = sentences(STORY + " " + Q)
        q = split_question(sents[-1])
        toks_list = list(sents[:-1]) + ([q[0]] if q and q[0] else [])
        if Q and (not q or not q[0]):
            toks_list = list(sents)
        for toks in toks_list:
            for items in clauses(perceive(toks, reader.lex, sit), reader.lex, sit):
                reader.frames.apply(Clause(items, sit), sit)
        print(f"--- NONNEG={flag}")
        for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
            print(f"    cell {key!s:<42} first={pair[0]} now={pair[1]}")
        qt = q[1] if q and q[1] else Q
        c = Clause(perceive(qt, reader.lex, sit), sit)
        atoms = c.atoms(sit, question=True)
        for k, v in sorted(atoms.items()):
            print(f"    atom {k!r:<38} known={v.known} c={v.c if v.known else '?'}")
        val, said = reader.frames.answer(c, sit)
        print(f"    answer {val} via {said['expr'] if said else None}")


if __name__ == "__main__":
    main()


