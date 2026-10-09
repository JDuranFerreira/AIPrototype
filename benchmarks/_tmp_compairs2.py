"""Every pair under statement keys containing 'more'/'fewer'/'less', with counts."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                              # noqa: E402

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
frames = mind.language.reading.reader().frames
for k, e in sorted(frames.table["S"].items()):
    if not any(w in k for w in ("more", "fewer", "less")):
        continue
    if not k.startswith(("more", "fewer", "less", "*")) and "|" not in k:
        continue
    for p, n in sorted(e["m"].items(), key=lambda kv: -kv[1]):
        print(f"  n={n:<5} key={k!r:<28} pair={p!r}")
