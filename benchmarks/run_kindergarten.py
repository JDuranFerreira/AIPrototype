"""Kindergarten experiment: how much does the brain understand after N scenes?

Learning curve for words, then world knowledge, actions and stories, all tested on NEW scenes,
new names, new numbers. No language model.

  python benchmarks/run_kindergarten.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from brainlike.kindergarten import ActionLearner, Kindergarten, WordLearner, WorldKnowledge, words_of  # noqa: E402
from brainlike.world import (COLOURS, KINDS, NUMBER_WORDS, PEOPLE, PLACES, SHAPES, WEATHER,      # noqa: E402
                             FEELINGS, ACTIONS, YOUNG, World, plural)

TRUE = {**{c: f"colour:{c}" for c in COLOURS}, **{s: f"shape:{s}" for s in SHAPES},
        **{w: f"count:{i}" for i, w in enumerate(NUMBER_WORDS) if 1 <= i <= 10},
        **{k: f"thing:{k}" for k in KINDS}, **{f: f"face:{f}" for f in FEELINGS},
        **{w: f"sky:{v}" for w, v in WEATHER.items()}, **{a: f"doing:{a}" for a in ACTIONS},
        "big": "size:big", "small": "size:small", "under": "rel:under", "behind": "rel:behind",
        "next": "rel:next", "front": "rel:front", "on": "rel:on"}


def vocab_score(words):
    right = [w for w, f in TRUE.items() if (m := words.meaning(w)) and m[0] == f]
    wrong = {w: words.meaning(w)[0] for w in TRUE if words.meaning(w) and words.meaning(w)[0] != TRUE[w]}
    return right, wrong


def quizzes(words, world, n=200):
    """Understanding in NEW scenes: find the red one / what colour is the dog / how many cats."""
    out = {}
    for kind in ("find colour", "name colour", "count"):
        ok = 0
        for _ in range(n):
            things, q, answer = world.quiz(kind)
            qw = words_of(q)
            if kind == "find colour":
                colour = next((m[0] for w in qw if (m := words.meaning(w, "colour"))), None)
                pick = next((t for t in things if colour == f"colour:{t['colour']}"), None)
                ok += pick is answer
            elif kind == "name colour":
                thing = next((m[0] for w in qw if (m := words.meaning(w, "thing"))), None)
                t = next((t for t in things if thing == f"thing:{t['kind']}"), None)
                ok += t is not None and words.word_for(f"colour:{t['colour']}") == answer
            else:
                thing = next((m[0] for w in qw if (m := words.meaning(w, "thing"))), None)
                t = next((t for t in things if thing == f"thing:{t['kind']}"), None)
                ok += t is not None and words.word_for(f"count:{t['count']}") == answer
        out[kind] = ok / n
    return out


def main():
    world = World(seed=1)
    test_world = World(seed=99)                      # new scenes for testing
    words = WordLearner()
    seen_total = 0
    print("STAGE 1-2  words from scenes (Hebbian, cross-situational)")
    for target in (100, 300, 1000, 3000, 10000):
        while seen_total < target:
            seen, heard = world.scene()
            words.observe(seen, heard)
            seen_total += 1
        right, wrong = vocab_score(words)
        q = quizzes(words, test_world)
        print(f"  after {target:>5} scenes: {len(right)}/{len(TRUE)} words mean the right thing"
              f" | new scenes: find-the-colour {q['find colour']:.0%}, name-the-colour {q['name colour']:.0%},"
              f" counting {q['count']:.0%}")
    print("  wrong meanings:", dict(list(wrong.items())[:8]))
    grammar = [w for w in ("the", "is", "a", "look", "there", "are", "this", "can", "today") if not words.meaning(w)]
    print("  grammar words with no meaning of their own:", grammar)
    print("  'orange' (a colour AND a fruit):", words.links("orange")[:3])

    print("\nSTAGE 3  knowledge about the world (inheritance along is-a)")
    know = WorldKnowledge(words)
    facts = world.facts()
    heard = sum(know.hear(f) for f in facts)
    print(f"  heard {len(facts)} facts, understood {heard}")
    tests = [("how many legs does a puppy have", 4), ("how many legs does a duckling have", 2),
             ("how many legs do three dogs have", 12), ("what does a lamb say", "baa"),
             ("is a duck an animal", "yes"), ("is a banana a food", "yes"), ("is a car an animal", "no"),
             ("can a chick walk", "yes"), ("how many legs does a spider have", 8),
             ("how many legs does a fish have", 0)]
    for q, a in tests:
        v, how = know.ask(q)
        print(f"  {'OK ' if v == a else 'NO '} {q}? -> {v}  ({how})")

    print("\nSTAGE 4  what actions do (before -> after)")
    actions = ActionLearner()
    for _ in range(300):
        before, heard, after, _ = world.event()
        actions.observe(before, heard, after)
    for verb in ("gives", "takes", "eats", "buys", "loses", "finds", "sells", "breaks"):
        print(f"  {verb:6} -> subject {actions.meaning(verb)[0] if actions.meaning(verb) else '?'}, "
              f"other person {actions.meaning(verb)[1] if actions.meaning(verb) else '?'}")

    print("\nSTAGE 5-6  stories, acted out with LEARNED frames (new names, numbers, things; no fixed patterns)")
    k = Kindergarten()
    k.teach("all")
    e = k.take_exam(n=100)
    print(f"  {e['right']}/{e['of']} new stories right")
    for kind, v in e["by_kind"].items():
        print(f"    {kind:16} {v['right']}/{v['of']}")
    s = k.summary()
    print("  pronouns it worked out:", s["pronouns"])
    print(f"  {s['frames']} frames, for example:", dict(list(s["frame_words"].items())[:8]))
    story, answer = World(seed=7).story()
    got, how, trace = k.reader().solve(story)
    print(f"    {story}\n      -> {got} (right: {answer}; {how})")
    for t in trace:
        print(f"         {t['clause']}: {'; '.join(t['did'])}  [{t['how']}]")


if __name__ == "__main__":
    main()
