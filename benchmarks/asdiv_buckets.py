"""Bucket the ASDiv outside exam by WHY the reader failed - read only, nothing is taught.

The gate is "grade 1 test above 30% right, claims at least 80% true". This says which wall each
problem hits: it never understood the QUESTION (the gate / no frame), it read the sentences only
as a guess, the doubt memory stopped it, or it claimed and was wrong.

  python benchmarks/asdiv_buckets.py [GRADE [split [STATE_DIR]]]
"""
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402
from brainlike.request import what_is_asked                     # noqa: E402
from brainlike.storyreader import (Clause, Situation, clauses,  # noqa: E402
                                   perceive, sentences, singular, split_question, unfamiliar, uses)


def bucket(how, got):
    if how == "understood every sentence":
        return "claimed"
    if how.startswith("not sure"):
        return "doubt-blocked"
    if how.startswith("guessed"):
        return "clause-guess"
    if how.startswith("didn't understand the question"):
        return "question-blocked"
    if how.startswith("doesn't know enough"):
        return "half-read"
    if got is None:
        return f"other({how[:30]})"
    return f"answered({how[:30]})"


def why_question_blocked(reader, text):
    """For a question it refused: no Q-frame at all, the request gate emptied it, or unknown words."""
    lex, frames = reader.lex, reader.frames
    sit = Situation()
    sit.units = frames.units
    sents = sentences(text)
    if getattr(lex, "CONTEXT", False):
        lex.read_context(sents)
    q = split_question(sents[-1])
    if not q:
        return "no question"
    for toks in list(sents[:-1]) + ([q[0]] if q and q[0] else []):
        for items in clauses(perceive(toks, lex, sit), lex, sit):
            frames.apply(Clause(items, sit), sit)
    c = Clause(perceive(q[1], lex, sit), sit)
    atoms = c.atoms(sit, question=True)
    asked = what_is_asked(c.text())
    thing = singular(asked["thing"] or "") if asked["kind"] != "money" else ""
    from brainlike.storyreader import counts_thing, scope_owner, by_owner
    cands = frames.candidates("Q", c, atoms)
    if thing:
        keep = [x for x in cands if counts_thing(c, x["expr"], thing)]
        owner = scope_owner(c, thing)
        if owner:
            sc = [x for x in keep if by_owner(c, x["expr"], owner)]
            keep = sc or keep
    else:
        keep = cands
    unknown = unfamiliar(c, lex)
    if not cands:
        return "no Q frame" + (f" + unknown {','.join(unknown[:3])}" if unknown else "")
    if not keep:
        return "gate dropped all" + (f" + unknown {','.join(unknown[:3])}" if unknown else "")
    if unknown:
        return f"unknown words {','.join(unknown[:3])}"
    return "no value worked out"


