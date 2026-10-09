"""Kindergarten exam on a disposable copy of the real brain (read-only for brain_state on disk)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                        # noqa: E402
from brainlike.serve import handle_kindergarten                           # noqa: E402


def main():
    import brainlike.storyreader as sr
    for a in sys.argv[1:]:                       # any _FLAG name is switched on for this run
        if a.startswith("_") and hasattr(sr, a):
            setattr(sr, a, True)
            print(f"[{a} switched on for this run]")
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
    mind = Mind.load(HERE.parent / "brain_state")
    r = handle_kindergarten(mind, "kindergarten", {"lesson": "exam"})
    e = r["kindergarten_exam"]
    print(f"kindergarten: {e['right']}/{e['of']}", "; per kind:", end=" ")
    print(", ".join(f"{k} {v['right']}/{v['of']}" for k, v in e["by_kind"].items()))


if __name__ == "__main__":
    main()