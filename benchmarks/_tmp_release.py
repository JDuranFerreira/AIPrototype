"""Doubt-release counterfactual on the post-fix code, with the doubt text per blocked row.

  python benchmarks/_tmp_release.py [flags]

For every ASDiv g1-test row the doubt memory blocked, print whether the block was a
word-memory doubt or a rival-reading doubt, and whether the row's answer was right. This
is the honesty line for a doubt release: a word-memory doubt on a row the reader now gets
right is stale; a rival-reading doubt is a live disagreement between two readings.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                    # noqa: E402
from brainlike.regions import Mind                               # noqa: E402
from brainlike.storyreader import StoryReader                    # noqa: E402

FLAG = next((a for a in sys.argv[1:] if a.startswith("_")), None)
if FLAG:
    import brainlike.storyreader as sr
    setattr(sr, FLAG, True)
    print(f"[{FLAG} switched on for this run]")

# capture the doubt text per row instead of swallowing it
_orig_doubt = StoryReader.doubt_about
BOX = {"last": []}


def doubt_about(self, *a, **k):
    doubts, checks = _orig_doubt(self, *a, **k)
    BOX["last"] = list(doubts)
    return doubts, checks


StoryReader.doubt_about = doubt_about

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
exam = primary.outside_exam(mind.language.reading, 1, "test")
rows = [r for r in exam["rows"] if r["how"].startswith("not sure")]

print(f"{len(rows)} doubt-blocked rows:\n")
word_only = rival = both = 0
right_wordonly = 0
for r in rows:
    doubts = BOX["last"] if r is exam["rows"][-1] else []
    # re-solve to get this row's doubts (the hook only keeps the last)
    got, how, trace = mind.language.reading.reader().solve(r["text"])
    doubts = next((t.get("doubts", []) for t in reversed(trace) if t.get("question")), [])
    has_rival = any(d.startswith("two ways") or d.startswith("the working") for d in doubts)
    has_word = any(d.startswith("these words") for d in doubts)
    tag = "both" if (has_rival and has_word) else "rival" if has_rival else "word" if has_word else "?"
    if tag == "word":
        word_only += 1
        if r["right"]:
            right_wordonly += 1
    elif tag == "rival":
        rival += 1
    elif tag == "both":
        both += 1
    print(f"  {tag:<6} {'RIGHT' if r['right'] else 'wrong'} want {r['answer']:>4} got {str(r['got']):>4} "
          f":: {r['text'][:60]}")
    for d in doubts:
        print(f"           {d[:96]}")

print(f"\nword-memory-only doubt: {word_only} (right when answered: {right_wordonly})")
print(f"rival-reading doubt:    {rival}")
print(f"both:                   {both}")
