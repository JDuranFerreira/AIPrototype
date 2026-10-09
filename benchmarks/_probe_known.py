"""Why does each stuck word stay a literal? Print what known/thing/nouns/person say for it,
and which branch of perceive() catches it. Read-only."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                      # noqa: E402
from brainlike.storyreader import singular                              # noqa: E402

WORDS = ["jerry", "cherries", "had", "john", "shirt", "shirts", "sammy", "math", "problem",
         "problems", "victor", "apps", "dvds", "debby", "candy", "waiter", "customers",
         "poems", "lives", "boxes", "frank", "box", "pigeon", "breadcrumbs", "carrying",
         "pizzas", "slices", "radishes", "seashells", "flour", "kitten", "kittens"]


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    reader = mind.language.reading.reader()
    lex, frames = reader.lex, reader.frames
    nouns = set(getattr(lex, "nouns", {})) | set(getattr(frames, "nouns", {}))
    print(f"{'word':<14} {'known':<6} {'words':>5} {'heard':>5} {'mean':>5} thing person nounL like_known")
    for w in WORDS:
        print(f"{w:<14} {str(lex.known(w)):<6} {lex.words.word.get(w, 0):>5} "
              f"{frames.heard.get(w, 0):>5} {int(w in lex.meanings):>5} "
              f"{str(bool(lex.thing(w))):<6} {str(bool(lex.person(w))):<5} "
              f"{str(bool(singular(w) in nouns or w in nouns)):<6} {getattr(lex, 'like_known', lambda *_: '?')(w)}")


if __name__ == "__main__":
    main()
