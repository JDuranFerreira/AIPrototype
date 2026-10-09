"""Row-level diff of the g1 test with the change-clause cell fallback off -> on.

  python benchmarks/_tmp_celldiff.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def snap(off):
    import brainlike.storyreader as sr
    sr._CHANGE_FIX_CELLS = not off
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, 1, "test")
    return {r["text"]: (r["got"], r["right"], r["understood"], r["answer"], r["how"])
            for r in exam["rows"]}


def main():
    a = snap(True)                                   # cellsfix OFF
    b = snap(False)                                  # cellsfix ON
    print(f"changed rows: {sum(1 for k in a if a[k] != b[k])}")
    for k in a:
        if a[k] != b[k]:
            ga, ra, ua, wa, ha = a[k]                # OFF
            gb, rb, ub, wb, hb = b[k]                # ON
            print(f"  OFF: got {ga!s:>5} want {wa:>4} {'right' if ra else '     '} "
                  f"{'claim' if ua else '     '} {ha[:40]}")
            print(f"  ON : got {gb!s:>5} want {wb:>4} {'right' if rb else '     '} "
                  f"{'claim' if ub else '     '} {hb[:40]}")
            print(f"     {k[:110]}")


if __name__ == "__main__":
    main()
