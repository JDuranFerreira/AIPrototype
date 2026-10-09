"""JSON command interface, so other apps (the AgenticOS "Brain" tab) can talk
to the brain. Reads one JSON command on stdin, prints one JSON reply.

  echo {"action": "ask", "problem": "3+4"} | python -m brainlike.serve --state brain_state

The brain has seven regions (see regions.py) and every question goes to one:
  language    words and word meanings, grammar, sentences, reading stories (the
              reading engine) and learned phrases; answers first when it can act
              a story out, and otherwise works out what you mean and says it
              back in the brain's own language for you to confirm
  knowledge   facts about the world (capital of france = Paris): told to it,
              or learned from scenes
  memory      the episodes it lived through, replayed in sleep
  arithmetic  single-digit facts (3+4) learned by trial and error in one section
              per operation; bigger math (10*10, 7/2) worked out from those facts;
              rules with letters (n/n = 1) used as shortcuts, or to work out facts
              it doesn't know (a*b = a*(b-1)+a)
  prefrontal  plans with several steps ("plan: a = 3*4; a-2") and working memory
  coordination the TOOLS (count up in groups, work out a percent, common factors,
              ...), which of them it was taught, where each may be used, how well
              each pays off, and action selection - for a fact it doesn't know:
              guess or work it out? learned from rewards (strategy.py, basal ganglia)
  monitor     confidence and number sense on every math answer; doubts

The report card (levels, exams, grades) is bookkeeping, not a region: `stats`
returns it separately as `report_card`.

Actions
  ask          {problem, mistakes, literal}           answer, guess, worked-out steps, or "understood"
  feedback     {problem, guess, correct, mistakes, worked}  teacher says yes/no
  tell         {problem, answer, mistakes}             teacher gives the answer to the current question
  teach        {problem, answer, literal}              "problem = answer": it answers first, then learns
  learn_phrase {text, meaning}                         teacher confirmed what a sentence means
  auto         {problem}                               the built-in math checker teaches it
  rule         {rule, accept}                          teacher's verdict on a rule the brain noticed
  kindergarten {lesson, rounds}                        lessons from the simulated world: words, facts, actions,
                                                       stories, all; or exam (new stories, read only); or P1 / P2:
                                                       one level of the world-based primary school (primary.py)
  notice | rules | doubts | sleep {rounds} | exam | stats | forget {problem} | reset
  mode   {mode}                            normal (it just answers, default) or training (it learns from you)

The language region's reading engine answers first when it can: stories with a question ("Mia has 7 cookies. She eats 2.
How many cookies does Mia have now?") are acted out; "what is red?", "how many legs does a puppy have?";
facts like "a zebra has four legs". A story with its answer ("... now? = 5") teaches it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from . import compose, english_chat, equations, monitor, planner, rules, task
from .coordination import ARITH_TOOLS
from .language import LanguageError
from .reading import Reading
from .regions import Mind, new_arithmetic

# "ask" changes the brain too: number sense throws out impossible guesses, the section learns from that,
# and working memory keeps the answer
MUTATING = {"ask", "feedback", "tell", "teach", "auto", "sleep", "forget", "reset", "rule", "learn_phrase",
            "english_rule", "solving_rule", "kindergarten", "school_exam", "mode", "teach_procedure", "code_lesson"}
_KG_FACT = re.compile(r"^\s*an? [a-z]+ (?:has [a-z]+ legs|says [a-z]+|can [a-z]+|is an? young [a-z]+)\s*\.?\s*$", re.I)
_KG_ISA = re.compile(r"^\s*an? [a-z]+ is an? [a-z]+\s*\.?\s*$", re.I)
_MATHY = re.compile(r"^[\d\s.+\-*xX×·/÷()%^]+$")
_ASKING = re.compile(r"^\s*(what\s+is|what's|how\s+much\s+is|calculate|compute|solve)\s+", re.I)


def classify(text):
    """-> (key, kind) with kind 'basic', 'big', 'rule' or 'free'."""
    math = _ASKING.sub("", text).strip().rstrip("?").strip()   # "what is 7/2?" -> "7/2"
    if "$" in math and _MATHY.match(math.replace("$", "")):
        math = math.replace("$", "")                            # $4.50 + $2.75: a dollar sign is just a label
    if rules.is_rule(math):
        return compose.normalize(math, variables=True), "rule"
    try:
        key = compose.normalize(math)
    except ValueError:
        if _MATHY.match(math):
            raise                          # it is math, just mistyped (like 3++4): say what's wrong
        return " ".join(text.lower().strip().rstrip("?").split()), "free"
    return key, "basic" if compose.is_basic(key) else "big"


def same(a, b):
    try:
        return compose.to_value(a) == compose.to_value(b)
    except ValueError:
        return str(a).strip().lower() == str(b).strip().lower()


def stats(mind):
    brain = mind.arithmetic
    regions = mind.regions()
    by = {r["name"]: r for r in regions}
    sections = by["arithmetic"]["sections"]
    wrong = sorted(p for p, f in brain.memory.items() if not task.check(p, f["answer"]))
    quality = exam(brain)
    for s in sections:                     # each section's own exam result
        if s["op"]:
            s["exam"] = quality["by_op"][s["op"]]
    return {"regions": regions, "report_card": mind.report_card(), "quality": quality, "usage": mind.usage,
            "mode": mind.mode,
            "basic_known": sum(s["facts"] for s in sections), "total_problems": len(task.all_problems()),
            "big_known": by["arithmetic"]["bigger_problems"], "free_known": by["knowledge"]["facts"],
            "rules_known": by["arithmetic"]["rules"],
            "phrases_known": by["language"]["phrases"] + by["language"]["patterns"],
            "total_weights": brain.total_params, "active_weights": brain.active_params, "taught_wrong": wrong}


def exam(brain):
    """Only single-digit problems it has NOT learned. Two scores: what the
    sections guess on their own (intuition), and what it gets when it may
    also use its rules to work facts out (understanding)."""
    unseen = [p for p in task.all_problems() if p not in brain.memory]
    by_op = {op: [0, 0, 0, 0] for op in task.OPS}
    for p in unseen:
        s = by_op[task.parse(p)[1]]
        s[0] += task.check(p, brain.first_guess(p)[0])
        s[1] += task.check(p, int(brain.work_out(p)[0]))
        s[2] += 1
        s[3] += task.check(p, self_checked_guess(brain, p, [], learn=False)[0]["answer"])
    n = len(unseen)

    def total(i):
        return sum(s[i] for s in by_op.values()) / n if n else None
    return {"unseen": n, "right": sum(s[0] for s in by_op.values()), "score": total(0), "understanding": total(1),
            "self_checked": total(3),
            "by_op": {op: {"right": s[0], "understood": s[1], "self_checked": s[3], "of": s[2]} for op, s in by_op.items()}}


def self_checked_guess(brain, problem, mistakes, learn=True):
    """A section's guess, checked by number sense first: a guess that can't
    be right is thrown out (and the section learns from it) before the
    teacher ever sees it."""
    rejected = []
    g = brain.next_guess(problem, mistakes)
    while len(rejected) < 40:
        s = monitor.sense(problem, g["answer"])
        v = monitor.verify(brain, problem, g["answer"]) if not s or s["ok"] else None
        if (not s or s["ok"]) and not (v and not v["ok"]):
            g = {**g, "verified": v}             # passed number sense, and the undo check if it could do one
            break
        rejected.append(g["answer"])             # can't be right: too far off, or undoing it doesn't work
        if learn:
            brain.feedback(problem, g["answer"], False)
        g = brain.next_guess(problem, list(mistakes) + rejected)
    return g, rejected


def tool_ops(problem):
    """Which arithmetic tools this problem needs ('%' = what's left over, '^' = a power)."""
    flat = problem.replace(" ", "")
    return [op for op in ("%", "^") if op in flat]


def solve_tool(mind, problem):
    """A tool the teacher taught it answers this: the tool's own working, and a check by undoing it."""
    tree = compose.parse(problem)
    args = [compose.evaluate(t) for t in tree[1:3]]
    v, work, check = mind.coordination.arith_work(tree[0], args)
    return {"problem": problem, "source": "tool", "tool": tree[0], "answer": compose.fmt(v), "how": work,
            "checked": check, "confidence": 1.0 if "\u2713" in check else 0.5}


_CMP = re.compile(r"^\s*(-?[\d.]+(?:/\d+)?)\s*(<=|>=|<|>|=)\s*(-?[\d.]+(?:/\d+)?)\s*$")
_SORT = re.compile(r"^\s*sort\s+(.+)$", re.I)
_COUNT = re.compile(r"^\s*count\s+(?:on\s+)?from\s+(-?\d+)\s+to\s+(-?\d+)\s*$", re.I)


def coding_tool(problem):
    """A plain-language problem that needs one of the taught-by-examples tools ('c' compare, 's' put in
    order, 'n' count on). -> (op, args, how to say it) or None."""
    m = _CMP.match(problem or "")
    if m:
        return "c", [compose.to_value(m.group(1)), compose.to_value(m.group(3))], f"{m.group(1)} {m.group(2)} {m.group(3)}"
    m = _SORT.match(problem or "")
    if m:
        numbers = [compose.to_value(t) for t in re.findall(r"-?[\d.]+(?:/\d+)?", m.group(1))]
        return ("s", [numbers], f"sort {', '.join(compose.fmt(n) for n in numbers)}") if len(numbers) > 1 else None
    m = _COUNT.match(problem or "")
    if m:
        return "n", [int(m.group(1)), int(m.group(2))], f"count on from {m.group(1)} to {m.group(2)}"
    return None


def solve_coding_tool(mind, asked):
    """One of the taught algorithm tools answers it, with its working and a check that undoes it."""
    op, args, said = asked
    v, work, check = mind.coordination.arith_work(op, args)
    return {"problem": said, "source": "tool", "tool": op, "answer": v if isinstance(v, str) else compose.fmt(v),
            "how": work, "checked": check, "confidence": 1.0 if "\u2713" in check else 0.5}


_COUNT_LIKE = {"count", "all", "needed", "each", "money", "left"}


def _impossible_count(reply, asked):
    """A count of things cannot be negative, so a program that ends in a negative number has not
    answered the question - it has only shown it does not understand it. The brain says so instead
    of reporting a negative number of cars."""
    if asked.get("kind") not in _COUNT_LIKE:
        return ""
    answer = reply.get("answer")
    try:
        number = float(str(answer))
    except (TypeError, ValueError):
        return ""
    return ("it worked out a negative number for a count of things, so it does not understand this one"
            if number < 0 else "")


def run_words(mind, text, plans):
    """First read what is being asked; then a taught recipe writes a program for the sentence, the
    prefrontal runs it and checks every step. If more than one recipe fits, the one whose steps all
    check out wins; a program that ends in an impossible count is ignored; if nothing works, it says
    what it could not do and ticks its doubt memory."""
    asked = mind.coordination.what_is_asked(text)
    tried, best = [], None
    for name, plan in plans:
        try:
            reply = solve_plan(mind, plan)
        except ValueError as e:
            tried.append({"procedure": name, "plan": plan, "error": str(e)})
            continue
        impossible = _impossible_count(reply, asked)
        checks = reply.get("checked") or []
        ok = bool(checks) and all(c.get("ok") for c in checks) and not impossible
        tried.append({"procedure": name, "plan": plan, "answer": reply.get("answer"), "ok": ok,
                      "checked": f"{sum(1 for c in checks if c.get('ok'))}/{len(checks)}",
                      "why_not": impossible})
        if ok:
            return {**reply, "problem": text, "read_as": plan, "procedure": name, "asked": asked,
                    "tried": tried}
        if best is None and not impossible:
            best = (reply, name, plan)
    if best is None:
        silent = [{"procedure": n, "why": mind.coordination.why_not(n, text)}
                  for n in mind.coordination.procedures if mind.coordination.why_not(n, text)]
        mind.doubts.doubt("request", f"nothing could answer '{text[:50]}' - it wants {asked['said']}")
        return {"problem": text, "source": "procedure", "asked": asked, "tried": tried,
                "not_sure": [f"it wants {asked['said']}, and no taught recipe answers that"] +
                           [f"{s['procedure']}: {s['why']}" for s in silent[:3]],
                "note": "it read what was asked, but had no recipe that answers it"}
    reply, name, plan = best
    mind.doubts.doubt("procedure", f"a recipe wrote '{plan}' for: {text[:50]}")
    return {**reply, "problem": text, "read_as": plan, "procedure": name, "asked": asked, "tried": tried,
            "not_sure": [f"the steps of '{plan}' did not all check out"]}


def solve_math(mind, problem, kind, mistakes=()):
    """Every math question goes through here: memory, rules, the strategy
    chooser (guess or work it out), the monitor's checks, written methods."""
    brain = mind.arithmetic
    mistakes = list(mistakes)
    if problem in brain.memory:
        k = brain.memory[problem]["module"]
        return {"problem": problem, "answer": brain.memory[problem]["answer"], "source": "memory", "module": k,
                "section": brain.section_name(k) if k is not None else None, "confidence": 1.0}
    if kind == "basic":
        by_rule = rules.apply_to(brain, problem)
        if by_rule is not None and not any(same(by_rule[0], m) for m in mistakes):
            return {"problem": problem, "source": "rule", "answer": int(by_rule[0]), "rule": by_rule[1], "confidence": 1.0}
        section = brain.section_name(brain._route(task.encode(problem)))
        derived = None if mistakes else worked_out(brain, problem)
        options = (["derive"] if derived else []) + ["guess"]
        choice, why = mind.strategy.choose(section, options)
        chosen = {"strategy": choice, "strategy_why": why, "options": options, "section": section}
        if choice == "derive":
            v = monitor.verify(brain, problem, derived["answer"])
            return {**derived, **chosen, "verified": v, "sense": monitor.sense(problem, derived["answer"]),
                    "confidence": 1.0 if v and v["ok"] else monitor.confidence(derived["steps"])}
        ints = [int(compose.to_value(m)) for m in mistakes]
        g, rejected = self_checked_guess(brain, problem, ints)
        if g.get("verified") and g["verified"]["ok"]:
            g["confidence"] = 1.0                    # undoing it confirmed the guess
        return {"problem": problem, "source": "module", **g, **chosen, "mistakes": ints + rejected,
                "self_rejected": rejected, "sense": monitor.sense(problem, g["answer"])}
    answer, steps = brain.work_out(problem)
    v = monitor.verify(brain, problem, answer)
    return {"problem": problem, "source": "steps", "answer": compose.fmt(answer), "steps": steps,
            "uncertain": uncertain(steps), "repeats_mistake": any(same(answer, m) for m in mistakes),
            "verified": v, "sense": monitor.sense(problem, answer),
            "confidence": 1.0 if v and v["ok"] else monitor.confidence(steps)}


def _tool_check(mind, step):
    """A bare division or remainder step cannot be undone, so the whole-group tool re-derives it
    instead (full groups, groups needed, what's left over). -> {"ok", "check"} or None."""
    try:
        tree = compose.parse(step["problem"])
        got = compose.to_value(step["answer"])
    except (ValueError, TypeError, KeyError):
        return None
    if not (isinstance(tree, tuple) and tree[0] in compose.REMAINDER_OPS):
        return None
    checked = mind.coordination.check_story({"div": "&", "divup": "^", "rem": "%"}[tree[0]], tree[1], tree[2], got)
    return None if checked is None else {"ok": checked[0], "check": checked[1], "expected": "the same"}


def solve_plan(mind, text, mistakes=()):
    """A plan with several steps, run by the prefrontal region."""
    def solve(p):
        kind = "basic" if compose.is_basic(p) else "big"
        return solve_math(mind, task.normalize(p) if kind == "basic" else p, kind)

    def compare(a, b, sign):                            # an if is the taught compare tool's job
        if not mind.coordination.arith_taught("c"):
            raise ValueError("I haven't been taught how to compare numbers yet: show me a worked example")
        v, _, check = mind.coordination.arith_work("c", [a, b])
        return v == sign, check

    def count():                                        # a loop counts on, which is a taught tool too
        if not mind.coordination.arith_taught("n"):
            raise ValueError("I haven't been taught to count on yet: show me a worked example")

    answer, done = planner.run(text, mind.working, solve, compare, count)
    unsure, seen = [], set()
    for d in done:
        how = d["how"]
        guesses = [{"problem": how["problem"], "answer": how["answer"], "source": "module",
                    "confidence": how.get("confidence")}] if how["source"] == "module" else []
        for u in guesses + how.get("uncertain", []):
            if u["problem"] not in seen:
                seen.add(u["problem"])
                unsure.append(u)
    senses = [d["how"].get("sense") for d in done]
    checked = []                                        # every step it can check by undoing, it checks
    for d in done:
        if d.get("checked"):                            # a condition: the compare tool checks itself
            checked.append({"problem": d["problem"], "answer": d["answer"], "kind": "condition",
                            "ok": "\u2713" in d["checked"], "check": d["checked"]})
            continue
        if d["how"].get("source") == "loop":            # the loop counter itself: nothing to undo
            continue
        v = monitor.verify(mind.arithmetic, d["problem"], d["answer"])
        if v is None:                            # a division step can't be undone: the group tool checks it
            v = _tool_check(mind, d)
        if v is not None:
            checked.append({"problem": d["problem"], "answer": d["answer"], **v})
    bad = [c for c in checked if not c["ok"]]
    for c in bad:
        mind.doubts.doubt("plan", f"a step of a plan did not check out: {c['problem']}")
    reply = {"problem": text, "source": "plan", "answer": answer, "uncertain": unsure,
             "plan": [{"name": d["name"], "expression": d["expression"], "problem": d["problem"],
                       "answer": d["answer"], "source": d["how"]["source"], "section": d["how"].get("section"),
                       "rule": d["how"].get("rule"), "steps": d["how"].get("steps", []),
                       "sense": d["how"].get("sense"), "kind": d.get("kind", "step")} for d in done],
             "checked": checked,
             "confidence": 0.0 if bad else min(d["how"].get("confidence", 1.0) for d in done),
             "sense": {"ok": all(x is None or x["ok"] for x in senses)},
             "repeats_mistake": any(same(answer, m) for m in mistakes), "working_memory": mind.working.values}
    if bad:
        reply["not_sure"] = [f"{c['problem']} = {c['answer']}, but undoing it gives {c['check']} instead of {c['expected']}"
                            for c in bad]
    return reply


def uncertain(steps):
    return [s for s in steps if s["source"] == "module"]


def learned(problem, answer, tries, kind, **extra):
    return {"problem": problem, "learned": answer, "tries": tries,
            "agrees_with_math": None if kind in ("free", "plan") else task.check(problem, answer), **extra}


def noticing(brain, reply):
    """After learning a fact, see whether it points to a rule worth asking about."""
    if "learned" in reply:
        reply["proposed_rule"] = rules.suggest(brain, [(reply["problem"], reply["learned"])])
    return reply


def worked_out(brain, problem):
    """A single-digit fact it doesn't know, worked out from a rule -> reply, or None."""
    answer, steps = brain.work_out(problem)
    top = next((s for s in steps if s["problem"] == problem), None)
    if not top or top["source"] != "derived":
        return None
    return {"problem": problem, "source": "steps", "answer": compose.fmt(answer), "steps": steps,
            "uncertain": uncertain(steps), "worked": True, "repeats_mistake": False}


def handle_rule(brain, action, name, cmd):
    """Questions and teaching with letters: n/n, n/n = 1."""
    lhs = name.split(" = ")[0]
    known = [r for r, v in brain.rules.items()
             if not v.get("rejected") and v["lhs"] == compose.to_text(compose.parse(lhs, variables=True))]
    if action == "ask":
        if known:
            return {"problem": lhs, "answer": brain.rules[known[0]]["rhs"], "source": "rule", "rule": known[0]}
        return {"problem": lhs, "source": "unknown"}
    if action in ("tell", "teach"):
        for r in known:                     # a new answer for the same left side replaces the old rule
            del brain.rules[r]
        rule, math_ok = rules.add(brain, lhs, str(cmd["answer"]))
        fits, breaks = rules.evidence(rules.known_facts(brain), *rule.split(" = ", 1))
        return {"problem": lhs, "learned_rule": rule, "agrees_with_math": math_ok, "examples": fits[:6],
                "breaks": breaks[:6], "explains": compose.explains(*rules.parse_rule(*rule.split(" = ", 1))[:2])}
    if action == "forget":
        for r in known:
            del brain.rules[r]
        return {"problem": lhs, "forgot": bool(known)}
    raise ValueError("a rule can't be checked like that; teach it (n/n = 1) or forget it (forget n/n)")


def store_basic(brain, problem, answer, mistakes):
    """Teacher's answer to a single-digit fact. The sections can only say
    -9..81; anything else (a teacher who is wrong) goes to plain memory."""
    value = compose.to_value(answer)
    if value.denominator == 1 and task.MIN_RESULT <= value <= task.MAX_RESULT:
        brain.feedback(problem, int(value), True, [int(m) for m in mistakes if not same(m, value)])
        return int(value)
    brain.remember(problem, value, mistakes)
    return compose.fmt(value)


def understood(mind, text):
    """Hand a sentence to the language region -> reply, or None if it has no idea."""
    try:
        facts = "; ".join(f"{q} = {a}" for q, a in mind.knowledge.facts.items())     # the only outside numbers allowed
        u = mind.language.understand(text, mind.working.describe(), facts, mind.knowledge.facts)
    except LanguageError as e:
        return {"problem": text, "source": "unknown", "note": str(e)}
    if not u:
        return None
    if mind.mode == "normal" and len(u["meaning"]) == 1:
        # normal chat: if what it read is one piece of math, just answer it ("now add 5 to that" -> 45)
        line = str(u["meaning"][0].get("say") or "")
        try:
            key = compose.normalize(line)
        except (ValueError, KeyError):
            key = None
        if key:
            reply = solve_math(mind, task.normalize(key) if compose.is_basic(key) else key,
                               "basic" if compose.is_basic(key) else "big")
            if reply.get("answer") is not None and not reply.get("error"):
                return {**reply, "read": line, "understood": u["how"]}
    return {"problem": text, "source": "understood", "meaning": u["meaning"], "how": u["how"]}


def handle_plan(mind, action, text, cmd, mistakes):
    if action == "ask":
        return solve_plan(mind, text, mistakes)
    if action == "feedback":
        guess, correct = cmd["guess"], bool(cmd["correct"])
        plan = solve_plan(mind, text, mistakes)
        if not correct:
            return {"problem": text, "mistakes": mistakes + [guess], "check_steps": plan["uncertain"]}
        for s in plan["uncertain"]:             # the plan's answer was right, so its guessed facts probably were too
            mind.arithmetic.feedback(s["problem"], int(s["answer"]), True)
        return learned(text, guess, len(mistakes) + 1, "plan")
    if action in ("tell", "teach"):
        plan = solve_plan(mind, text, mistakes)
        right = same(plan["answer"], cmd["answer"])
        mind.working.put("last", compose.to_value(cmd["answer"]))
        return learned(text, compose.fmt(compose.to_value(cmd["answer"])), len(mistakes) + 1, "plan",
                       check_steps=[] if right else plan["uncertain"], own_answer=plan["answer"], agreed=right)
    raise ValueError("a plan can be asked, judged or corrected")


def remember_last(mind, cmd, reply):
    """Working memory keeps the latest math answer, so 'add 5 to that' works."""
    if cmd.get("action") not in ("ask", "feedback", "tell", "teach") or reply.get("region") == "knowledge":
        return
    if reply.get("source") in ("knowledge", "understood", "unknown", "plan") or reply.get("learned_rule"):
        return
    value = reply.get("learned", reply.get("answer"))
    if value is None or rules.is_rule(str(reply.get("problem", ""))) or planner.is_plan(str(reply.get("problem", ""))):
        return
    try:
        mind.working.put("last", compose.to_value(value))
    except ValueError:
        pass


def handle_english(mind, action, cmd):
    """English questions and lessons go to the English region. -> reply, or None if it isn't English."""
    if action == "english_rule":
        mind.english.accept_rule(cmd["form"], cmd["rule"], bool(cmd.get("accept")))
        return {"form": cmd["form"], "rule": cmd["rule"]["name"], "accepted": bool(cmd.get("accept")),
                "next": mind.english.notice()}
    if action == "notice" and cmd.get("region") == "english":
        return {"proposed_english_rule": mind.english.notice()}
    text = cmd.get("problem") or ""
    if not text or action not in ("ask", "teach", "tell", "feedback", "forget"):
        return None
    if action == "teach":
        lesson = english_chat.read_lesson(f"{text}")
        if lesson is None and cmd.get("answer") is not None:
            lesson = english_chat.read(text)
    else:
        lesson = english_chat.read(text) or (english_chat.read_lesson(text) if action == "ask" else None)
    if lesson is None:
        return None
    kind, parts = lesson
    base = {"problem": text, "source": "english", "kind": kind, "region": "english"}
    if kind == "teach_relation":                     # "a dog is an animal", "big means large"
        mind.english.teach_relation(parts["relation"], parts["a"], parts["b"])
        return {**base, "learned": f"{parts['a']} {'is a' if parts['relation'] == 'is-a' else 'means'} {parts['b']}",
                "tries": 1, "agrees_with_math": None}
    if action == "ask":
        return {**base, **english_chat.ask(mind.english, kind, parts)}
    if action == "feedback":
        if cmd.get("correct"):
            return {**base, "tries": 1, "agrees_with_math": None,
                    **english_chat.teach(mind.english, kind, parts, cmd["guess"])}
        return {**base, "wrong": cmd.get("guess"), "need_answer": True}
    if action in ("teach", "tell"):
        return {**base, "tries": 1, "agrees_with_math": None,
                **english_chat.teach(mind.english, kind, parts, cmd["answer"])}
    if action == "forget" and kind == "form":
        return {**base, "forgot": mind.english.forms.get(parts["form"], {}).pop(parts["word"], None) is not None}
    return None


_SOLVE_RULE = re.compile(r"^\s*solve\s+(.+?)\s+by\s+(.+?)\s*$", re.I)


def handle_missing_and_compare(mind, action, cmd):
    """Missing numbers (8 + ? = 11) and comparing (which is bigger, 45 or 54?). -> reply or None."""
    brain = mind.arithmetic
    if action == "solving_rule":
        if cmd.get("accept"):
            brain.solving[cmd["shape"]] = cmd["how"]
        return {"shape": cmd["shape"], "how": cmd["how"], "accepted": bool(cmd.get("accept"))}
    text = (cmd.get("problem") or "").strip()
    if action not in ("ask", "teach", "tell") or not text:
        return None
    m = _SOLVE_RULE.match(text if action == "ask" or cmd.get("answer") is None else f"{text} = {cmd['answer']}")
    if m and "?" in m[1]:                              # "solve a+?=c by c-a"
        shape = equations.read_equation(m[1].replace("a", "1").replace("b", "1").replace("c", "2"))
        how = m[2].replace(" ", "").replace("b", "a")          # the known number may be called a or b
        if not shape or how not in equations.CANDIDATES:
            raise ValueError(f"teach it like: solve a+?=c by c-a (ways: {', '.join(equations.CANDIDATES)})")
        brain.solving[shape[0]] = how
        return {"problem": text, "source": "equation", "learned_rule": f"{shape[0]} -> {brain.solving[shape[0]]}",
                "region": "arithmetic"}
    full = f"{text} = {cmd['answer']}" if action in ("teach", "tell") and cmd.get("answer") is not None else text
    if "?" in full:
        head, _, tail = full.rpartition("=")
        if action in ("teach", "tell") and equations.read_equation(head) and not equations.read_equation(full):
            eq = equations.read_equation(head)                  # "8 + ? = 11 = 3": an example with its answer
            work = lambda p: brain.work_out(p)
            own = equations.solve(work, brain.solving, head)
            brain.equation_examples.append([eq[0], eq[1], eq[2], tail.strip()])
            found = {k: v for k, v in equations.notice(brain.equation_examples).items() if brain.solving.get(k) != v}
            return {"problem": head.strip(), "source": "equation", "learned": tail.strip(), "tries": 1,
                    "agrees_with_math": True if own is None else None, "own_answer": own and own.get("answer"),
                    "agreed": bool(own and own.get("answer") == tail.strip()),
                    "proposed_solving_rule": [{"shape": k, "how": v} for k, v in found.items()][:1] or None}
        if equations.read_equation(full):
            r = equations.solve(lambda p: brain.work_out(p), brain.solving, full)
            if r["answer"] is None:
                return {"problem": full, "source": "unknown", "shape": r["shape"],
                        "note": f"I don't know how to find the missing number in {r['shape']} yet. "
                                f"Teach me examples like {full} = …, or a rule like: solve {r['shape']} by c-a"}
            return {**r, "worked_as": r["problem"], "problem": full, "source": "equation", "region": "arithmetic",
                    "confidence": 1.0 if r["check"] else 0.5}
    whole = equations.read_whole_division(text) if action == "ask" else None
    if whole:
        kind, a, b = whole
        q = brain.work_out(f"{a} div {b}")[0]
        r, steps = brain.work_out(f"{a} rem {b}")
        answer = f"{compose.fmt(q)} R {compose.fmt(r)}" if kind == "qr" else compose.fmt(r)
        return {"problem": text, "source": "compare", "region": "arithmetic", "answer": answer, "steps": steps,
                "difference": f"{a} div {b} = {compose.fmt(q)}, {a} rem {b} = {compose.fmt(r)}", "confidence": 1.0}
    simp = equations.read_simplest(text) if action == "ask" else None
    if simp:
        answer, g, rounds = equations.simplest(lambda p: brain.work_out(p), *simp)
        return {"problem": text, "source": "compare", "region": "arithmetic", "answer": answer, "steps": [],
                "difference": f"both divide by {g}, found in {rounds} subtractions", "confidence": 1.0}
    c = equations.read_compare(text) if action == "ask" else None
    if c:
        work = lambda p: brain.work_out(p)
        if c[0] == "which":
            sign, diff, steps = equations.compare(work, c[2], c[3])
            bigger = c[1] in ("bigger", "greater", "larger", "more")
            answer = c[2] if (sign == ">") == bigger else c[3]
            if sign == "=":
                answer = f"they are equal ({c[2]})"
        elif c[0] == "fill":
            sign, diff, steps = equations.compare(work, c[1], c[2])
            answer = f"{c[1]} {sign} {c[2]}"
        else:
            sign, diff, steps = equations.compare(work, c[1], c[3])
            holds = {"<": sign == "<", ">": sign == ">", "=": sign == "=", "<=": sign != ">", ">=": sign != "<"}[c[2]]
            answer = "yes" if holds else "no"
        return {"problem": text, "source": "compare", "region": "arithmetic", "answer": answer, "steps": steps,
                "difference": compose.fmt(diff), "confidence": 1.0}
    return None


def handle_kindergarten(mind, action, cmd):
    """Lessons, stories acted out, words and world facts. -> reply, or None if it isn't for this region."""
    kg = mind.language.reading                                 # the language region's reading engine
    if action == "school_exam":                               # a new exam, then the teacher goes over every mistake
        from . import primary
        level = cmd.get("lesson") or "P1"
        if level not in primary.LEVELS:
            raise ValueError(f"school_exam: a level, one of {', '.join(primary.LEVELS)}")
        return {"school_exam": primary.review_exam(kg, level), "region": "report"}
    if action == "words_to_learn":                            # read only: the words worth teaching, one by one
        from . import primary
        return {"words_to_learn": primary.words_to_learn(kg, top=cmd.get("rounds") or 20), "region": "language"}
    if action == "kindergarten":
        lesson = cmd.get("lesson") or "all"
        from . import primary                                 # here: primary -> school -> serve
        if lesson in primary.LEVELS:                          # the world-based primary school: one level
            log = []
            entry = primary.run_level(mind, lesson, log=log.append, real=cmd.get("real", True) is not False)
            primary.file_report(mind, entry)
            return {"school_level": entry, "school_log": log, "region": "report"}
        if lesson == "exam":
            return {"kindergarten_exam": kg.take_exam(), "region": "language"}
        done = kg.teach(lesson, cmd.get("rounds"))
        return {"kindergarten_lesson": done, "kindergarten_exam": kg.take_exam(), "region": "language",
                "summary": kg.summary()}
    if action == "code_lesson":                      # the code lesson: taught tools and recipes, then an exam
        from . import coding
        entry = coding.run_level(mind, log=lambda *_: None)
        from . import primary
        primary.file_report(mind, entry, subject="code")
        return {"code_lesson": entry, "region": "report"}
    if action == "teach_procedure":                    # a recipe: a word pattern -> the program to write
        name, pattern, plan = str(cmd.get("name") or "").strip(), cmd.get("pattern"), cmd.get("plan")
        examples = cmd.get("examples") or []
        if not name or not pattern or not plan or not examples:
            raise ValueError("a procedure needs a name, a word pattern, a plan with {n1} {n2} or {role} holes, "
                             "and [(sentence, plan)] examples")
        asks = cmd.get("asks")                       # what question it answers: needed / each / all / money / left
        if isinstance(asks, str):
            asks = [asks]
        kept, work = mind.coordination.teach_procedure(
            name, str(cmd.get("said") or name), str(pattern), str(plan),
            [(str(e[0]), str(e[1])) for e in examples],
            asks=asks or None, not_about=cmd.get("not_about"))
        return {"problem": name, "procedure": name, "kept": kept, "examples": work, "region": "coordination"}
    text = (cmd.get("problem") or "").strip()
    if not text:
        return None
    plans = mind.coordination.plans_for(text)
    kept_refusal = None
    if plans and action in ("ask", "teach"):
        # A recipe that cannot answer the question must not stop the reading engine from trying, so
        # its "I cannot do this one" is kept and only used if the reader has nothing either.
        refused = run_words(mind, text, plans)
        if refused.get("answer") is not None:
            return refused
        kept_refusal = refused
    teaching = mind.mode == "training"       # in normal mode it answers like a person: nothing in the chat is a lesson
    if action in ("ask", "teach") and teaching and Reading.reads_as_meaning(text):   # 'migrating means flying away'
        r = kg.teach_meaning(text)
        if r:
            m = re.fullmatch(r"\s*([a-z]+) means ([a-z]+)\s*\.?\s*", text, re.I)
            if m:                                                # one word for another: the English region too
                mind.english.teach_relation("synonym", m[1].lower(), m[2].lower())
            return r
    if Reading.is_story(text):
        if action == "ask":
            r = kg.read_story(text, check=cmd.get("check", True) is not False)
            if r["kind"] == "word_question":
                return r
            return r if r["answer"] is not None else kept_refusal   # it couldn't act it out: let the language region try
        if action in ("teach", "tell") and cmd.get("answer") is not None:
            return kg.learn_story(text, cmd["answer"])
        if action == "feedback":
            if cmd.get("correct"):
                return kg.learn_story(text, cmd["guess"])
            return {"problem": text, "source": "language", "kind": "story", "region": "language",
                    "wrong": cmd.get("guess"), "need_answer": True}
        return None
    if action == "ask" and teaching and _KG_FACT.match(text):                   # "a zebra has four legs"
        ok = kg.hear_fact(text)
        return {"problem": text, "source": "language", "kind": "fact", "region": "knowledge",
                "learned": text.strip(" ."), "understood": ok, "tries": 1, "agrees_with_math": None}
    if action in ("ask", "teach") and teaching and _KG_ISA.match(text):        # "a zebra is an animal": both regions learn it
        kg.hear_fact(text)
        return None
    if action == "ask" and mind.recall_fact(text)[0] is None:      # the index says it is not stored here
        chat = kg.chat(text)
        return chat if chat and chat.get("answer") is not None else kept_refusal
    return kept_refusal


def handle(mind, cmd):
    brain = mind.arithmetic
    action = cmd.get("action")
    literal = bool(cmd.get("literal"))
    if action == "mode":                       # the switch the user flips: normal chat, or teaching
        mode = str(cmd.get("mode") or "").strip().lower()
        if mode not in ("normal", "training"):
            raise ValueError("mode is 'normal' (it just answers) or 'training' (lessons, teaching, exams)")
        mind.mode = mode
        return {"mode": mode,
                "note": "Normal: it answers like a person and learns nothing from the chat."
                        if mode == "normal" else
                        "Training: every story with its answer teaches it, and it asks you to check its work."}
    kindergarten = handle_kindergarten(mind, action, cmd)
    if kindergarten is not None:
        return kindergarten
    english = handle_english(mind, action, cmd)
    if english is not None:
        return english
    asked = coding_tool(cmd.get("problem") or "")          # '8 > 3', 'sort 5, 3, 9', 'count on from 3 to 7'
    if asked and (action != "ask" or mind.coordination.arith_taught(asked[0])):
        op, args, said = asked
        if action != "ask" and cmd.get("answer") is not None:
            kept, mine = mind.coordination.teach_arithmetic(op, [(tuple(args), cmd["answer"])], said=said)
            return {"problem": said, "tool": op, "kept_tool": kept, "worked": mine, "region": "coordination"}
        if mind.coordination.arith_taught(op):
            return solve_coding_tool(mind, asked)
        return {"problem": said, "source": "no tool",
                "note": f"I haven't been taught how to {ARITH_TOOLS[op]} yet: show me a worked example"}
    extra = handle_missing_and_compare(mind, action, cmd)
    if extra is not None:
        return extra
    if cmd.get("problem") and planner.is_plan(cmd["problem"]):
        problem, kind = cmd["problem"].strip(), "plan"
    else:
        problem, kind = classify(cmd["problem"]) if cmd.get("problem") else (None, None)
    mistakes = cmd.get("mistakes", [])
    if action in ("ask", "feedback", "tell", "teach", "auto", "forget") and not problem:
        raise ValueError(f"'{action}' needs a question, e.g. 3+4")
    if kind == "basic":
        problem = task.normalize(problem)
    if kind == "rule":
        return handle_rule(brain, action, problem, cmd)
    if kind == "plan":
        return handle_plan(mind, action, problem, cmd, mistakes)

    if action == "ask":
        if kind == "free":
            answer, how = mind.recall_fact(problem)               # exact key, or found by its cue words
            if answer is not None:
                return {"problem": problem, "answer": answer, "source": "knowledge",
                        "found_by": how, "stored_at": (mind.where_is(problem) or [None])[0]}
            if not literal:
                reply = understood(mind, cmd["problem"])
                if reply:
                    return reply
            return {"problem": problem, "source": "unknown"}
        needed = tool_ops(problem)
        if needed and all(mind.coordination.arith_taught(op) for op in needed):
            return solve_tool(mind, problem)
        if needed:                       # no guessing with a tool it was never taught
            return {"problem": problem, "source": "no tool",
                    "note": f"I haven't been taught how to work out {ARITH_TOOLS[needed[0]]} yet: show me a "
                            f"worked example, like teach me: {problem} = (the answer)"}
        return solve_math(mind, problem, kind, mistakes)

    if action == "feedback":
        guess, correct = cmd["guess"], bool(cmd["correct"])
        if kind == "basic" and cmd.get("strategy") and not mistakes:
            # the basal ganglia's reward: did the chosen way of answering pay off?
            steps = len(brain.work_out(problem)[1]) if cmd["strategy"] == "derive" else 1
            mind.strategy.reward(brain.section_name(brain._route(task.encode(problem))), cmd["strategy"], correct, steps)
        if kind == "basic" and cmd.get("worked"):            # a fact it worked out from a rule
            _, steps = brain.work_out(problem)
            if not correct:
                return {"problem": problem, "mistakes": mistakes + [guess], "check_steps": uncertain(steps)}
            for s in uncertain(steps):
                brain.feedback(s["problem"], s["answer"], True)
            stored = store_basic(brain, problem, guess, mistakes)   # understanding teaches intuition
            return noticing(brain, learned(problem, stored, len(mistakes) + 1, kind))
        if kind == "basic":
            guess, mistakes = int(compose.to_value(guess)), [int(m) for m in mistakes]
            brain.feedback(problem, guess, correct, mistakes)
            if not correct:
                mistakes.append(guess)
                g = brain.next_guess(problem, mistakes)
                return {"problem": problem, "source": "module", "mistakes": mistakes,
                        "section": brain.section_name(g["module"]), **g}
        elif kind == "big":
            _, steps = brain.work_out(problem)
            if not correct:
                return {"problem": problem, "mistakes": mistakes + [guess], "check_steps": uncertain(steps)}
            for s in uncertain(steps):       # the total was right, so its guessed steps probably were too
                brain.feedback(s["problem"], s["answer"], True)
            brain.remember(problem, guess, mistakes)
            guess = compose.fmt(compose.to_value(guess))
        else:
            raise ValueError("teach it with: question = answer")
        return noticing(brain, learned(problem, guess, len(mistakes) + 1, kind))

    if action in ("tell", "teach"):
        answer = cmd["answer"]
        if kind == "free":
            if action == "teach" and not literal:
                # maybe it isn't a plain fact ("any number divided by the same number is = 1")
                reply = understood(mind, f"{cmd['problem']} = {answer}")
                if reply and reply["source"] == "understood" and not (
                        len(reply["meaning"]) == 1 and reply["meaning"][0].get("literal")):
                    return reply
                if reply and reply["source"] == "understood":       # a fact, with a cleaner question
                    problem, answer = reply["meaning"][0]["say"].split(" = ", 1)
            own = mind.recall_fact(problem)[0]
            mind.knowledge.remember(problem, answer)
            mind.reindex()                                         # the index must know the new memory
            return learned(problem, str(answer).strip(), 1, kind, own_answer=own,
                           agreed=own is not None and same(own, answer), region="knowledge")
        compose.to_value(answer)                                  # must be a number
        needed = tool_ops(problem)
        if needed:                       # a tool: the teacher shows examples, the brain checks them itself
            op = needed[0]
            tree = compose.parse(problem)
            args = [compose.evaluate(t) for t in tree[1:3]]
            examples = [(tuple(args), compose.to_value(answer))]
            for pair in cmd.get("examples") or []:                # the teacher may show more worked examples
                examples.append((tuple(pair[0]), compose.to_value(pair[1])))
            kept, mine = mind.coordination.teach_arithmetic(op, examples, said=f"{problem} = {answer}")
            return learned(problem, str(answer), len(examples), kind, kept_tool=kept, tool=op,
                           worked=mine, region="coordination")
        if problem in brain.memory:
            own, steps = brain.memory[problem]["answer"], []
        elif kind == "basic":
            own, steps = int(brain.work_out(problem)[0]), []      # what it would say: memory, rules, reasoning, then a guess
        else:
            value, steps = brain.work_out(problem)
            own = compose.fmt(value)
        agreed = same(own, answer)
        if action == "teach" and not agreed and own is not None and problem not in brain.memory:
            mistakes = mistakes + [own]
        if kind == "basic":
            stored = store_basic(brain, problem, answer, mistakes)
            check = []
        else:
            if agreed:                         # its own working was right: trust the guessed steps
                for s in uncertain(steps):
                    brain.feedback(s["problem"], s["answer"], True)
            brain.remember(problem, answer, mistakes)
            stored = compose.fmt(compose.to_value(answer))
            check = [] if agreed else uncertain(steps)            # where did its own working go wrong?
        return noticing(brain, learned(problem, stored, len(mistakes) + 1, kind, own_answer=own, agreed=agreed,
                                       steps=steps, check_steps=check))

    if action == "learn_phrase":
        meaning = [{"say": str(m["say"]), **({"literal": True} if m.get("literal") else {})} for m in cmd["meaning"]]
        mind.language.learn(cmd["text"], meaning)
        return {"text": cmd["text"], "learned_meaning": meaning}

    if action == "auto":
        if kind == "free":
            raise ValueError("it can only check math by itself; teach it with: question = answer")
        if kind == "basic":
            return {"problem": problem, **brain.solve(problem)}
        if problem in brain.memory:
            return {"problem": problem, "answer": brain.memory[problem]["answer"], "source": "memory"}
        taught = []
        while True:
            # fixing a guessed step can change the steps after it (a different carry,
            # for example), so work it out again until every step is from memory
            answer, steps = brain.work_out(problem)
            if not uncertain(steps):
                break
            taught += [{"problem": s["problem"], "tries": brain.solve(s["problem"])["tries"]}
                       for s in uncertain(steps)]
        if task.check(problem, answer):
            brain.remember(problem, answer)
        return {"problem": problem, "answer": compose.fmt(answer), "source": "steps", "steps": steps,
                "taught_steps": taught, "agrees_with_math": task.check(problem, answer)}

    if action == "rule":
        name = cmd["rule"]
        if cmd.get("accept"):
            fits, _ = rules.evidence(rules.known_facts(brain), *name.split(" = ", 1))
            _, math_ok = rules.add(brain, *name.split(" = ", 1), examples=fits[:6], taught=False)
            return {"rule": name, "accepted": True, "agrees_with_math": math_ok}
        rules.reject(brain, name)
        return {"rule": name, "accepted": False}

    if action == "notice":
        return {"proposed_rule": rules.suggest_from_memory(brain)}

    if action == "doubts":
        return {"doubts": monitor.doubts(brain)}

    if action == "rules":
        return {"rules": [{"rule": name, "taught": r.get("taught", True), "examples": r.get("examples", []),
                           "explains": compose.explains(*rules.parse_rule(r["lhs"], r["rhs"])[:2])}
                          for name, r in brain.rules.items() if not r.get("rejected")]}

    if action == "sleep":
        brain.sleep(rounds=int(cmd.get("rounds", 20)))
        dreamed = mind.language.reading.sleep()         # the reading engine relives remembered stories too
        return {"slept": int(cmd.get("rounds", 20)), "kindergarten_sleep": dreamed, **stats(mind)}

    if action == "exam":
        return exam(brain)

    if action == "stats":
        return stats(mind)

    if action == "forget":
        if kind == "free":
            return {"problem": problem, "forgot": mind.knowledge.forget(problem)}
        return {"problem": problem, "forgot": brain.memory.pop(problem, None) is not None}

    if action == "reset":
        mind.arithmetic = new_arithmetic()
        mind.knowledge.facts.clear()
        mind.language.phrases.clear()
        mind.language.patterns.clear()
        mind.working.clear()
        mind.strategy.stats.clear()
        mind.coordination.rules.clear()
        mind.coordination.stats.clear()
        mind.language.reading = Reading()
        mind._bind()
        return {"reset": True, **stats(mind)}

    raise ValueError(f"unknown action {action!r}")


def answered_by(reply):
    """For the efficiency counters: what part of the brain produced this answer?"""
    source = reply.get("source")
    if source == "understood":
        return f"language ({reply.get('how')})"
    if source == "steps":
        return "worked out (rule)" if reply.get("worked") else "worked out (written method)"
    if source == "plan":
        return "plan (prefrontal)"
    if source == "language":
        return {"story": "language (read a story)", "knowledge": "knowledge (world facts)",
                "word": "language (word meaning)", "fact": "knowledge (world facts)",
                "meaning": "language (taught meaning)"}.get(reply.get("kind"))
    if source == "module":
        return "section guess"
    return {"memory": "memory", "knowledge": "knowledge", "rule": "rule shortcut"}.get(source)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="brain_state")
    ap.add_argument("--language-model", default="none",
                    help="local Ollama model the language region may ask for help ('none' = only its own reader)")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = ap.parse_args()
    state = Path(args.state)
    try:
        cmd = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")   # PowerShell pipes add a BOM
        mind = Mind.load(state, {"model": args.language_model, "url": args.ollama_url})
        reply = handle(mind, cmd)
        remember_last(mind, cmd, reply)
        how = answered_by(reply) if cmd.get("action") in ("ask", "feedback") else None
        if how:
            mind.count(how)
        if cmd.get("action") in MUTATING:
            # in normal mode a plain question is just a question: no lesson, nothing new to keep, so the
            # whole brain is not written again (chat stays quick and the file is not churned)
            if not (mind.mode == "normal" and cmd.get("action") == "ask"):
                mind.save(state)
            else:
                mind.save_usage(state)
                mind.save_conversation(state)   # "now add 5 to that" still works between messages
        elif how:
            mind.save_usage(state)
    except (ValueError, KeyError, TypeError) as e:
        reply = {"error": str(e)}
    sys.stdout.buffer.write((json.dumps(reply, default=str, ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
