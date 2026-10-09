"""Why does the reader answer with the WRONG CELL of the story? Three wrong cases and one right-but-unclaimed.

For each: the cells it acted the statements out into, then every Q-candidate with its value, which the
request gate keeps, and what the surest reading answers. If the right expression is a candidate and
loses, it is ranking (code); if it is not there at all, no frame ever taught it (training).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                                    # noqa: E402
from brainlike.request import what_is_asked                           # noqa: E402
from brainlike.storyreader import (Clause, Situation, by_owner,       # noqa: E402
                                   clauses, counts_thing, evaluate,
                                   perceive, scope_owner, sentences,
                                   show_work, singular, split_question,
                                   unfamiliar, uses)

CASES = [
    ("Adam has five more apples than Jackie. Jackie has nine apples. How many apples does Adam have?", "14"),
    ("Jake has six fewer peaches than Steven. Steven has 13 peaches. How many peaches does Jake have?", "7"),
    ("17 plums were in the basket. More plums were added to the basket. Now there are 21 plums. "
     "How many plums were added?", "4"),
    ("Seven red apples and two green apples are in the basket. How many apples are in the basket?", "9"),
]


def act(reader, text):
    lex, frames = reader.lex, reader.frames
    sit = Situation()
    sit.units = frames.units
    sents = sentences(text)
    if getattr(lex, "CONTEXT", False):
        lex.read_context(sents)
    q = split_question(sents[-1])
    for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
        for items in clauses(perceive(toks, lex, sit)):
            frames.apply(Clause(items, sit), sit)
    c = Clause(perceive(q[1], lex, sit), sit)
    return sit, c, c.atoms(sit, question=True), frames


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    for text, want in CASES:
        sit, c, atoms, frames = act(reader, text)
        print("=" * 100)
        print(f"WANT {want} :: {text}")
        print("  cells after the statements:")
        for k, v in sorted(sit.cells.items()):
            print(f"    {k!s:<28} = {v[0]}")
        asked = what_is_asked(c.text())
        thing = "" if asked["kind"] == "money" else singular(asked["thing"] or "")
        print(f"  asked: kind={asked['kind']} thing={asked['thing']!r} singular={thing!r}")
        cands = frames.candidates("Q", c, atoms)
        keep = [x for x in cands if counts_thing(c, x["expr"], thing)] if thing else cands
        owner = scope_owner(c, thing) if thing else None
        scoped = [x for x in keep if by_owner(c, x["expr"], owner)] if owner else []
        print(f"  owner scope: {owner!r} -> keeps {len(scoped)} of {len(keep)} gated")
        best = None
        for x in cands:
            v = evaluate(x["expr"], atoms)
            v = v.bind(sit.bound) if v is not None else None
            ink = "KEEP" if x in keep else "drop"
            ins = "scoped" if x in scoped else "     "
            val = str(v) if v is not None else "None"
            mark = ""
            if v is not None and v.known and str(v.c) == want:
                mark = "  <== THE RIGHT READING"
            print(f"    {ink} {ins} c={x['c']:.2f} rank={x['rank']} key={x['key']:<14} "
                  f"expr={x['expr']:<22} value={val}{mark}")
            if best is None and x in keep and v is not None and v.known and not (thing and 0 < v.c < 1):
                best = (x, v.c)
        got, how, _ = mind.language.reading.reader().solve(text)
        print(f"  => reader answered: {got}  ({how})")
        print(f"  question unsure: {unfamiliar(c, reader.lex)}")


if __name__ == "__main__":
    main()
