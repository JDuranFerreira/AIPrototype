"""Trace one story with the change-family verb reading off then on."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import brainlike.storyreader as sr                                    # noqa: E402
from brainlike.regions import Mind                                    # noqa: E402

CASE = "There are 86 blocks. 9 blocks more are added. How many are there total?"


def run(fix):
    sr._CHANGE_FIX_VERB = fix
    kg = Mind.load(HERE.parent / "brain_state").language.reading
    reader = kg.reader()
    got, how, trace = reader.solve(CASE)
    print(f"--- verb-fix {'ON' if fix else 'off'} -> {got} ({how})")
    for t in trace:
        m = "Q" if t.get("question") else "  "
        print(f"   [{m}] {t['clause']!r} sure={t['sure']} -> {t['did']}")


if __name__ == "__main__":
    run(False)
    run(True)