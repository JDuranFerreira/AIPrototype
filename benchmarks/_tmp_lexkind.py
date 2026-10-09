"""What kind of word is each name? (kind/property tables of the lexicon)"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                              # noqa: E402

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
lex = mind.language.reading.reader().lex
for w in ("ellen", "brian", "paul", "adam", "marin", "jackie", "has", "more", "than",
          "before", "first", "there", "some", "left"):
    info = []
    for attr in ("kind", "word_property", "prop", "category"):
        if hasattr(lex, attr):
            try:
                info.append(f"{attr}={getattr(lex, attr)(w)!r}")
            except TypeError:
                info.append(f"{attr}=?")
    print(f"{w:<8} known={lex.known(w)} thing={lex.thing(w)} "
          f"person={lex.person(w)} pronoun={lex.pronoun(w)} {' '.join(info)}")
