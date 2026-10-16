"""Three fresh tasks for brain vs qwen (2026-10-12, user asked).

1st math, 2nd language, 3rd code. All items hand-written today: new numbers and
phrasing, never taught, never in any exam. Same items for everyone; the brain answers
in normal mode (learns nothing), qwen at temperature 0 with no thinking.

  python benchmarks/compare_tasks3.py            # brain + qwen3:0.6b + qwen3:8b
  python benchmarks/compare_tasks3.py brain      # brain only
  python benchmarks/compare_tasks3.py qwen3:8b   # one model only
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

MATH = [
    ("A baker packs 9 boxes with 7 muffins in each box. How many muffins are there altogether?", "63"),
    ("Lena shares 56 stickers equally among 8 friends. How many stickers does each friend get?", "7"),
    ("A farmer collects 50 eggs. He packs them in boxes of 6. How many eggs are left over?", "2"),
    ("Tom has 15 marbles. He buys 3 bags with 6 marbles in each bag. How many marbles does he have now?", "33"),
    ("5 notebooks cost 20 dollars. How much do 8 notebooks cost?", "32"),
    ("A shirt costs 40 dollars. There is 25 percent off. What is 25 percent of 40 dollars?", "10"),
    ("A crate is 4 cm long, 5 cm wide and 3 cm high. How many cubic cm are inside the crate?", "60"),
    ("3 eggs make 6 pancakes. How many eggs do you need for 12 pancakes?", "6"),
    ("There are 6 bags with 9 beads in each bag. Mia takes 6 bags and gives away 5 beads. How many beads does Mia have now?", "49"),
    ("Ana scored 84 points on Monday and 96 points on Tuesday. What is her average score?", "90"),
    ("A classroom has 4 rows with 6 desks in each row. 5 desks are broken. How many whole desks are there?", "19"),
    ("A train goes 70 km in one hour. How many km does it go in 4 hours?", "280"),
]

LANGUAGE = [
    ("Tom has 5 apples. He gives 2 apples to Ana. How many apples does Tom have now?", "3"),
    ("Mia has 8 pears. Ana has 3 pears. Ana gives Mia 4 more pears. How many pears does Mia have now?", "12"),
    ("Sam has 6 balls. He finds 3 more balls. He gives 4 balls to his friend. How many balls does Sam have now?", "5"),
    ("Lily has 10 stickers. Her brother has 6 stickers. How many more stickers does Lily have than her brother?", "4"),
    ("Ben has 7 toy cars. His sister takes 2 of his cars. How many cars does Ben have left?", "5"),
    ("There are 12 birds in a tree. 5 birds fly away. 3 more birds come. How many birds are in the tree now?", "10"),
    ("Zoe has 9 marbles. She puts 3 marbles in a box. She puts 2 more marbles in the box. How many marbles are in the box?", "5"),
    ("Raj has 11 pencils. He breaks 2 pencils. How many whole pencils does Raj have now?", "9"),
    ("Ana and Mia pick apples. Ana picks 7 apples. Mia picks 5 apples. They put all the apples in one basket. How many apples are in the basket?", "12"),
    ("Tom has 4 red balls and 3 green balls. How many balls does Tom have altogether?", "7"),
    ("A farmer has 15 cows. He buys 6 more cows. He sells 4 cows. How many cows does the farmer have now?", "17"),
    ("Ella has 20 beads. She gives 5 beads to Sam and 3 beads to Ana. How many beads does Ella have left?", "12"),
]

CODE = [
    ("There are 315 people. Each bus holds 40 people. How many buses are needed?", "8"),
    ("A shop made 96 dollars. It shares the money equally among 8 workers. How much does each worker get?", "12"),
    ("A game hero has 45 health. He loses 18 health. How much health is left?", "27"),
    ("A player scores 150 points. A bonus adds 60 points. What is the total score?", "210"),
    ("A box holds 120 marbles. 35 marbles are taken out. How many marbles are in the box now?", "85"),
    ("A level needs 200 coins. You have 145 coins. How many more coins do you need?", "55"),
    ("plan: total = 6*7; total = total - 2", "40"),
    ("plan: score = 10; if score > 5 then score = score + 5 else score = score - 5", "15"),
    ("plan: counter = 0; for i from 1 to 4 do counter = counter + 3", "12"),
    ("plan: n = 3*4; if n > 10 then for i from 1 to 2 do n = n + n else n = n - 1", "48"),
    ("plan: health = 100; if health > 50 and health < 150 then health = health - 30 else health = health + 10", "70"),
    ("plan: a = 2*9; b = a + 6; b/3", "8"),
]

TASKS = [("math", MATH), ("language", LANGUAGE), ("code", CODE)]
OLLAMA = "http://127.0.0.1:11434"
SYSTEM = ("Solve the problem. Reply with only the final answer: a single number. "
          "Nothing else.")


def numbers(text):
    return [n.replace(",", "").replace(" ", "") for n in
            re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+)?", text)]


def right(got, answer):
    try:
        want = [str(Fraction(n)) for n in re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", answer)]
        return [str(Fraction(n)) for n in got] == want
    except (ValueError, ZeroDivisionError):
        return False


def run_brain():
    from brainlike.regions import Mind
    from brainlike import serve
    mind = Mind.load(HERE.parent / "brain_state")
    assert mind.mode == "normal", f"brain must be in normal mode, is {mind.mode}"
    out, t0 = {}, time.time()
    for name, items in TASKS:
        rows = []
        for task, told in items:
            t = time.time()
            try:
                r = serve.handle(mind, {"action": "ask", "problem": task})
                got = numbers(str(r.get("answer", "")))
            except Exception as e:  # noqa: BLE001
                got, r = [f"ERROR {e}"], {}
            good = right(got, told)
            rows.append({"task": task, "told": told, "got": ", ".join(got), "right": good,
                         "source": r.get("source"), "seconds": round(time.time() - t, 3)})
            print(f"[brain/{name}] {'OK ' if good else 'MISS'} told={told} got={', '.join(got)}"
                  f" src={r.get('source')} :: {task[:65]}", flush=True)
        out[name] = rows
    secs = time.time() - t0
    n = sum(len(v) for v in out.values())
    ok = sum(r["right"] for v in out.values() for r in v)
    print(f"brain: {ok}/{n} in {secs:.1f}s (~{secs / max(1, n) * 1000:.0f} ms/problem)")
    return out


def run_model(model):
    out, t0 = {}, time.time()
    for name, items in TASKS:
        rows = []
        for task, told in items:
            t = time.time()
            body = {"model": model, "stream": False, "think": False,
                    "options": {"temperature": 0, "num_predict": 300},
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": task}]}
            try:
                req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=900) as r:
                    text = json.loads(r.read())["message"]["content"]
                got = numbers(re.sub(r"<think>.*?</think>", "", text, flags=re.S))
            except Exception as e:  # noqa: BLE001
                got = [f"ERROR {e}"]
            good = right(got, told)
            rows.append({"task": task, "told": told, "got": ", ".join(got), "right": good,
                         "seconds": round(time.time() - t, 2)})
            print(f"[{model}/{name}] {'OK ' if good else 'MISS'} told={told} got={', '.join(got)}"
                  f" :: {task[:65]}", flush=True)
        out[name] = rows
    secs = time.time() - t0
    n = sum(len(v) for v in out.values())
    ok = sum(r["right"] for v in out.values() for r in v)
    print(f"{model}: {ok}/{n} in {secs:.1f}s (~{secs / max(1, n):.1f} s/problem)")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    dest = HERE.parent / "results" / "three_tasks_2026-10-12.json"
    data = {"tasks": {name: [{"task": t, "answer": a} for t, a in items] for name, items in TASKS}}
    if which in ("all", "brain"):
        data["brain"] = run_brain()
    for model in (["qwen3:0.6b", "qwen3:8b"] if which == "all" else ([which] if ":" in which else [])):
        data[model] = run_model(model)
    dest.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"-> {dest}")
    for who, out in data.items():
        if who == "tasks":
            continue
        parts = " ".join(f"{name} {sum(r['right'] for r in rows)}/{len(rows)}" for name, rows in out.items())
        tot = sum(r["right"] for rows in out.values() for r in rows)
        n = sum(len(rows) for rows in out.values())
        print(f"{who}: {parts} | total {tot}/{n}")


if __name__ == "__main__":
    main()
