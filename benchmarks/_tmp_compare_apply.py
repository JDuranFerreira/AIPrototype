"""Inside apply() for the comparative rows: candidates, missing, wider, chosen.

  python benchmarks/_tmp_compare_apply.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Situation, clauses, perceive, sentences, split_question  # noqa: E402

TEXTS = [
    ("Ellen", "Ellen has six more balls than Marin. Marin has nine balls. "
              "How many balls does Ellen have?"),
    ("Brian", "Brian has four more plums than Paul. Paul has seven plums. "
              "How many plums does Brian have?"),
]

import brainlike.storyreader as sr                              # noqa: E402
_orig_apply = sr.Frames.apply


def traced(self, clause, sit, asked=None):
    atoms = clause.atoms(sit)
    cands = self.candidates("S", clause, atoms)
    print(f"  clause {clause.text()!r}")
    print(f"    labels={list(clause.labels())} items={clause.items}")
    print(f"    atoms={ {k: str(v) for k, v in atoms.items()} }")
    for x in cands[:5]:
        print(f"    cand c={x['c']:.2f} rank={x['rank']} {x['target']} = {x['expr']!r} key={x['key']!r}")
    out = _orig_apply(self, clause, sit, asked)
    print(f"    -> did {out}")
    return out


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    sr.Frames.apply = traced
    for name, text in TEXTS:
        print(f"== {name}")
        sit = Situation()
        value, how, trace = reader.solve(text, sit=sit)
        print(f"  RESULT {value} ({how})")
        for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
            first, now = (pair + [pair[-1]])[:2] if isinstance(pair, list) else (pair, pair)
            print(f"    cell {key!s:<36} now={now} first={first}")


if __name__ == "__main__":
    main()