def main():
    grade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    split = sys.argv[2] if len(sys.argv) > 2 else "test"
    state = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE.parent / "brain_state"
    import brainlike.storyreader as sr
    for a in sys.argv[1:]:                       # any _FLAG name is switched on for this run
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
    if "nogate" in sys.argv:                     # counterfactual: what does the request gate cost?
        import brainlike.storyreader as sr
        sr.counts_thing = lambda *a: True
        sr.scope_owner = lambda *a: None
        print("[request gate switched off for this run]")
    if "nodoubt" in sys.argv:                    # counterfactual: what does the doubt memory cost?
        from brainlike.storyreader import StoryReader
        StoryReader.doubt_about = lambda self, *a, **k: ([], [])
        print("[doubt memory switched off for this run]")
    if "both" in sys.argv:                       # counterfactual: neither gate nor doubt
        import brainlike.storyreader as sr
        from brainlike.storyreader import StoryReader
        sr.counts_thing = lambda *a: True
        sr.scope_owner = lambda *a: None
        StoryReader.doubt_about = lambda self, *a, **k: ([], [])
        print("[request gate AND doubt memory switched off for this run]")
    if "names" in sys.argv:                      # counterfactual: an unknown capitalised word is a name
        from brainlike.storyreader import Lexicon
        caps = set()
        for g in range(1, 7):
            for x in primary.load_outside(g):
                caps.update(w.lower() for w in re.findall(r"\b[A-Z][a-z]{2,}\b", x["text"]))
        _orig = Lexicon.person
        def person(self, w, _caps=caps, _orig=_orig):
            got = _orig(self, w)
            if got:
                return got
            return w if w in _caps and not self.known(w) else None
        Lexicon.person = person
        print(f"[unknown capitalised words treated as names for this run: {len(caps)} candidates]")
    if "newnoun" in sys.argv:                   # counterfactual: a word only ever HEARD can still be a new noun
        from brainlike.storyreader import (Frames, _BETWEEN, _BREAK, _DET, _GLUE, _NOT_NOUNS,
                                           _SMALL, _WHERE)
        _orig_is_noun = Frames.is_noun
        function = _DET | _SMALL | _BETWEEN | _NOT_NOUNS | _WHERE | _GLUE | _BREAK

        def is_noun(self, w, _orig=_orig_is_noun, _function=function):
            if _orig(self, w):
                return True
            if w in _function or self.pronoun(w):
                return False
            return self.heard.get(w, 0) > 0

        Frames.is_noun = is_noun
        print("[a heard-but-never-learned word counts as a possible new noun for this run]")
    if "newnoun2" in sys.argv:                  # counterfactual: ...but only a word no frame has ever used
        from _tmp_guard import apply_newnoun2
        apply_newnoun2()
    if "knownnodoubt" in sys.argv:               # counterfactual: doubt only words it does not really know
        from brainlike.storyreader import StoryReader, _content_words
        _orig_doubt = StoryReader.doubt_about

        def doubt_about(self, *args, **kwargs):
            saved = self.doubts.words
            self.doubts.words = {w: n for w, n in saved.items() if not self.lex.familiar(w)}
            try:
                return _orig_doubt(self, *args, **kwargs)
            finally:
                self.doubts.words = saved

        StoryReader.doubt_about = doubt_about
        print("[doubt memory applies only to words it is not sure it knows]")
    if "worddoubt" in sys.argv:                  # counterfactual: drop only the word-memory doubt; keep
        from brainlike.storyreader import StoryReader  # rival-reading and failed-working doubts
        _orig_word_doubt = StoryReader.doubt_about

        def doubt_about(self, text, clause, sit, value, x, rivals=(), atoms=None):
            doubts, checks = _orig_word_doubt(self, text, clause, sit, value, x, rivals, atoms)
            kept = [d for d in doubts if not d.startswith("these words have led me wrong before")]
            if len(kept) != len(doubts):
                checks.append("word-memory doubt dropped; rival/working doubts kept")
            return kept, checks

        StoryReader.doubt_about = doubt_about
        print("[the word-memory doubt does not block; rival-reading and working doubts still do]")
    if "rivaldoubt" in sys.argv:                 # counterfactual: drop only the rival-reading doubt; keep
        from brainlike.storyreader import StoryReader  # the word-memory doubt
        _orig_rival_doubt = StoryReader.doubt_about

        def doubt_about(self, text, clause, sit, value, x, rivals=(), atoms=None):
            doubts, checks = _orig_rival_doubt(self, text, clause, sit, value, x, rivals, atoms)
            kept = [d for d in doubts if not d.startswith("two ways of reading")]
            if len(kept) != len(doubts):
                checks.append("rival-reading doubt dropped; word-memory doubt kept")
            return kept, checks

        StoryReader.doubt_about = doubt_about
        print("[the rival-reading doubt does not block; the word-memory doubt still does]")
    if "deltafix" in sys.argv:                    # counterfactual: a 'how many were added' question reads now - first
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_DELTA = True
        print("[delta question reading switched on for this run]")
    if "cellsfix" in sys.argv:                    # counterfactual: a change clause acts on the known cell of its noun
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_CELLS = True
        print("[change clause cell fallback switched on for this run]")
    if "topicfix" in sys.argv:                    # counterfactual: ... else the story's topic cell
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_CELLS = True
        sr._CHANGE_FIX_TOPIC = True
        print("[change clause topic fallback switched on for this run]")
    if "namesfix" in sys.argv:                    # counterfactual: a known word where a name goes is a person
        import brainlike.storyreader as sr
        sr._NAMES_FIX = True
        print("[known-subject-as-person tagging switched on for this run]")
    if "beforefix" in sys.argv:                   # counterfactual: a before-question reads the at-first value
        import brainlike.storyreader as sr
        sr._BEFORE_FIX = True
        print("[before-question reading switched on for this run]")
    if "nonnegfix" in sys.argv:                   # counterfactual: never claim a negative count
        import brainlike.storyreader as sr
        sr._NONNEG_FIX = True
        print("[non-negative count filter switched on for this run]")
    if "flyfix" in sys.argv:                      # counterfactual: 'flies away' is a departure
        import brainlike.storyreader as sr
        sr._FLY_FIX = True
        print("[fly-away reading switched on for this run]")
    if "listfix" in sys.argv:                     # counterfactual: a total question sums the cells
        import brainlike.storyreader as sr
        sr._LIST_FIX = True
        print("[total-over-cells reading switched on for this run]")
    if "ratefix" in sys.argv:                     # counterfactual: a rate writes a positive cell
        import brainlike.storyreader as sr
        sr._RATE_FIX = True
        print("[rate reading switched on for this run]")
    if "relclfix" in sys.argv:                    # counterfactual: 'a book THAT HAS 17 pages' -> book's page
        from _tmp_guard import apply_relclfix
        apply_relclfix()
    if "promote" in sys.argv:                     # counterfactual: the change verb's departure beats the overwrite
        from _tmp_guard import apply_promote
        apply_promote()
    if "eventfix" in sys.argv:                    # counterfactual: a created cell tallies what went out of it
        from _tmp_guard import apply_eventfix
        apply_eventfix()
    if "firstbase" in sys.argv:                   # counterfactual: a told at-first that contradicts the parts is a base
        from _tmp_guard import apply_firstbase
        apply_firstbase()
    if "ownerless" in sys.argv:                   # counterfactual: an empty owner target falls back to the lone ownerless cell
        from _tmp_guard import apply_ownerless
        apply_ownerless()
    mind = Mind.load(state, {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, split)

    counts = Counter(bucket(r["how"], r["got"]) for r in exam["rows"])
    right = sum(r["right"] for r in exam["rows"])
    claimed = [r for r in exam["rows"] if r["understood"]]
    print(f"ASDiv g{grade} {split}: {exam['n']} problems, right {right}, claims {len(claimed)} "
          f"({100 * right / max(len(claimed), 1):.0f}% true), always answers "
          f"{sum(r['guess_right'] for r in exam['rows'])}")
    for k, v in counts.most_common():
        ok = sum(1 for r in exam["rows"] if bucket(r["how"], r["got"]) == k and r["guess_right"])
        print(f"  {k:<22} {v:>3}   (right when it answers: {ok})")

    # the claims that were wrong - the honesty problem
    wrong_claim = [r for r in claimed if not r["right"]]
    if wrong_claim:
        print("\nclaimed but wrong:")
        for r in wrong_claim[:8]:
            print(f"  want {r['answer']:>6} got {r['got']:>6} :: {r['text'][:80]}")

    # why the questions it refused were refused
    reasons = Counter()
    reader = mind.language.reading.reader()
    blocked = [r for r in exam["rows"] if bucket(r["how"], r["got"]) == "question-blocked"]
    for r in blocked:
        reasons[why_question_blocked(reader, r["text"])] += 1
    if blocked:
        print(f"\nquestion-blocked ({len(blocked)}), why:")
        for k, v in reasons.most_common():
            print(f"  {k:<40} {v:>3}")

    # answered wrongly (not claimed) - what would raise the score if reading improved
    missed = [r for r in exam["rows"] if r["got"] is not None and not r["right"]]
    print(f"\nanswered but wrong (not claimed): {len(missed)}")
    for r in missed[:8]:
        print(f"  want {r['answer']:>6} got {r['got']:>6} :: {r['text'][:80]}")

    # doubt-blocked rows: the word-memory vs the rival-reading doubt (the honesty line for a release)
    dblocked = [r for r in exam["rows"] if bucket(r["how"], r["got"]) == "doubt-blocked"]
    if dblocked:
        print(f"\ndoubt-blocked ({len(dblocked)}), why:")
        for r in dblocked:
            tag = "RIGHT" if r["right"] else "wrong"
            print(f"  {tag:<6} want {r['answer']:>4} got {str(r['got']):>4} :: {r['text'][:66]}")


if __name__ == "__main__":
    main()
