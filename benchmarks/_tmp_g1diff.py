"""Which ASDiv g1-test rows improve under the change-family verb reading (and which regress)."""
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
    return primary.outside_exam(kg, 1, "test")["rows"]


def main():
    off, on = run(False), run(True)
    gained = lost = 0
    for a, b in zip(off, on):
        r0, r1 = bool(a["guess_right"]), bool(b["guess_right"])
        if r0 == r1:
            continue
        if r1 and not r0:
            gained += 1
            print(f"[GAINED] want {a['answer']} off={a['got']} on={b['got']}: {a['text'][:95]}")
        else:
            lost += 1
            print(f"[LOST  ] want {a['answer']} off={a['got']} on={b['got']}: {a['text'][:95]}")
    print(f"\ng1 answered right: off {sum(r['guess_right'] for r in off)} -> on {sum(r['guess_right'] for r in on)} "
          f"(gained {gained}, lost {lost})")


if __name__ == "__main__":
    main()