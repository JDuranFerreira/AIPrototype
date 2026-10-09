"""Repro for the user's fuel-consumption question."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind  # noqa: E402
from brainlike import coding  # noqa: E402

TEXTS = [
    "A car needs to drive 300 km. It consumes 7 liters per km. How many liters does it need?",
    "A car needs to drive 300km how many liters of gasoline needs when it consumes 7l/km",
    "A car drives 300 km. It uses 7 liters per km. How many liters does it need?",
]


def main():
    mind = Mind.load(HERE.parent / "brain_state")
    coding.teach(mind, lambda *_: None)
    r = mind.language.reading.reader()
    for t in TEXTS:
        got, how, trace = r.solve(t)
        print(repr(t))
        print("  =>", got, "|", how)
        print("  trace:", trace)


if __name__ == "__main__":
    main()
