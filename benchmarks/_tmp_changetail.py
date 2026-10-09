"""All change/remaining g1-test rows that are wrong or blocked, with the per-clause trace and question reading.
Read only. Hour glass: group by WHAT the reading failed to do, not by keyword."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import primary                                   # noqa: E402
from brainlike.regions import Mind                              # noqa: E402

CH = re.compile(r"\b(left|remain|rest|still|now there|were? (added|taken|removed|put)|put in|took|take|ate|eaten|"
                r"finished|flew|sold|bought|spent|picked|gave|given|got|had|brought|brought|collected|received|"
                r"drank|are gone|went)\b")


def main():
    mind = Mind.load(HERE.parent / "brain_state", {"model": "none", "url": ""})
    exam = primary.outside_exam(mind.language.reading, 1, "test")
    rows = [r for r in exam["rows"] if CH.search(r["text"].lower()) and not r["guess_right"]]
    print(f"change/remaining wrong+blocked in g1 test: {len(rows)}\n")
    reader = mind.language.reading.reader()
    for r in rows:
        got, how, trace = reader.solve(r["text"])
        writes = [(s["clause"], s["did"], bool(s.get("sure"))) for s in trace if not s.get("question")]
        qs = [s for s in trace if s.get("question")]
        qdid = qs[0]["did"] if qs else None
        print("=" * 100)
        print(f"want {r['answer']} | brain: {got} ({how})")
        print(f"  {r['text']}")
        for cl, did, sure in writes:
            mark = "SURE" if sure else "??  "
            w = did if did else "NOTHING"
            print(f"   [{mark}] {cl!r} -> {w}")
        if qdid:
            print(f"   [Q  ] {qs[0]['clause']!r} -> {qdid}")


if __name__ == "__main__":
    main()