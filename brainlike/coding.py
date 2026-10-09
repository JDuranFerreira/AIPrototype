"""The code lesson: taught tools, taught procedures, then running and checking programs.

It is a school lesson like any other: the teacher shows worked examples, the brain keeps a tool or
a recipe only if it reproduces every example with its own procedure, and then an exam on fresh
questions asks whether it can use them on its own.

  python -m brainlike.coding              # teach, use, exam, and save the brain
  python -m brainlike.coding --dry-run    # same, saving nothing
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import request, serve
from .regions import Mind

ABOUT = ("tools taught with worked examples (what is left over, a power, which is bigger, numbers in "
         "order, counting on), recipes that turn a sentence into a program, and programs run and "
         "checked step by step")

# ---- what the teacher shows, tool by tool: (what it's called, the arguments, the answer) ------------
TOOLS = {
    "%": [("what is left over", (17, 5), "2"), ("what is left over", (23, 7), "2"), ("what is left over", (19, 4), "3")],
    "^": [("a power", (2, 5), "32"), ("a power", (3, 3), "27"), ("a power", (10, 2), "100")],
    "c": [("which is bigger", (8, 3), ">"), ("which is bigger", (3, 8), "<"), ("which is bigger", (5, 5), "="),
          ("which is bigger", (12, 12), "=")],
    "s": [("put numbers in order", ([5, 3, 9, 1],), "1, 3, 5, 9"), ("put numbers in order", ([12, 4, 40],), "4, 12, 40")],
    "n": [("count on", (3, 7), "3, 4, 5, 6, 7"), ("count on", (10, 14), "10, 11, 12, 13, 14")],
}

# ---- recipes: a word pattern -> the program to write for it -------------------------------------------
PEOPLE = r"people|pupils?|children|kids?|boys?|girls?|students?|friends?|passengers?|guests?"
BOXES = r"boxes|bags|crates|trays|packs|jars|baskets|sheets?"
PROCEDURES = [
    {"name": "how many needed", "said": "each one holds a number of people, so how many are needed",
     "pattern": r"each\b.*\b(?:holds?|can hold|fits?|seats?)\b", "plan": "{n1} divup {n2}",
     "asks": "needed", "container": PEOPLE,
     "examples": [["There are 428 people. Each car holds 11 people. How many cars are needed?", "428 divup 11"],
                  ["260 pupils are going on a trip. Each table holds 26 pupils. How many tables are needed?",
                   "260 divup 26"]]},
    {"name": "how many needed, each one first",
     "said": "how many ride in each: the per-one number comes after the total",
     "pattern": r"\bcan\s+(?:hold|ride|sit|fit)s?\s+in\s+each\b|\bper\s+(?:child|person|box|bag|basket|table|car|bus|boat|tent|tray|crate|jar|sheet|row|shelf|pack)\b",
     "plan": "{n1} divup {n2}",
     "asks": "needed", "container": PEOPLE,
     "examples": [["32 children are going on a trip. 3 children can ride in each tent. How many tents do they need?",
                   "32 divup 3"],
                  ["12 kids are going on a trip. 4 kids can sit in each bus. How many buses do they need?",
                   "12 divup 4"]]},
    {"name": "how many in each", "said": "each one has a number of things, so how many in all",
     "pattern": r"each\b.*\bhas\b", "plan": "{n1}*{n2}",
     "asks": ["all", "count"], "container": BOXES,
     "examples": [["Lily bought 72 jars of sandwiches. Each jar has 12 sandwiches. How many sandwiches?", "72*12"],
                  ["There are 12 trays. Each tray has 9 cups. How many cups are there?", "12*9"]]},
    {"name": "share between", "said": "share equally between some number of people",
     "pattern": r"shar(?:e|ed)\b.*\bbetween\b", "plan": "{n1} div {n2}",
     "asks": ["each"],
     "examples": [["Share 24 sweets between 6 children. How many does each child get?", "24 div 6"],
                  ["72 marbles shared between 8 friends: how many each?", "72 div 8"]]},
    {"name": "three steps", "said": "some things, each holding some, minus a few, shared between friends",
     "pattern": r"\b(?:bags|boxes|packs|jars|trays|crates)\s+(?:of|with)\b", "plan": "total = {n1}*{n2}; left = total-{n3}; left/{n4}",
     "asks": ["each", "count"], "container": BOXES,
     "examples": [["I have 3 bags of 4 apples. I eat 2. Share the rest between 5 friends.",
                   "total = 3*4; left = total-2; left/5"],
                  ["There are 5 boxes with 7 pens in each. Raj gives away 4 pens and shares the rest between "
                   "2 children. How many pens does each child get?", "total = 5*7; left = total-4; left/2"]]},
    {"name": "boxes each, minus some",
     "said": "so many boxes with so many in each, and some are taken away; 'away' is named, so the same "
             "number may appear twice in the sentence",
     "pattern": r"\b(?:boxes|bags|crates|trays|packs)\s+with\b.*\bin\s+each\b",
     "plan": "total = {n1}*{n2}; left = total-{gives away|eats|ate|breaks|broke|lost|loses}",
     "asks": ["count", "left"], "container": BOXES,
     "examples": [["There are 14 boxes with 6 pens in each. Raj gives away 10 pens. How many pens does Raj have now?",
                   "total = 14*6; left = total-10"],
                  ["There are 9 bags with 5 apples in each. Kim eats 7 apples. How many apples does Kim have?",
                   "total = 9*5; left = total-7"],
                  ["There are 14 boxes with 6 pens in each. Raj takes 14 boxes and gives away 10 pens. "
                   "How many pens does Raj have now?", "total = 14*6; left = total-10"]]},
    {"name": "price of each, then how many",
     "said": "so many cost so much, so first find the price of one (the total cost comes before the question)",
     "pattern": r"\bcost\b[^.?]*\bhow much\b|\bhow much (?:do|does|would)\b", "plan": "each = {n2} div {n1}; {n3}*each",
     "asks": ["money", "count"],
     "examples": [["5 pens cost 15 dollars. How much do 8 pens cost?", "each = 15 div 5; 8*each"],
                  ["3 tickets cost 21 dollars. How much do 7 tickets cost?", "each = 21 div 3; 7*each"]]},
    {"name": "times as many", "said": "so many times as many",
     "pattern": r"\btimes as (?:many|much)\b", "plan": "{n1}*{n2}",
     "examples": [["Ana has 12 pens. Raj has 3 times as many. How many pens does Raj have?", "12*3"],
                  ["There were 15 birds. Last year there were 4 times as many. How many birds were there last year?",
                   "15*4"]]},
    {"name": "percent of", "said": "a percent is a part of a hundred: the whole times the percent, over a hundred",
     "pattern": r"\bpercent\b", "plan": "{n2}*{n1}/100",
     "asks": ["money", "count"],
     "examples": [["What is 10 percent of 250?", "250*10/100"],
                  ["What is 5 percent of 80 dollars?", "80*5/100"]]},
    {"name": "box volume", "said": "long times wide times high",
     "pattern": r"\b(?:long|wide|high|tall)\b", "plan": "{n1}*{n2}*{n3}",
     "asks": ["count"],
     "examples": [["A box is 3 cm long, 4 cm wide and 2 cm high. How many cubic cm are inside?", "3*4*2"],
                  ["A case is 5 cm long, 2 cm wide and 6 cm high. How many cubic cm are inside?", "5*2*6"]]},
    {"name": "average of two", "said": "add the two and share between two",
     "pattern": r"\baverage\b", "plan": "({n1}+{n2})/2",
     "asks": ["count"],
     "examples": [["Ana scored 70 and then 90. What is Ana's average score?", "(70+90)/2"],
                  ["Ben had 40 marbles and then 60. What is Ben's average?", "(40+60)/2"]]},
    {"name": "how many more", "said": "the first number minus the second",
     "pattern": r"\bhow many (?:more|less|fewer)\b", "plan": "{n1}-{n2}",
     "asks": ["count", "all"],
     "examples": [["Ana has 20 pears. Raj has 8 pears. How many more pears does Ana have?", "20-8"],
                  ["There are 15 red beads and 9 blue beads. How many fewer red beads are there than blue beads?",
                   "15-9"]]},
    {"name": "two groups together", "said": "add the two groups",
     "pattern": r"\b(?:boys and|girls and|red and|blue and|apples and|pens and)\b.*\bhow many\b",
     "plan": "{n1}+{n2}",
     "asks": ["all", "count"], "not_about": r"red|blue|green|yellow|boys|girls",
     "examples": [["There are 12 boys and 15 girls in the class. How many children are there?", "12+15"],
                  ["A shop has 30 red pens and 42 blue pens. How many pens are there?", "30+42"]]},
]

# ---- programs it runs and checks ---------------------------------------------------------------------
PROGRAMS = [
    "plan: total = 6*7; left = total-2; left/5",
    "plan: apples = 3*4; apples-2",
    "plan: jars = 12*12; jars-7",
    "plan: boxes = 144/12; boxes+1",
    "plan: total = 10; if total > 5 then total = total + 1 else total = total - 1",
    "plan: total = 2; if total > 5 then total = total + 1 else total = total - 1",
    "plan: counter = 0; for i from 1 to 4 do counter = counter + 2",
    "plan: counter = 1; for i from 1 to 3 do counter = counter * counter",
    "plan: n = 3*4; if n > 10 then for i from 1 to 2 do n = n + n else n = n - 1",
]

TASKS = ["17%5", "2^10", "8 > 3", "12 < 12", "sort 9, 4, 7, 1, 4", "count on from 2 to 9"]

# ---- the exam: fresh questions it has never been taught, with the right answers -----------------------
# About a third are traps: the same words as a taught recipe but asking for something else ("how many
# boxes are there?" when the recipe counts the pens inside the boxes). Those prove it read the request
# instead of matching words.
EXAM = [
    ("There are 253 people. Each car holds 5 people. How many cars do they need?", "51"),
    ("There are 600 apples. There are 24 per basket. How many baskets are needed?", "25"),
    ("48 pens shared between 8 friends: how many each?", "6"),
    ("There are 8 boxes with 7 pencils in each. Ana gives away 9 pencils. How many pencils does Ana have?", "47"),
    ("sort 7, 2, 9, 4", "2, 4, 7, 9"),
    ("count on from 5 to 9", "5, 6, 7, 8, 9"),
    ("2^6", "64"),
    ("17 % 4", "1"),
    ("plan: total = 9*7; total-5", "58"),
    ("plan: n = 4; if n > 2 then n = n * 10 else n = n + 1", "40"),
    # --- traps: the same words, a different question ---
    ("There are 8 boxes with 7 pencils in each. How many boxes are there?", "8"),
    ("There are 253 people. Each car holds 5 people. How many people are in one car?", "5"),
    ("72 marbles shared between 8 friends. How many marbles are there?", "72"),
    ("5 pens cost 15 dollars. How many pens cost 15 dollars?", "5"),
    ("Each jar has 12 sandwiches. There are 72 jars. How many jars are there?", "72"),
    ("There are 30 red pens and 42 blue pens. How many red pens are there?", "30"),
    # --- more plain English, fresh sentences ---
    ("12 kids are going on a trip. 4 kids can sit in each bus. How many buses do they need?", "3"),
    ("Ana has 12 pens. Raj has 3 times as many. How many pens does Raj have?", "36"),
    ("What is 10 percent of 250?", "25"),
    ("A box is 3 cm long, 4 cm wide and 2 cm high. How many cubic cm are inside?", "24"),
    ("Ana scored 70 and then 90. What is Ana's average score?", "80"),
    ("Ana has 20 pears. Raj has 8 pears. How many more pears does Ana have?", "12"),
    ("There are 12 boys and 15 girls in the class. How many children are there?", "27"),
    ("3 tickets cost 21 dollars. How much do 7 tickets cost?", "49"),
]


def _run(mind, task):
    """One task through the brain -> the reply."""
    return serve.handle(mind, {"action": "ask", "problem": task})


def _checks_ok(reply):
    checks = reply.get("checked")
    if isinstance(checks, str):
        return "\u2713" in checks
    return bool(checks) and all(c.get("ok") for c in checks)


def what_is_asked(sentence):
    """Read the request in a question: what kind of answer it wants, and about what."""
    return request.what_is_asked(sentence)


def teach(mind, log=print):
    """The teacher shows every example; the brain keeps a tool or a recipe only if it matches them all.
    Each recipe is told what question it answers and what it counts inside, so it stays quiet on a
    question it was not taught to answer."""
    tools, recipes = [], []
    for op, examples in TOOLS.items():
        kept = []
        for phrase, args, told in examples:
            good, _ = mind.coordination.teach_arithmetic(op, [(tuple(args), told)], said=phrase)
            kept.append(good)
        tools.append((op, all(kept)))
        log(f"  tool {op}: {'kept' if all(kept) else 'NOT kept'} ({sum(kept)}/{len(kept)} examples)")
    for p in PROCEDURES:
        kept, work = mind.coordination.teach_procedure(
            p["name"], p["said"], p["pattern"], p["plan"], [tuple(e) for e in p["examples"]],
            asks=p.get("asks"), not_about=p.get("not_about") or p.get("container"))
        recipes.append((p["name"], kept))
        log(f"  recipe {p['name']}: {'kept' if kept else 'NOT kept'}")
        for w in work:
            if not w["matched"]:
                log(f"    {w['sentence'][:66]}\n      it wrote: {w['its_plan']}  |  you said: {w['your_plan']}")
    return tools, recipes


def use(mind, log=print):
    """Now it uses them on its own: every answer carries a check that undoes it."""
    ok_tasks = sum(1 for t in TASKS if _checks_ok(_run(mind, t)))
    steps = total = 0
    for plan in PROGRAMS:
        reply = _run(mind, plan)
        checks = reply.get("checked") or []
        total += len(checks)
        steps += sum(1 for c in checks if c.get("ok"))
    log(f"  tasks: {ok_tasks}/{len(TASKS)} answered with a check")
    log(f"  programs: {len(PROGRAMS)} run, {steps}/{total} steps checked by undoing")
    return {"tasks": [len(TASKS), ok_tasks], "programs": [len(PROGRAMS), total, steps]}


def take_exam(mind, log=print):
    """Fresh questions, never taught: can it use what it learned?"""
    rows = []
    for task, told in EXAM:
        reply = _run(mind, task)
        got = None if reply.get("answer") is None else str(reply["answer"])
        ok = got == told
        rows.append({"task": task, "answer": told, "got": got, "ok": ok,
                     "checked": _checks_ok(reply), "how": reply.get("read_as") or reply.get("how")})
        log(f"  {'✓' if ok else '✗'} {task[:60]} -> {got} (right: {told})")
    right = sum(r["ok"] for r in rows)
    return {"n": len(rows), "right": right, "score": right / len(rows) if rows else 0.0, "rows": rows}


def run_level(mind, log=print):
    """A full round: the exam BEFORE the lesson (what it could already do), then the lesson, then the
    exam again on exactly the same questions, then a line for the report card. The difference is the
    lesson's own worth, measured rather than claimed."""
    before = take_exam(mind, lambda *_: None)
    log(f"code exam before the lesson: {before['score']:.0%} ({before['right']}/{before['n']})")
    log("code lesson: tools")
    tools, recipes = teach(mind, log)
    log("code lesson: using them")
    used = use(mind, log)
    log("code exam (the same fresh questions again)")
    exam = take_exam(mind, log)
    learned = [r["task"] for r, b in zip(exam["rows"], before["rows"])
               if r["ok"] and not b["ok"]]
    log(f"the lesson taught it {len(learned)} of the questions it could not do before")
    entry = {"level": "code", "subject": "code", "about": ABOUT, "round": 1,
             "tools": {"kept": sum(k for _, k in tools), "of": len(tools)},
             "recipes": {"kept": sum(k for _, k in recipes), "of": len(recipes)},
             "used": used, "score": exam["score"], "before": before["score"], "learned": learned,
             "learned_n": len(learned),
             "grade": "AL1" if exam["score"] >= 0.9 else
             ("AL2" if exam["score"] >= 0.8 else "needs practice"),
             "predicted": used["tasks"][1] / len(TASKS), "mastered": all(k for _, k in tools)
             and all(k for _, k in recipes) and exam["score"] >= 0.8,
             "attempts": [{"exam": "code", "score": exam["score"]}],
             "strengths": [t for t in TASKS if any(r["task"] == t and r["ok"] for r in exam["rows"])],
             "work_on": [f"{t} ({sum(1 for r in exam['rows'] if r['task'] == t and not r['ok'])} wrong)"
                         for t in TASKS + [p for p, _ in EXAM] if any(r["task"] == t and not r["ok"] for r in exam["rows"])],
             "exam": exam, "date": date.today().isoformat()}
    return entry


def main():
    if hasattr(sys.stdout, "reconfigure"):      # the working has − and ✓ in it: don't let the code page crash us
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(Path(__file__).resolve().parent.parent / "brain_state"))
    ap.add_argument("--dry-run", action="store_true", help="teach a copy and save nothing")
    args = ap.parse_args()
    mind = Mind.load(args.state)
    entry = run_level(mind)
    print(f"\ncode: {entry['tools']['kept']}/{entry['tools']['of']} tools, "
          f"{entry['recipes']['kept']}/{entry['recipes']['of']} recipes, "
          f"exam {entry['before']:.0%} before -> {entry['score']:.0%} after -> {entry['grade']} "
          f"({entry['learned_n']} questions the lesson taught it)")
    if not args.dry_run:
        from . import primary
        primary.file_report(mind, entry, subject="code")
        mind.save(args.state)
        print(f"saved to {args.state}")
    print(json.dumps({k: v for k, v in entry.items() if k != "exam"}, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
