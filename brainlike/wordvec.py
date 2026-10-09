"""Pretrained word vectors: what a word is like *before* the brain has heard it.

Tier 2 of the reading plan. The vectors are GloVe 6B 50d (400,000 words, 50 numbers per word, trained
on Wikipedia + Gigaword) filtered to the words this brain can meet - `resources/wordvec.npz`, built by
`benchmarks/build_wordvec.py` from `resources/glove.6B.50d.txt`. They are read-only: nothing here
learns, and nothing here writes brain_state. Every vector is already normalised, so a dot product is
a cosine.

They are used for exactly one thing: when the brain meets a word it has never heard, `nearest` says
which word it already knows the new word is most like, and the reader may take the new word as
understood when the two are very close (`MIN_FAMILIAR`, measured flat from 0.75 to 0.80 - see
HANDOFF). Meanings, counts and exam scores stay earned through experience: these vectors only open a
door the word would otherwise stay behind. Borrowing the neighbour's *role* as well (a person, a
thing, a colour) was measured too and made the claims less true, so nothing here feeds `Lexicon.feats`.
"""
import os
from pathlib import Path

import numpy as np

MIN_FAMILIAR = 0.78                  # cosine: an unheard word counts as understood at or above this
_PATHS = [Path(__file__).resolve().parent.parent / "resources" / "wordvec.npz"]
if os.environ.get("BRAINLIKE_WORDVEC"):
    _PATHS.insert(0, Path(os.environ["BRAINLIKE_WORDVEC"]))

_data = None                         # (vocab list, index dict, matrix), loaded once per process


def _load():
    global _data
    if _data is None:
        for p in _PATHS:
            if p.exists():
                d = np.load(p, allow_pickle=True)
                vocab = [str(w) for w in d["vocab"]]
                _data = (vocab, {w: i for i, w in enumerate(vocab)}, d["vecs"].astype(np.float32))
                break
        else:
            _data = ([], {}, np.zeros((0, 1), dtype=np.float32))
    return _data


def available():
    return bool(_load()[0])


def nearest(w, pool):
    """The closest word of `pool` to `w` -> (word, cosine), or None. Both the word and its neighbours
    must be in the pretrained vocabulary, and `pool` may be any iterable of words."""
    _, index, vecs = _load()
    i = index.get(w)
    if i is None:
        return None
    best, best_s = None, -1.0
    for x in pool:
        j = index.get(x)
        if j is None or j == i:
            continue
        s = float(vecs[j] @ vecs[i])
        if s > best_s:
            best, best_s = x, s
    return (best, best_s) if best is not None else None


def similar(w, k=5, within=None):
    """The `k` closest words to `w` (all of them, or only words in `within`) -> [(word, cosine)]."""
    _, index, vecs = _load()
    i = index.get(w)
    if i is None:
        return []
    if within is None:
        keys, rows = list(index.keys()), np.arange(len(vecs))
    else:
        keys = [x for x in within if x in index and x != w]
        if not keys:
            return []
        rows = np.array([index[x] for x in keys])
    s = vecs[rows] @ vecs[i]
    order = np.argsort(-s)[:k]
    return [(keys[int(o)], float(s[int(o)])) for o in order]
