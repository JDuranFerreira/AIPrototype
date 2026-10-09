"""Which doubted words block which ASDiv test rows, right vs wrong readings? Read-only."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                                             # noqa: E402
from brainlike.regions import Mind                                        # noqa: E402
from brainlike.storyreader import _content_words                          # noqa: E402


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    d = mind.doubts
    exam = primary.outside_exam(mind.language.reading, 1, "test")
    rows = [r for r in exam["rows"] if r["how"] and r["how"].startswith("not sure")
            and "led me wrong" in r["how"]]
    right = wrong = 0
    print(f"{len(rows)} doubt-blocked rows:")
    for r in rows:
        w = sorted(x for x in _content_words(r["text"]) if d.doubted(x))
        tag = f"RIGHT got {r['got']}" if r["guess_right"] else f"wrong got {r['got']}"
        right += r["guess_right"]
        wrong += not r["guess_right"]
        print(f"  {tag:<16} want {r['answer']:>4} :: {r['text'][:68]}   doubt={w[:3]}")
    print(f"sum: {right} right, {wrong} wrong")


if __name__ == "__main__":
    main()