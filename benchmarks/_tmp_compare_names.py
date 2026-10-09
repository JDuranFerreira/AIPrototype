"""What does the lexicon say about the comparative story's names?

  python benchmarks/_tmp_compare_names.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
lex = mind.language.reading.reader().lex
for w in ("ellen", "marin", "brian", "paul", "adam", "jackie", "david", "beryl", "gale", "hilt"):
    print(f"{w:<8} person={lex.person(w)!r} known={lex.known(w)} pronoun={lex.pronoun(w)!r} "
          f"thing={lex.thing(w) if hasattr(lex, 'thing') else '?'}")
