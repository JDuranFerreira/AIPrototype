"""Decisive experiment: can the request gate on the story reader fix the exam's two failures?

Q1 'How many people are in one car?' -> reader answers person/car = 1/5 (a rate) instead of 5.
Q2 'How many pens cost 15 dollars?'   -> reader answers pen/dollar = 1/3 (a rate) instead of 5.

Variants tested: (a) as-is; (b) with the per-car fact ('car's person = 5) also stored;
(c) the gate itself: readings that cannot be a count of the asked noun are dropped from the
Q-candidates before the surest reading is taken.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind   # noqa: E402
from brainlike.request import what_is_asked  # noqa: E402
from brainlike.storyreader import (  # noqa: E402
    Clause, Lin, Situation, clauses, counts_thing, evaluate, perceive, sentences, singular,
    split_question, uses)

CASES = [
    ("There are 253 people. Each car holds 5 people. How many people are in one car?", "5"),
    ("5 pens cost 15 dollars. How many pens cost 15 dollars?", "5"),
    ("Each jar has 12 sandwiches. There are 72 jars. How many jars are there?", "72"),
    ("There are 8 boxes with 7 pencils in each. How many boxes are there?", "8"),
    ("5 pens cost 15 dollars. How much do 8 pens cost?", "24"),
    ("There are 253 people. Each car holds 5 people. How many cars do they need?", "51"),
]


def act_out(reader, text, extra_cells=None, drop_cells=()):
    """Run the story's statements -> (question clause, atoms, frames)."""
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
    for cell, value in (extra_cells or {}).items():
        sit.cells[cell] = [Lin(value), Lin(value)]
    for cell in drop_cells:
        sit.cells.pop(cell, None)
    c = Clause(perceive(q[1], lex, sit), sit)
    return c, c.atoms(sit, question=True), frames


def cell_nouns(clause, expr):
    """The nouns this expression counts: {'P1.T1': 'pen', ...} for the atoms it uses."""
    nouns = {}
    for lab in uses(expr):
        if lab.startswith("P"):
            cell = clause.cell(lab[2:] if lab.startswith("F:") else lab)
            if cell:
                nouns[lab] = cell[1]
    return nouns


# ---- the gate itself, mirrored in production (Frames.answer uses counts_thing the same way) ---------

def gate(clause, cands, asked_thing):
    """Keep the readings that could count the asked noun; if that empties the pool, keep everything
    (the gate never leaves the reader with nothing when it had something). -> (kept, fired)"""
    if not asked_thing:
        return cands, False
    keep = [x for x in cands if counts_thing(clause, x["expr"], asked_thing)]
    return (keep, True) if keep else (cands, False)


def _first_value(cands, atoms, thing):
    """The reading `answer()` would take: the surest candidate that works out to a known number,
    skipping readings no count of things could be (between none and one), with the surest of them
    kept as the last resort -- the production answer() loop, value rule and all."""
    spared = None
    for x in cands:
        v = evaluate(x["expr"], atoms)
        if v is not None:
            v = v.bind({})
            if v.known:
                if thing and v.c != 0 and v.c < 1:
                    spared = spared or (x, v.c)
                    continue
                return x, v.c
    if spared:
        return spared[0], spared[1]
    return None, None


def show_gate(reader, text, extra_cells=None):
    """As-is winner vs gated winner, using the production `counts_thing` and the production asked."""
    c, atoms, frames = act_out(reader, text, extra_cells or {})
    asked = what_is_asked(c.text())          # production reads the request from the question clause
    thing = "" if asked["kind"] == "money" else singular(asked["thing"] or "")
    cands = frames.candidates("Q", c, atoms)
    kept, fired = gate(c, cands, thing)
    b0, v0 = _first_value(cands, atoms, "")
    b1, v1 = _first_value(kept, atoms, thing)
    print(f"\n{text}\n  asked kind={asked['kind']} thing={asked['thing']!r} -> singular {thing!r}")
    print(f"  as-is  : {v0}  expr={b0['expr'] if b0 else None} c={b0['c'] if b0 else 0:.2f}")
    print(f"  gated  : {v1}  expr={b1['expr'] if b1 else None} c={b1['c'] if b1 else 0:.2f}"
          + ("  (gate fired)" if fired else "  (gate quiet)"))
    for x in cands:
        keep = any(y["expr"] == x["expr"] and y["key"] == x["key"] for y in kept)
        if not keep or x is b1:
            print(f"    {'KEEP' if keep else 'DROP'} c={x['c']:.2f} rank={x['rank']} key={x['key']:<10} "
                  f"expr={x['expr']:<18} value={evaluate(x['expr'], atoms)}")


def dump_statement(reader, text):
    """Every S-candidate for each statement clause of the story (the statement-side root cause)."""
    lex, frames = reader.lex, reader.frames
    sit = Situation()
    sit.units = frames.units
    sents = sentences(text)
    if getattr(lex, "CONTEXT", False):
        lex.read_context(sents)
    for toks in sents:
        for items in clauses(perceive(toks, lex, sit)):
            c = Clause(items, sit)
            atoms = c.atoms(sit)
            print(f"\n  clause: {c.text()!r}  atoms={ {k: str(v) for k, v in atoms.items()} }")
            from brainlike.storyreader import _self_owned, _scales_content_total
            for x in frames.candidates("S", c, atoms)[:10]:
                flag = "DROP" if (_self_owned(c, x["target"])
                                  or _scales_content_total(c, x["target"], x["expr"])) else "keep"
                print(f"    [{flag}] c={x['c']:.2f} rank={x['rank']} key={x['key']:<10} "
                      f"{x['target']:<8} = {x['expr']:<16} value={evaluate(x['expr'], atoms)}")
            frames.apply(c, sit)
    print("  cells after:", {k: str(sit.cells[k][0]) for k in sit.cells})


def main():
    mind = Mind.load(HERE.parent / "brain_state")
    from brainlike import coding
    coding.teach(mind, lambda *_: None)
    reader = mind.language.reading.reader()

    print("=" * 100)
    print("STATEMENT SIDE: how 'Each car holds 5 people' is acted out")
    dump_statement(reader, "There are 253 people. Each car holds 5 people.")
    print("=" * 100)
    print("QUESTION SIDE: as-is winner vs gated winner")
    for text, told in CASES:
        show_gate(reader, text)
    show_gate(reader, "There are 253 people. Each car holds 5 people. How many people are in one car?",
              extra_cells={("car", "person", frozenset()): 5})


if __name__ == "__main__":
    main()
