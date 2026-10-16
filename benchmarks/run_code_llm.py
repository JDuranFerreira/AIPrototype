"""A plain language model (no brain) on the code lesson's exam: the same fresh questions
the brain is examined on (word problems, traps, and plan: programs it must execute).

The brain's exam answers are single numbers or ordered number lists ("2, 4, 7, 9"),
so the model is asked for exactly that shape, and graded on the full ordered list:

  python benchmarks/run_code_llm.py qwen3:0.6b nothink   -> results/code_qwen3-0.6b_nothink.json
  python benchmarks/run_code_llm.py qwen3:8b nothink     -> results/code_qwen3-8b_nothink.json
"""
import json
import re
import sys
import time
import urllib.request
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from brainlike import coding  # noqa: E402

MODEL, MODE = sys.argv[1], sys.argv[2]
SYSTEM = ("Solve the problem. Reply with only the final answer: a single number, "
          "or the numbers in order separated by commas. Nothing else.")
URL = "http://127.0.0.1:11434"


def ask(question):
    body = {"model": MODEL, "stream": False, "think": MODE == "think",
            "options": {"temperature": 0, "num_predict": 4096 if MODE == "think" else 300},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]}
    req = urllib.request.Request(f"{URL}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        text = json.loads(r.read())["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return [n.replace(",", "").replace(" ", "") for n in re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+)?", text)]


def right(got, answer):
    try:
        want = [str(Fraction(n)) for n in re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", answer)]
        return [str(Fraction(n)) for n in got] == want
    except (ValueError, ZeroDivisionError):
        return False


out, ok, t0 = [], 0, time.time()
for i, (task, told) in enumerate(coding.EXAM):
    t = time.time()
    try:
        got = ask(task)
    except Exception as e:  # noqa: BLE001 - one failure must not lose the batch
        got = [f"ERROR {e}"]
    good = right(got, told)
    ok += good
    out.append({"i": i, "task": task, "told": told, "got": ", ".join(got), "right": good,
                "seconds": round(time.time() - t, 2)})
    print(f"[{i + 1}/{len(coding.EXAM)}] {'OK ' if good else 'MISS'} told={told} got={', '.join(got)} :: {task[:70]}",
          flush=True)
n = len(coding.EXAM)
dest = HERE / "results" / f"code_{MODEL.replace(':', '-')}_{MODE}.json"
dest.write_text(json.dumps({"model": MODEL, "mode": MODE, "n": n, "right": ok,
                            "seconds_per_problem": round((time.time() - t0) / max(1, n), 2),
                            "answers": out}, indent=1), encoding="utf-8")
print(f"{MODEL} {MODE} code: {ok}/{n} = {ok / max(1, n):.1%} -> {dest.name}")
