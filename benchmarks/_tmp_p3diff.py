"""Diff the P3 real-story rows: with and without the change-family verb reading."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import brainlike.storyreader as sr                                    # noqa: E402
from brainlike import primary                                         # noqa: E402
from brainlike.regions import Mind                                    # noqa: E402


def run(fix):
    sr._CHANGE_FIX_VERB = fix
    kg = Mind.load(HERE.parent / "brain_state").language.reading
    reader = copy.deepcopy(kg).reader()
    out = []
    for text, answer in primary.real_stories("P3")[1]:
        got, how, _ = reader.solve(text)
        out.append((text, answer, got, how))
    return out


def main():
    off, on = run(False), run(True)
    diffs = 0
    for (t0, a, g0, h0), (t1, b, g1, h1) in zip(off, on):
        r0, r1 = g0 == a, g1 == b
        if r0 != r1:
            diffs += 1
            mark = "lost" if r0 and not r1 else ("gained" if r1 and not r0 else "?!")
            print(f"[{mark}] want {a} : off={g0} on={g1}")
            print(f"       off: {h0} / on: {h1}")
            print(f"       {t0[:110]}")
    print(f"\nP3 real stories: off {sum(1 for r in off if r[2] == r[1])}/{len(off)} -> "
          f"on {sum(1 for r in on if r[2] == r[1])}/{len(on)} ({diffs} rows differ)")


if __name__ == "__main__":
    main()