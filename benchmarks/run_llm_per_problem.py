"""A plain language model (no brain) on the first N SVAMP problems (or an ASDiv grade), saving every
answer, so the brain can be compared on exactly the same problems (and on any subset of them).

  python benchmarks/run_llm_per_problem.py qwen3:0.6b nothink 300          -> results/svamp300_qwen3-0.6b_nothink.json
  python benchmarks/run_llm_per_problem.py qwen3:0.6b nothink asdiv1       -> results/asdiv1_qwen3-0.6b_nothink.json
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
sys.path.insert(0, str(HERE))
from asdiv import load_asdiv           # noqa: E402
from run_reader import load_svamp      # noqa: E402

MODEL, MODE, WHICH = sys.argv[1], sys.argv[2], sys.argv[3]
SYSTEM = "Solve the math word problem. Reply with only the final answer as a number, nothing else."
URL = "http://127.0.0.1:11434"


def ask(question):
    body = {"model": MODEL, "stream": False, "think": MODE == "think",
            "options": {"temperature": 0, "num_predict": 4096 if MODE == "think" else 300},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]}
    req = urllib.request.Request(f"{URL}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        text = json.loads(r.read())["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    nums = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+)?", text)
    return nums[-1].replace(",", "") if nums else None


def right(got, answer):
    try:
        return got is not None and Fraction(got) == answer
    except (ValueError, ZeroDivisionError):
        return False


rows = load_asdiv(int(WHICH[5:])) if WHICH.startswith("asdiv") else load_svamp("svamp_dev.csv")[:int(WHICH)]
N = len(rows)
NAME = WHICH if WHICH.startswith("asdiv") else f"svamp{N}"
out, ok, t0 = [], 0, time.time()
for i, r in enumerate(rows):
    t = time.time()
    got = ask(r["text"])
    good = right(got, r["answer"])
    ok += good
    out.append({"i": i, "got": got, "right": good, "seconds": round(time.time() - t, 2)})
    if (i + 1) % 50 == 0:
        print(f"{MODEL} {MODE}: {ok}/{i + 1}", flush=True)
dest = HERE / "results" / f"{NAME}_{MODEL.replace(':', '-')}_{MODE}.json"
dest.parent.mkdir(exist_ok=True)
dest.write_text(json.dumps({"model": MODEL, "mode": MODE, "n": N, "right": ok,
                            "seconds_per_problem": round((time.time() - t0) / max(1, N), 2), "answers": out}, indent=1),
                encoding="utf-8")
print(f"{MODEL} {MODE} {NAME}: {ok}/{N} = {ok / max(1, N):.1%} -> {dest.name}")
