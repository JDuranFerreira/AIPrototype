"""Which g1 test questions ask for the CHANGED amount (a delta), and how each fares now?

  python benchmarks/_tmp_delta.py [split]
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402

DELTA = {"added", "add", "ate", "eaten", "eating", "gave", "given", "give", "giving",
         "deleted", "delete", "spent", "spending", "sold", "sell", "lost", "use", "used",
         "removed", "remove", "took", "taken", "take", "picked", "pick", "finished", "buy",
         "bought", "get", "got", "receives", "received", "collected"}
BEFORE = {"left", "remain", "now", "begin", "start", "before", "first", "together",
          "altogether", "total", "in", "all", "each", "again", "more"}


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "test"
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, 1, split)
    rows = []
    for r in exam["rows"]:
        q = r["text"].split("?")[0].split(".")[-1].lower()
        qw = set(re.findall(r"[a-z]+", q))
        if qw & DELTA and not (qw & BEFORE):
            rows.append(r)
    print(f"delta-shaped questions: {len(rows)} of {exam['n']}")
    for r in rows:
        q = r["text"].split("?")[0].split(".")[-1].strip()
        flag = "CLAIMED" if r["understood"] else ("right " if r["guess_right"] else "      ")
        print(f"  {flag} want {r['answer']:>6} got {r['got']!s:>6} :: {q}  :: {r['text'][:60]}")


if __name__ == "__main__":
    main()
