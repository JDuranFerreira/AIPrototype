"""Trace the base-before-comparative story (Connie/Juan) with _NAMES_FIX off and on."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Situation                     # noqa: E402
import brainlike.storyreader as sr                              # noqa: E402

TEXT = ("Connie has 323 marbles. Juan has 175 more marbles than Connie. "
        "How many marbles does Juan have?")


def run(fix):
    sr._NAMES_FIX = fix
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    sit = Situation()
    value, how, trace = reader.solve(TEXT, sit=sit)
    print(f"namesfix={'on ' if fix else 'off'} -> {value!s} ({how})")
    for d in trace:
        print(f"  {d['clause'][:70]!r:<72} did={d['did']}")
    for key, pair in sorted(sit.cells.items(), key=lambda kv: str(kv)):
        print(f"    {key!s:<40} now={pair[1] if isinstance(pair, list) else pair}")


def main():
    run(False)
    run(True)


if __name__ == "__main__":
    main()
