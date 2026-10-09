"""Does teaching the new recipes (with the request gate) change what the brain answers in the chat?

The same fixed world questions (exam sets it has already been taught, plus the S1/S2 sets) go through
the ask path twice: once on the brain as it is now, once after the code lesson is taught on a copy of
the same brain. A recipe may only make an answer better; if it makes one worse, that is shown here.
"""
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import coding, primary, serve                          # noqa: E402
from brainlike.regions import Mind                                   # noqa: E402


def as_text(v):
    try:
        return Fraction(str(v))
    except (ValueError, TypeError, ZeroDivisionError):
        return str(v).strip()


def main():
    import brainlike.storyreader as sr
    for a in sys.argv[1:]:                       # any _FLAG name is switched on for this run
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
    if "verbfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_VERB = True
    if "deltafix" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_DELTA = True
    if "cellsfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_CELLS = True
    if "namesfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._NAMES_FIX = True
    if "beforefix" in sys.argv:
        import brainlike.storyreader as sr
        sr._BEFORE_FIX = True
    if "nonnegfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._NONNEG_FIX = True
    if "flyfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._FLY_FIX = True
    if "listfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._LIST_FIX = True
    if "ratefix" in sys.argv:
        import brainlike.storyreader as sr
        sr._RATE_FIX = True
    if "relclfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._RELCL_FIX = True
    if "promote" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_PROMOTE = True
    if "eventfix" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_EVENT = True
    if "firstbase" in sys.argv:
        import brainlike.storyreader as sr
        sr._FIRST_BASE = True
    if "ownerless" in sys.argv:
        import brainlike.storyreader as sr
        sr._CHANGE_FIX_OWNERLESS = True
    old = Mind.load(HERE.parent / "brain_state")
    new = Mind.load(HERE.parent / "brain_state")
    kept, _ = coding.teach(new, lambda *_: None)

    items = []
    for level in ("P1", "P3", "S1", "S2"):
        for topic, question, truth in primary.exam_items(level, "A", 0)[:50]:
            items.append((f"{level}/{topic}: {question}", truth))
    better = worse = same = 0
    rows = []
    for question, truth in items:
        a = serve.handle(old, {"action": "ask", "problem": question})
        b = serve.handle(new, {"action": "ask", "problem": question})
        right_a, right_b = as_text(a.get("answer")) == truth, as_text(b.get("answer")) == truth
        if right_b and not right_a:
            better += 1
            rows.append(("BETTER", question, a.get("answer"), b.get("answer"), truth))
        elif right_a and not right_b:
            worse += 1
            rows.append(("WORSE", question, a.get("answer"), b.get("answer"), truth))
        else:
            same += 1
    print(f"recipes taught now: {sum(k for _, k in kept)}/{len(kept)}")
    print(f"{len(items)} world questions through the chat: {better} better, {worse} worse, {same} unchanged")
    for kind, q, a, b, t in rows:
        print(f"  {kind:6} {a} -> {b} (right {t})  {q[:80]}")


if __name__ == "__main__":
    main()