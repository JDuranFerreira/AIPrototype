"""Does reading MORE real word problems help? Load a saved brain, read N real stories of a level (the teacher gives
each answer; no ASDiv or SVAMP problem is in the pool), and measure the ASDiv dev halves before and after.

  python benchmarks/try_real_scale.py BRAIN.json LEVEL N [--save OUT] [--source svamp_train|gsm8k_train]
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.kindergarten import Kindergarten                 # noqa: E402


def dev(kg):
    out = []
    for g in (1, 2, 3, 4):
        o = primary.outside_exam(kg, g, "dev")
        out.append(f"g{g} {o['right']}/{o['n']} (always {o['guess_right']})")
    return "  ".join(out)


def main():
    path, level, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if "--source" in sys.argv:                        # only one source of the library (svamp_train or gsm8k_train)
        import library
        src = sys.argv[sys.argv.index("--source") + 1]
        primary._LIBRARY["all"] = [x for x in library.load()[0] if x["source"] == src]
    kg = Kindergarten(json.loads(Path(path).read_text(encoding="utf-8")))
    print("before:", dev(kg), flush=True)
    t = time.time()
    done = primary.real_lessons(kg, level, n)
    kg.sleep(primary.SLEEP)
    print(f"read {n} real {level} stories in {time.time() - t:.0f}s (pool {done['pool']}): right first time "
          f"{done['right first time']}, found what it misread in {done['learned from']}")
    print("after: ", dev(kg))
    print("test:  ", "  ".join(f"g{g} {primary.outside_exam(kg, g, 'test')['right']}" for g in (1, 2, 3, 4)))
    if "--save" in sys.argv:
        Path(sys.argv[sys.argv.index("--save") + 1]).write_text(json.dumps(kg.state()), encoding="utf-8")


if __name__ == "__main__":
    main()
