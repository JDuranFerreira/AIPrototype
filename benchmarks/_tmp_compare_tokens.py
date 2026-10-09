"""Per-token: what does the parser see and decide for the comparative sentences?

  python benchmarks/_tmp_compare_tokens.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                              # noqa: E402
from brainlike.storyreader import Situation, sentences          # noqa: E402

TEXTS = [
    "Ellen has six more balls than Marin. Marin has nine balls. How many balls does Ellen have?",
    "Brian has four more plums than Paul. Paul has seven plums. How many plums does Brian have?",
]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    lex = reader.lex
    for text in TEXTS:
        sit = Situation()
        sit.units = reader.frames.units
        sents = sentences(text)
        if getattr(lex, "CONTEXT", False):
            lex.read_context(sents)
            print(f"  (read_context on, CONTEXT=True)")
        for sent in sents:
            print(f"sent: {sent!r}")
            for w in sent:
                if w.isalpha():
                    print(f"   {w:<10} known={lex.known(w)} person={lex.person(w)}")


if __name__ == "__main__":
    main()
