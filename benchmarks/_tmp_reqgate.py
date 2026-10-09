"""Read-only: where does the story reader's request gate stand? The code-exam traps (questions whose
words match a taught recipe but ask something else), the whole code exam, and the ASDiv grade-1 gate.
Checks brain_state is byte-identical before and after."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brainlike import coding, primary, serve                 # noqa: E402
from brainlike.regions import Mind                           # noqa: E402

STATE = HERE.parent / "brain_state"


def md5s():
    return {p.relative_to(STATE).as_posix(): __import__("hashlib").md5(p.read_bytes()).hexdigest()
            for p in sorted(STATE.rglob("*")) if p.is_file()}


before = md5s()
mind = Mind.load(STATE, {"model": "none", "url": ""})

print("== code exam traps (want -> got, source) ==")
for task, want in coding.EXAM:
    r = serve.handle(mind, {"action": "ask", "problem": task})
    got = r.get("answer")
    mark = "ok " if str(got) == want else "WRONG"
    print(f"  {mark} want {want!r:>8} got {str(got)!r:>8}  src={r.get('source')} "
          f"{r.get('not_sure') or r.get('note') or ''}  :: {task[:70]}")

exam = coding.take_exam(mind, lambda *_: None)
print(f"code exam: {exam['score']:.0%} ({exam['right']}/{exam['n']})")

t = primary.outside_exam(mind.language.reading, 1, "test")
print(f"ASDiv g1 TEST: right {t['right']}/{t['n']}, claims {t['understood']} "
      f"({100 * t['right'] / t['understood']:.0f}% true), always answers {t['guess_right']}")

after = md5s()
diff = [k for k in before if before[k] != after.get(k)] + [k for k in after if k not in before]
print("brain_state changed by this run:", diff or "nothing (byte-identical)")
