"""Generate brainlike/reading.py (the LANGUAGE region's engine) from kindergarten.py and
leave kindergarten.py as a compatibility shim. Run once."""
from pathlib import Path

here = Path(__file__).resolve().parents[2] / "brainlike"
src = (here / "kindergarten.py").read_text(encoding="utf-8")

subs = [
    ('"""Kindergarten: learning words and the world from scenes, like a young child.',
     '"""Reading (the LANGUAGE region\'s engine): learning words and the world from scenes, like a young child.'),
    ("The region lives in brain_state/kindergarten/kindergarten.json. It has no neural weights: what it",
     "Its state is kept by the language region (brain_state/language/reading.json). It has no neural weights: what it"),
    ("class Kindergarten:", "class Reading:"),
    ('"""The kindergarten region: words from scenes, facts about the world, what verbs do, and stories\n    read by acting them out with learned sentence frames.            -> brain_state/kindergarten/"""',
     '"""Reading: words from scenes, facts about the world, what verbs do, and stories\n    read by acting them out with learned sentence frames.   -> the language region"""'),
    ('"source": "kindergarten"', '"source": "language"'),
    ('"region": "kindergarten"', '"region": "language"'),
    ('f"kindergarten lessons:', 'f"reading lessons:'),
]

for a, b in subs:
    n = src.count(a)
    print(f"{n:>3}x  {a[:60]!r}")
    src = src.replace(a, b)

(here / "reading.py").write_text(src, encoding="utf-8")

shim = '''"""Compatibility shim.

The reading engine moved to reading.py, where it is the LANGUAGE region's engine
(words, sentence frames, reading stories). Import from .reading in new code; this
module only keeps older imports working.
"""
from .reading import *            # noqa: F401,F403
from .reading import Reading as Kindergarten   # old name
'''
(here / "kindergarten.py").write_text(shim, encoding="utf-8")
print("wrote reading.py and kindergarten.py shim")
