"""What does the school's own 'removed' story have that ASDiv's change stories don't?
Act both out and print every clause's write, the cells, and the labels the frames can target."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                    # noqa: E402
from brainlike.storyreader import (Clause, Situation, clauses,        # noqa: E402
                                   perceive, sentences, split_question)

CASES = [
    ("school P1 'removed' (works)", "There were 17 oranges in the basket. Five oranges were taken from the "
     "basket. Now there are 12 oranges. How many oranges are left in the basket?"),
    ("ASDiv (fails)", "Some oranges were in the basket. Five oranges were taken from the basket. Now there "
     "are 3 oranges. How many oranges were there at first?"),
    ("ASDiv (fails)", "17 plums were in the basket. More plums were added to the basket. Now there are 21 "
     "plums. How many plums were added?"),
    ("school P1 'change' (works?)", "Sam had 9 math problems. He finished 2 of them. How many math problems "
     "does he have left to do?"),
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for label, text in CASES:
        lex, frames = reader.lex, reader.frames
        sit = Situation()
        sit.units = frames.units
        print("=" * 100)
        print(f"{label}: {text}")
        sents = sentences(text)
        if getattr(lex, "CONTEXT", False):
            lex.read_context(sents)
        q = split_question(sents[-1])
        for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
            for items in clauses(perceive(toks, lex, sit)):
                c = Clause(items, sit)
                atoms = c.atoms(sit)
                done = frames.apply(c, sit)
                print(f"  {c.text()!r}")
                print(f"     labels: {sorted(c.labels())}")
                print(f"     D={c.D}  P={c.P}  T={c.T}")
                print(f"     wrote: {[d['target'] + ' = ' + d['expr'] for d in done or []] or 'NOTHING'}")
        print("  cells (start -> now):")
        for k, v in sorted(sit.cells.items(), key=lambda kv: str(kv[0])):
            print(f"    {k!s:<34} {v[0]} -> {v[-1]}")
        got, how, trace = reader.solve(text)
        print(f"  => answer {got} ({how})")
        for s in trace:
            print(f"     {'Q' if s.get('question') else ' '} {s['clause']!r} -> {s['did']} sure={s['sure']}")


if __name__ == "__main__":
    main()
