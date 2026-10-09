"""For every question-blocked grade-1 test problem: which statement wrote nothing, and what the
question frame lookup tried. Read-only; the point is to name the reading gap per problem."""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import (Clause, Situation, clauses,  # noqa: E402
                                   perceive, sentences, split_question)


def main():
    grade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, "test")
    reader = mind.language.reading.reader()
    blocked = [r for r in exam["rows"] if r["got"] is None]
    print(f"{len(blocked)} question-blocked problems")
    reasons = Counter()
    for r in blocked:
        text = r["text"]
        lex, frames = reader.lex, reader.frames
        sit = Situation()
        sit.units = frames.units
        sents = sentences(text)
        if getattr(lex, "CONTEXT", False):
            lex.read_context(sents)
        q = split_question(sents[-1])
        silent, said = [], []
        for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
            for items in clauses(perceive(toks, lex, sit)):
                c = Clause(items, sit)
                done = frames.apply(c, sit)
                (said if done else silent).append(c.text())
        # the question side
        got, how, trace = reader.solve(text)
        # classify
        if not q:
            tag = "no question part found"
        elif not said and not silent:
            tag = "NO CLAUSES PERCEIVED"
        elif not said:
            tag = "every statement wrote nothing"
        else:
            tag = "value exists, question side failed"
        reasons[tag] += 1
        print(f"\n- {text[:88]}")
        print(f"    {tag}")
        if silent:
            print(f"    silent statements: {silent}")
        if said:
            print(f"    wrote: {len(said)} statements")
        print(f"    solve: {got} ({how})")
    print("\nsummary:", dict(reasons.most_common()))


if __name__ == "__main__":
    main()
