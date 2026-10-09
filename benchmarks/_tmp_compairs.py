"""What statement pairs does the table hold for 'more'/'fewer' keys?"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike.regions import Mind                              # noqa: E402

mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
frames = mind.language.reading.reader().frames
rows = []
for k, e in frames.table["S"].items():
    if "more" in k or "fewer" in k or "less" in k:
        for p, n in e["m"].items():
            if "+N" in p or "N1+" in p.split("=", 1)[-1]:
                rows.append((n, k, p, e.get("n"), e.get("o", {}).get(p, 0)))
rows.sort(reverse=True)
for n, k, p, tot, chances in rows[:40]:
    print(f"  count={n:<5} sure={n / max(chances, 1):.2f} key={k!r:<24} pair={p!r}")
print(f"total such pairs: {len(rows)}")

print("\nall pairs whose target/expr involve TWO cells (P1 & P2):")
for k, e in frames.table["S"].items():
    for p, n in e["m"].items():
        tgt, expr = p.split("=", 1)
        if "P1" in expr and "P2" in expr or ("P2" in tgt):
            print(f"  count={n:<5} key={k!r:<24} pair={p!r}")
