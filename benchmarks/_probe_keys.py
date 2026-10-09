"""Which frame keys does a silent statement offer, and does the S-table know them?
Compares a statement that writes nothing with one that writes, same shape."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                   # noqa: E402
from brainlike.storyreader import (Clause, Situation, clauses,       # noqa: E402
                                   perceive, sentences)

TEXTS = [
    "Jerry had eleven cherries. He ate eight of them.",
    "Frank had thirteen boxes. If he filled eight with toys, how many boxes does he have left?",
    "John has twelve shirts. Later he bought four more shirts.",
    "Sammy has 9 math problems to do for homework. He has already finished 2 of them.",
    "Debby had twelve pieces of candy. After eating some, she had three pieces.",
    "Victor had nineteen apps on his phone. He deleted eight of them.",
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    lex, frames = reader.lex, reader.frames
    for text in TEXTS:
        print("=" * 96)
        print(text)
        sit = Situation()
        sit.units = frames.units
        sents = sentences(text)
        if getattr(lex, "CONTEXT", False):
            lex.read_context(sents)
        for toks in sents:
            for items in clauses(perceive(toks, lex, sit)):
                c = Clause(items, sit)
                print(f"  clause {c.text()!r}  items={c.items}")
                print(f"     labels={sorted(c.labels())} P={c.P} T={c.T} nums={c.nums}")
                for rank, k in c.keys():
                    e = frames.table["S"].get(k)
                    n = e["n"] if e else 0
                    ms = list(e["m"])[:4] if e else []
                    print(f"    rank {rank} key {k!r}: n={n} {ms}")
                done = frames.apply(c, sit)
                print(f"    wrote: {[d['target'] + ' = ' + d['expr'] for d in done or []] or 'NOTHING'}")


if __name__ == "__main__":
    main()
