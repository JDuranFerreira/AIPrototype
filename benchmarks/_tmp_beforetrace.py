"""Why do some before-questions fire the F: reading and others not: cells + Q atoms per story."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Situation, sentences, split_question,   # noqa: E402
                                   perceive, Clause)
import brainlike.storyreader as sr                              # noqa: E402

STORIES = [
    ("oranges(FIRES)", "Some oranges were in the basket. Five oranges were taken from the basket. "
                       "Now there are three oranges. How many oranges were in the basket before "
                       "some of the oranges were taken?"),
    ("chef(FIRES)", "A chef used fifteen apples to make a pie. Now he has four apples left. "
                    "How many apples did he have before he made the pie?"),
    ("rachel(no)", "Rachel picked three apples from her tree. Now the tree has four apples still "
                   "on it. How many apples did the tree have to begin with?"),
    ("bookfair(no)", "The book fair sold four posters. Now they have two posters left. "
                     "How many posters did they have to begin with?"),
    ("ned(no)", "Ned gave away thirteen of his video games to a friend. Now Ned has six games. "
                "How many games did Ned have before he gave the games away?"),
]


def main():
    sr._BEFORE_FIX = True
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for name, text in STORIES:
        sit = Situation()
        sents = sentences(text)
        q = split_question(sents[-1])
        for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
            for items in clauses_of(toks, reader, sit):
                reader.frames.apply(Clause(items, sit), sit)
        print(f"--- {name}")
        for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
            print(f"    cell {key!s:<42} first={pair[0]} now={pair[1]}")
        c = Clause(perceive(q[1], reader.lex, sit), sit)
        atoms = c.atoms(sit, question=True)
        fs = {k: (v.known, v.c if v.known else "?") for k, v in atoms.items() if k.startswith("F:")}
        bases = {k: (v.known, v.c if v.known else "?") for k, v in atoms.items()
                 if not k.startswith(("F:", "N", "K"))}
        print(f"    Q items {c.items}")
        print(f"    Q F: {fs}")
        print(f"    Q base {bases}")
        val, said = reader.frames.answer(c, sit)
        print(f"    answer {val} via {said['expr'] if said else None}")


def clauses_of(toks, reader, sit):
    from brainlike.storyreader import clauses
    return clauses(perceive(toks, reader.lex, sit), reader.lex, sit)


if __name__ == "__main__":
    main()
