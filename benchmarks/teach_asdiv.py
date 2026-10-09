"""Teach the brain the ASDiv **dev** half (even problems; the test half is never taught) and show what
that did: the test half before teaching, after teaching and after sleep, plus the real-story exam, so a
lesson that hurts what it already knew is visible at once.

  python benchmarks/teach_asdiv.py GRADE [SLEEP_N [WEIGHT [STATE_DIR]]]

GRADE 1 is P1's outside grade, SLEEP_N 600 (0 skips the sleep), WEIGHT 3 (1 = the gentle weight sleep
replay uses), STATE_DIR defaults to brain_state. Writes the state directory - back it up first
(`brain_state_backup_before_<what>/`).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402


def pct(a, b):
    return f"{100 * a / b:.0f}% true" if b else "no claims"


def report(kg, grade, label):
    t = primary.outside_exam(kg, grade, "test")
    d = primary.outside_exam(kg, grade, "dev")
    r = primary.real_exam(kg, "P1")
    print(f"[{label}] ASDiv g{grade} TEST  right {t['right']}/{t['n']}, claims {t['understood']} "
          f"({pct(t['right'], t['understood'])}), always answers {t['guess_right']}", flush=True)
    print(f"[{label}] ASDiv g{grade} dev   right {d['right']}/{d['n']}, claims {d['understood']} "
          f"({pct(d['right'], d['understood'])}), always answers {d['guess_right']}", flush=True)
    print(f"[{label}] real stories         right {r['right']}/{r['n']}, claims {r['understood']} "
          f"({pct(r['right'], r['understood'])})", flush=True)


def main():
    grade = int(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    weight = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    state = Path(sys.argv[4]) if len(sys.argv) > 4 else HERE.parent / "brain_state"
    mind = Mind.load(state, {"model": "none", "url": ""})
    kg = mind.language.reading
    report(kg, grade, "before")

    dev = primary.outside_exam(kg, grade, "dev")
    agreed = learned = stuck = 0
    for row in dev["rows"]:
        res = kg.learn_story(row["text"], row["answer"], weight=weight, taught_words=False)
        if res.get("agreed"):
            agreed += 1
        elif res.get("lesson"):
            learned += 1
        else:
            stuck += 1
    print(f"taught the {len(dev['rows'])} dev problems (weight {weight}): it already had {agreed} right, "
          f"learned from {learned}, could not find the misread sentence in {stuck}", flush=True)
    mind.save(state)
    report(kg, grade, "after teach")

    if n:
        print(f"sleep: replaying {n} remembered stories ...", flush=True)
        kg.sleep(n)
        mind.save(state)
        report(kg, grade, "after sleep")
    else:
        print("no sleep requested", flush=True)

    exam = primary.take_exam(kg, primary.exam_items("P1", "A", kg.lessons.get("rounds_P1", 0)))
    sure = [r for r in exam["rows"] if r.get("sure")]
    print(f"[after sleep] P1 world exam {exam['score']:.1%}, claims {sum(r['ok'] for r in sure)}/{len(sure)} "
          f"({pct(sum(r['ok'] for r in sure), len(sure))})", flush=True)
    kg400 = kg.take_exam()
    print(f"[after sleep] kindergarten {kg400['right']}/{kg400['of']}", flush=True)
    print("saved")


if __name__ == "__main__":
    main()
