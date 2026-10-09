"""One-process A/B: is the trained model itself different from what save() writes?

  python benchmarks/results/tmp_driver.py
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))       # repo root (brainlike)
sys.path.insert(0, str(HERE.parent))              # benchmarks (train_reasoner, run_reader)
from brainlike.reasoner import Reasoner          # noqa: E402
from train_reasoner import evaluate, load_svamp, worked_examples   # noqa: E402

examples, _seen = worked_examples()
r = Reasoner().train(examples, epochs=1, cache=True, log=lambda s: None)
items = [(x["text"], x["answer"]) for x in load_svamp("svamp_dev.csv")]
print("in-memory:", evaluate(r, items)[0], flush=True)
r.save(str(HERE / "tmp_drv"))
r2 = Reasoner.load(HERE / "tmp_drv")
print("reloaded :", evaluate(r2, items)[0], flush=True)
print("weights bitwise equal:", np.array_equal(r.W, r2.W), flush=True)
