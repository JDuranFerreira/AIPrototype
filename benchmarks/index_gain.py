"""Does the cue index make finding a memory cheaper, or just more forgiving?

Every memory the brain stores is asked again in wordings a person would really use ("what is the
capital of Portugal?", "how many cents in a dollar?"). For each:

  exact    found by the old way (the same wording it was stored under)
  index    found by its cue words when the wording differs
  probes   stored entries the lookup had to touch: the index only opens the ones the question's
           words point at, the old way had to read the whole shelf

  python benchmarks/index_gain.py            # the real brain
  python benchmarks/index_gain.py --state brain_state_backup_before_s2
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                                 # noqa: E402


def wordings(stored, rng):
    """The same question, said the way a person would say it. Nothing here is written by hand per fact."""
    k = stored.replace("?", "")
    return [
        f"{k}?",                                   # just a question mark
        f"what is the {k}?",                       # the usual frame
        f"how many {k}?",                          # the "how many" frame
        f"please tell me {k}",                      # politeness
        " ".join(reversed(k.split())),             # the same words the other way round
        k.capitalize(),                            # capitalised
        f"{k} please",                             # trailing politeness
    ][: 6 if rng.random() < 0.8 else 7]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(HERE.parent / "brain_state"))
    args = ap.parse_args()
    mind = Mind.load(args.state)
    facts = mind.knowledge.facts
    if not facts:
        print("no told facts in this brain (the index still covers the arithmetic facts and the stories)")
        return
    index = mind.index
    rng = random.Random(0)

    rows = []
    for stored, answer in facts.items():
        for q in wordings(stored, rng):
            exact = mind.knowledge.get(q) == answer
            got, how = mind.recall_fact(q)
            rows.append({"q": q, "exact": exact, "index": got == answer, "how": how,
                         "probes": index.probes(q), "shelf": len(facts) + len(mind.arithmetic.memory)})

    n = len(rows)
    t0 = time.perf_counter()
    for r in rows:
        mind.knowledge.get(r["q"])
    t_exact = time.perf_counter() - t0
    t0 = time.perf_counter()
    for r in rows:
        mind.recall_fact(r["q"])
    t_index = time.perf_counter() - t0

    exact_hits = sum(r["exact"] for r in rows)
    index_hits = sum(r["index"] for r in rows)
    probes = sorted(r["probes"] for r in rows)
    size_kb = len(json.dumps(index.state(), ensure_ascii=False)) / 1024
    shelf = rows[0]["shelf"]
    # what the brain does instead when a lookup misses: wake the story reader / general chat.
    misses = [r["q"] for r in rows if not r["exact"]][:6]
    kg = mind.language.reading
    t0 = time.perf_counter()
    for q in misses:
        if mind.knowledge.get(q) is None:
            kg.chat(q)                           # the old way: a miss costs waking the reading engine
    t_miss = time.perf_counter() - t0
    t0 = time.perf_counter()
    for q in misses:
        if mind.recall_fact(q)[0] is None:
            kg.chat(q)
    t_miss_index = time.perf_counter() - t0

    print(f"{n} re-asked memories from {len(facts)} told facts "
          f"(+{len(mind.arithmetic.memory)} arithmetic facts indexed, {len(mind.memory.episodes)} story boxes not)")
    print(f"  found by exact wording (today) : {exact_hits:>4}/{n}  ({exact_hits / n:.0%})")
    print(f"  found with the cue index       : {index_hits:>4}/{n}  ({index_hits / n:.0%})")
    gained = [r for r in rows if r["index"] and not r["exact"]]
    print(f"  new ones the index found       : {len(gained)}")
    for r in gained[:6]:
        print(f"      {r['q'][:52]:52} -> {r['how']}")
    print(f"\n  entries opened per lookup      : median {probes[n // 2]}, worst {probes[-1]} with the index; "
          f"reading the whole shelf is {shelf}")
    print(f"  lookup time                    : {t_exact * 1000:>6.1f} ms exact, {t_index * 1000:>6.1f} ms with the index "
          f"({n} questions)")
    print(f"  the 6 misses the old way had   : {t_miss * 1000:>6.1f} ms waking the reading engine, "
          f"{t_miss_index * 1000:>6.1f} ms now (they no longer miss)")
    print(f"  index size                     : {size_kb:>6.1f} KB for {len(index):,} memories "
          f"({size_kb * 1024 / max(len(index), 1):.0f} bytes each)")


if __name__ == "__main__":
    main()