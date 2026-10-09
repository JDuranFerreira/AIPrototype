"""Classify the ASDiv grade-1 test problems by what kind of story they are, split by outcome
(answered wrong / no answer / right). Read only. -> which failure class is worth fixing first."""
import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def cls(t):
    l = t.lower()
    if re.search(r"\bmore\b|\bfewer\b|\bless than\b|\btimes as many\b", l):
        return "comparative/multiplier"
    if re.search(r"\b(left|remain|now there|were (added|taken|removed)|put in|took|ate|flew|sold|read|given|gave)\b", l):
        return "change/remaining"
    if re.search(r"\beach\b|\bper\b|\bshared\b|\bbetween\b", l):
        return "share/each"
    if re.search(r"\bcost|\bdollar|\bcent|\bprice\b", l):
        return "money/rate"
    return "other"


def main():
    if "changefix" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_FIX = True
        print("[change/remaining counterfactual is ON]")
    grade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    state = HERE.parent / "brain_state"
    if "nodoubt" in sys.argv:
        import brainlike.storyreader as sr
        from brainlike.storyreader import StoryReader
        StoryReader.doubt_about = lambda self, *a, **k: ([], [])
        print("[doubt memory switched off for this run]")
    if "nogate" in sys.argv:
        import brainlike.storyreader as sr
        from brainlike.storyreader import StoryReader
        sr.counts_thing = lambda *a: True
        sr.scope_owner = lambda *a: None
        print("[request gate switched off for this run]")
    mind = Mind.load(state, {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, grade, "test")
    wrong = [r for r in exam["rows"] if r["got"] is not None and not r["guess_right"]]
    blocked = [r for r in exam["rows"] if r["got"] is None]
    right = [r for r in exam["rows"] if r["guess_right"]]
    for label, rows in (("answered WRONG", wrong), ("no answer at all", blocked), ("answer right", right)):
        print(f"{label} ({len(rows)}): {dict(collections.Counter(cls(r['text']) for r in rows).most_common())}")
    print("\nno answer, by class, one example each:")
    ex = {}
    for r in blocked:
        ex.setdefault(cls(r["text"]), []).append(r)
    for k, rs in sorted(ex.items()):
        print(f"  {k} x{len(rs)}: {rs[0]['text'][:95]}")
    print("\nanswered wrong, one example each:")
    ex = {}
    for r in wrong:
        ex.setdefault(cls(r["text"]), []).append(r)
    for k, rs in sorted(ex.items()):
        print(f"  {k} x{len(rs)}: want {rs[0]['answer']} got {rs[0]['got']} :: {rs[0]['text'][:85]}")


if __name__ == "__main__":
    main()
