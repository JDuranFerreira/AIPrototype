"""Build the pretrained word-vector file the brain reads (tier 2 of the reading plan).

Raw source: GloVe 6B 50d (`resources/glove.6B.50d.txt`, 400,000 words, downloaded from the public
mirror of the StanfordNLP release; rebuild this file after changing it):

  python benchmarks/build_wordvec.py

Keeps the words the brain can plausibly meet - the first 20,000 GloVe entries (ordered by frequency)
plus every word found in brain_state, in the benchmark corpora and in this codebase - so the runtime
file stays a few MB instead of 163. Vectors are L2-normalised once, so a dot product is a cosine.
Writes `resources/wordvec.npz` (`vocab`, `vecs`, `meta`).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GLOVE = ROOT / "resources" / "glove.6B.50d.txt"
OUT = ROOT / "resources" / "wordvec.npz"
HEAD = 20_000                       # the most frequent GloVe words, kept whatever they are
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def wanted_words():
    """Every word the brain has met or could meet: its own state, the exam corpora, the code."""
    out = set()
    for folder, pats in ((ROOT / "brain_state", ("*.json",)),
                         (HERE, ("*.xml", "*.csv", "*.jsonl", "*.txt")),
                         (ROOT / "brainlike", ("*.py", "*.md")),
                         (HERE, ("*.py", "*.md"))):
        for pat in pats:
            for p in folder.glob(pat):
                try:
                    out.update(_WORD.findall(p.read_text(encoding="utf-8", errors="ignore").lower()))
                except OSError:
                    pass
    return {w for w in out if len(w) >= 2}


def main():
    if not GLOVE.exists():
        raise SystemExit(f"missing {GLOVE} - download glove.6B.50d.txt there first")
    want = wanted_words()
    vocab, vecs = [], []
    with GLOVE.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            w, *rest = line.rstrip().split(" ")          # GloVe 6B is ordered by frequency
            if i < HEAD or w in want:
                try:
                    v = np.array([float(x) for x in rest], dtype=np.float32)
                except ValueError:
                    continue
                n = float(np.linalg.norm(v))
                if n:
                    vocab.append(w)
                    vecs.append(v / n)
            if i and i % 100_000 == 0:
                print(f"  ...{i} lines, kept {len(vocab)}")
    a = np.array(vecs, dtype=np.float32)
    np.savez_compressed(OUT, vocab=np.array(vocab), vecs=a, meta=np.array([
        f"source=glove.6B.50d lines=400000 dim={a.shape[1]} kept={len(vocab)} head={HEAD}"]))
    print(f"wrote {OUT}  {len(vocab)} words x {a.shape[1]}d  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
