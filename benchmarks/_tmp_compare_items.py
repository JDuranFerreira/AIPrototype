"""What does the comparative statement look like to the reader: items, labels, cells, candidates.

  python benchmarks/_tmp_compare_items.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Clause, Situation, clauses,  # noqa: E402
                                   perceive, sentences, split_question)

TEXTS = [
    "Ellen has six more balls than Marin. Marin has nine balls. How many balls does Ellen have?",
    "Brian has four more plums than Paul. Paul has seven plums. How many plums does Brian have?",
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for text in TEXTS:
        sit = Situation()
        sit.units = reader.frames.units
        sents = sentences(text)
        q = split_question(sents[-1])
        for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
            print(f"toks: {toks}")
            for w in toks:
                if w.isalpha():
                    print(f"   {w:<10} known={reader.lex.known(w)} in_people={w in sit.people} "
                          f"gender={sit.gender.get(w)!r}")
            for items in clauses(perceive(toks, reader.lex, sit)):
                c = Clause(items, sit)
                print(f"clause: {c.text()!r}")
                print(f"  items: {c.items}")
                print(f"  labels: {c.labels()}")
                for lb in c.labels():
                    print(f"    cell({lb}) = {c.cell(lb)}  sit={sit.read(*c.cell(lb))}")
                atoms = c.atoms(sit)
                print(f"  atoms: { {k: str(v) for k, v in atoms.items()} }")
                cands = reader.frames.candidates("S", c, atoms)
                for x in cands[:6]:
                    print(f"    cand rank={x['rank']} c={x['c']:.2f} target={x['target']!r} "
                          f"expr={x['expr']!r} key={x['key']!r}")


if __name__ == "__main__":
    main()
