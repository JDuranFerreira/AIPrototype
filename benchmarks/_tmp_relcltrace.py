"""Book-row trace: what each statement writes to the story cells, _RELCL_FIX off vs on.

  python benchmarks/_tmp_relcltrace.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                      # noqa: E402
import brainlike.storyreader as sr                      # noqa: E402

STORY = ("Mrs. Hilt picked up a book that has 17 pages in it. She read 11 of the pages. "
         "How many pages does she have left to read?")


def diagnose(mind, fix):
    """Walk the story like solve() does and print the change-injection inputs per statement."""
    sr._RELCL_FIX = fix
    reader = mind.language.reading.reader()
    lex, frames = reader.lex, reader.frames
    sit = sr.Situation()
    sit.units = frames.units
    print(f"--- diagnosis, _RELCL_FIX={fix}")
    sents = sr.sentences(STORY)
    q = sr.split_question(sents[-1])
    for toks in [s for s in sents[:-1]] + ([q[0]] if q and q[0] else []):
        for seg in sr.clauses(sr.perceive(toks, lex, sit), lex, sit):
            c = sr.Clause(seg, sit)
            atoms = c.atoms(sit)
            cands = frames.candidates("S", c, atoms)
            verb = next((it[1] for it in c.items
                         if it[1] in sr._OUT_VERBS or it[1] in sr._IN_VERBS), None)
            head = cands[0] if cands else None
            match = bool(head and sr.re.fullmatch(r"N\d+", head["expr"]))
            cell = head["target"].replace("F:", "") if head else None
            key = c.cell(cell) if cell and not cell.startswith("F:") else None
            cur = sit.read(*key) if key else None
            dep = f"{cell}-N1" if cell else None
            exists = any(x["expr"] == dep and x["target"] == head["target"]
                         for x in cands) if head else False
            print(f"    clause {c.text()[:48]!r}")
            print(f"      verb={verb!r} cands0={head['key'] if head else None} "
                  f"expr={head['expr'] if head else None!r} fullmatch={match}")
            print(f"      cell_label={cell!r} clause.cell={key} sit.read={cur} "
                  f"known={getattr(cur, 'known', None)} departure_already_in_cands={exists}")
            if head:
                print(f"      top cands: {[(x['key'], x['expr'], round(x['c'], 2)) for x in cands[:4]]}")
            frames.apply(c, sit)
            for k in sorted(sit.cells, key=str):
                print(f"      -> cell {k} = {sit.cells[k]}")
    print()


def run(mind, fix):
    sr._RELCL_FIX = fix
    reader = mind.language.reading.reader()
    sit = sr.Situation()
    sit.units = reader.frames.units
    v, how, tr = reader.solve(STORY, sit=sit)
    print(f"[_RELCL_FIX={fix}] answer {v} | {how}")
    for k in sorted(sit.cells, key=str):
        print(f"    cell {k} = {sit.cells[k]}")
    for t in tr:
        print(f"    {t['clause'][:58]!r:62} did={t['did']} how={t['how']}")
    print()


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    run(mind, False)
    run(mind, True)
    diagnose(mind, False)
    diagnose(mind, True)


if __name__ == "__main__":
    main()
