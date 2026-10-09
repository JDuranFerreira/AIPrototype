"""Plain language models (no brain) on SVAMP and GSM8K: accuracy, time, GPU memory.

  python benchmarks/run_llm.py qwen3:8b nothink 1000 200
  python benchmarks/run_llm.py qwen3:0.6b think 100 50
"""
import json
import random
import re
import sys
import time
import urllib.request
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from run_reader import load_svamp      # noqa: E402

MODEL, MODE, N_SVAMP, N_GSM = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
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


def vram():
    with urllib.request.urlopen(f"{URL}/api/ps") as r:
        for m in json.loads(r.read())["models"]:
            if m["name"].startswith(MODEL):
                return m.get("size_vram", 0) / 1e9, m.get("size", 0) / 1e9
    return 0, 0


svamp = load_svamp("svamp_dev.csv")[:N_SVAMP]
gsm = [json.loads(line) for line in open(HERE / "gsm8k_test.jsonl", encoding="utf-8")]
random.Random(0).shuffle(gsm)
gsm = gsm[:N_GSM]
out = {}
for name, items in [("SVAMP", [(r["text"], r["answer"]) for r in svamp]),
                    ("GSM8K", [(g["question"], Fraction(g["answer"].split("####")[-1].strip().replace(",", ""))) for g in gsm])]:
    t = time.time()
    ok = sum(right(ask(q), a) for q, a in items)
    dt = (time.time() - t) / max(1, len(items))
    out[name] = (ok, len(items), dt)
    print(f"{MODEL} {MODE:7} {name}: {ok}/{len(items)} = {ok / max(1, len(items)):.1%}   {dt:.2f} s per problem", flush=True)
gpu, total = vram()
print(f"{MODEL} loaded: {total:.1f} GB, of which {gpu:.1f} GB on the GPU")
