"""Why does 'How many marbles does Juan have?' read Connie's cell? Print the Q clause internals."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Situation, sentences, split_question,   # noqa: E402
                                   perceive, Clause, what_is_asked)
import brainlike.storyreader as sr                              # noqa: E402

TEXT = ("Connie has 323 marbles. Juan has 175 more marbles than Connie. "
        "How many marbles does Juan have?")


def run(fix):
    sr._NAMES_FIX = fix
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    sit = Situation()
    sents = sentences(TEXT)
    q = split_question(sents[-1])
    for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
        for items in clauses_with(toks, reader, sit):
            reader.frames.apply(Clause(items, sit), sit)
    c = Clause(perceive(q[1], reader.lex, sit), sit)
    print(f"--- namesfix={'on ' if fix else 'off'}")
    print(f"  items   {c.items}")
    print(f"  P={c.P}  T={c.T}  owners={c.owners}  subject={sit.subject!r}")
    print(f"  labels  {list(c.labels())}")
    print(f"  people  {sit.people}")
    atoms = c.atoms(sit, question=True)
    print(f"  atoms   { {k: (v.known, v.c if v.known else '?') for k, v in atoms.items()} }")
    cands = reader.frames.candidates("Q", c, atoms)
    for cd in cands[:4]:
        print(f"  cand    {cd['target']}={cd['expr']}  n={cd.get('n')}")


def clauses_with(toks, reader, sit):
    from brainlike.storyreader import clauses
    return clauses(perceive(toks, reader.lex, sit), reader.lex, sit)


def main():
    run(False)
    run(True)


if __name__ == "__main__":
    main()
