"""Guard runner: world exam (fresh set) + real-story exam + ASDiv, for one or more levels, with an
optional perception counterfactual. Read-only: brain_state/ is not written.

  python benchmarks/_tmp_guard.py P1 P2          # baseline
  python benchmarks/_tmp_guard.py P1 P2 newnoun  # with the counterfactual
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def apply_newnoun():
    from brainlike.storyreader import (Frames, _BETWEEN, _BREAK, _DET, _GLUE, _NOT_NOUNS,
                                       _SMALL, _WHERE)
    orig = Frames.is_noun
    function = _DET | _SMALL | _BETWEEN | _NOT_NOUNS | _WHERE | _GLUE | _BREAK

    def is_noun(self, w, _orig=orig, _function=function):
        if _orig(self, w):
            return True
        if w in _function or self.pronoun(w):
            return False
        return self.heard.get(w, 0) > 0

    Frames.is_noun = is_noun
    print("[counterfactual: a heard-but-never-learned word counts as a possible new noun]")


def apply_newnoun2():
    """...but only a word no learned frame has ever used (so 'left' and 'had', which the brain has seen
    do work, stay literal; 'cherries', which it has only heard, may be the new noun it never got to meet)."""
    from brainlike.storyreader import (Frames, _BETWEEN, _BREAK, _DET, _GLUE, _NOT_NOUNS,
                                       _SMALL, _WHERE)
    orig = Frames.is_noun
    function = _DET | _SMALL | _BETWEEN | _NOT_NOUNS | _WHERE | _GLUE | _BREAK

    def is_noun(self, w, _orig=orig, _function=function):
        if _orig(self, w):
            return True
        if w in _function or self.pronoun(w) or self.heard.get(w, 0) == 0:
            return False
        if not hasattr(self, "_wordkeys"):                       # every word any learned frame used
            self._wordkeys = {k.split("|", 1)[0] for t in self.table.values()
                              for k in t if "|" in k}
        return w not in self._wordkeys

    Frames.is_noun = is_noun
    print("[counterfactual: a heard word no frame has ever used counts as a possible new noun]")


def apply_changefix():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX = True
    print("[counterfactual: change-family verbs depart/arrive on known cells; weak-frame heard words get the "
          "new-noun chance]")


def apply_changefixnoun():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_NOUN = True
    print("[counterfactual (noun part only): weak-frame heard words get the new-noun chance]")


def apply_changefixverb():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_VERB = True
    print("[counterfactual (verb part only): change-family verbs depart/arrive on known cells]")


def apply_deltafix():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_DELTA = True
    print("[counterfactual (delta question): a 'how many were added/did he eat' question reads now - first]")


def apply_cellsfix():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_CELLS = True
    print("[counterfactual (cell fallback): a change clause whose target holds nothing yet acts on the "
          "known cell of its noun]")


def apply_topicfix():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_CELLS = True
    sr._CHANGE_FIX_TOPIC = True
    print("[counterfactual (topic fallback): ... else the story's topic cell]")


def apply_namesfix():
    import brainlike.storyreader as sr
    sr._NAMES_FIX = True
    print("[counterfactual (names): a known word where a name goes is tagged person]")


def apply_beforefix():
    import brainlike.storyreader as sr
    sr._BEFORE_FIX = True
    print("[counterfactual (before): a before-question reads the cell's at-first value]")


def apply_nonnegfix():
    import brainlike.storyreader as sr
    sr._NONNEG_FIX = True
    print("[counterfactual (nonneg): never claim a negative count of things]")


def apply_flyfix():
    import brainlike.storyreader as sr
    sr._FLY_FIX = True
    print("[counterfactual (fly): 'flies away' reads as a departure]")


def apply_listfix():
    import brainlike.storyreader as sr
    sr._LIST_FIX = True
    print("[counterfactual (list): a total question sums every cell of the noun]")


def apply_ratefix():
    import brainlike.storyreader as sr
    sr._RATE_FIX = True
    print("[counterfactual (rate): a rate statement writes a positive per-unit cell]")


def apply_relclfix():
    import brainlike.storyreader as sr
    sr._RELCL_FIX = True
    print("[counterfactual (relcl): a known verb after that/which/who is not a thing ('a book THAT HAS 17 pages')]")


def apply_promote():
    import brainlike.storyreader as sr
    sr._CHANGE_PROMOTE = True
    print("[counterfactual (promote): the change verb's departure wins over the plain overwrite]")


def apply_eventfix():
    import brainlike.storyreader as sr
    sr._CHANGE_EVENT = True
    print("[counterfactual (event): a change statement that CREATES a cell tallies what went out]")


def apply_firstbase():
    import brainlike.storyreader as sr
    sr._FIRST_BASE = True
    print("[counterfactual (firstbase): a told at-first that contradicts the parts' starts is a base "
          "the parts don't cover]")


def apply_ownerless():
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_OWNERLESS = True
    print("[counterfactual (ownerless): a change clause whose target owner holds nothing departs from "
          "the lone ownerless known cell of the same noun]")


def main():
    levels = [a for a in sys.argv[1:] if a.startswith("P")]
    flags = [a for a in sys.argv[1:] if not a.startswith("P")]
    import brainlike.storyreader as sr
    for a in flags:                               # any _FLAG name is switched on for this run
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
    if "newnoun" in flags:
        apply_newnoun()
    if "newnoun2" in flags:
        apply_newnoun2()
    if "changefix" in flags:
        apply_changefix()
    if "changefixnoun" in flags:
        apply_changefixnoun()
    if "changefixverb" in flags:
        apply_changefixverb()
    if "deltafix" in flags:
        apply_deltafix()
    if "cellsfix" in flags:
        apply_cellsfix()
    if "topicfix" in flags:
        apply_topicfix()
    if "namesfix" in flags:
        apply_namesfix()
    if "beforefix" in flags:
        apply_beforefix()
    if "nonnegfix" in flags:
        apply_nonnegfix()
    if "flyfix" in flags:
        apply_flyfix()
    if "listfix" in flags:
        apply_listfix()
    if "ratefix" in flags:
        apply_ratefix()
    if "relclfix" in flags:
        apply_relclfix()
    if "promote" in flags:
        apply_promote()
    if "eventfix" in flags:
        apply_eventfix()
    if "firstbase" in flags:
        apply_firstbase()
    if "ownerless" in flags:
        apply_ownerless()
    levels = levels or ["P1"]
    kg = Mind.load(HERE.parent / "brain_state").language.reading
    for level in levels:
        rounds = kg.lessons.get(f"rounds_{level}", 0)
        items = primary.exam_items(level, "A", rounds)
        exam = primary.take_exam(kg, items)
        real = primary.real_exam(kg, level)
        print(f"{level} world exam: {exam['score']:.1%} (said understood {exam['predicted']:.0%}) | "
              f"real stories {real['right']}/{real['n']} (understood {real['understood']})")
    for g in (1, 2, 3, 4, 5, 6):
        o = primary.outside_exam(kg, g, "test")
        print(f"ASDiv g{g} test: right {o['right']}/{o['n']} ({o['right'] / o['n']:.0%}), "
              f"claims {o['understood']}, always answers {o['guess_right']}")


if __name__ == "__main__":
    main()
