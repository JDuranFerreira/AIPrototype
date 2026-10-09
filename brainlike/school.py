"""School: teach the brain level by level, Singapore and Estonia style.

For every level and subject:
  1. Readiness   a pre-test, taken on a copy of the brain so it learns nothing from it
  2. Engagement  the lessons. It tries first and the teacher corrects it. It notices rules from
                 examples, and the teacher confirms or rejects each one. Word problems are
                 shown as a bar model when it gets them wrong.
  3. Mastery     sleep (consolidation), then SELF-ASSESSMENT (it predicts its score from how sure
                 it is of each answer, Estonia), then the exam on items it has never seen.
                 Below 90% (AL1) it gets DESCRIPTIVE FEEDBACK (strengths, what to work on), is
                 taught exactly what it got wrong, and retakes a parallel exam.
Grades use Singapore's PSLE achievement levels: AL1 = 90%+ ... AL8 = under 20%.

The teacher knows the answers (the exam key, the math checker, the English word key). The brain
only ever gets right/wrong, the right answer, or a confirmed rule, like a pupil.

  python -m brainlike.school P1            teach one level (saves the brain)
  python -m brainlike.school P1 --dry-run  teach a copy, save nothing
"""
import argparse
import copy
import json
import sys
import time
from datetime import date
from pathlib import Path

from . import compose, rules
from .curriculum import CURRICULUM, IRREGULAR, KEY
from .regions import Mind
from .serve import handle

MASTERY = 0.90
AL_BANDS = [(0.90, "AL1"), (0.85, "AL2"), (0.80, "AL3"), (0.75, "AL4"), (0.65, "AL5"), (0.45, "AL6"), (0.20, "AL7"), (0.0, "AL8")]
SUBJECTS = ["math", "english", "integrated"]


def al(score):
    return next(band for cut, band in AL_BANDS if score >= cut)


def ask(mind, text, literal=False):
    try:
        return handle(mind, {"action": "ask", "problem": text, "literal": literal})
    except (ValueError, KeyError, TypeError) as e:
        return {"error": str(e)}


def answer_of(mind, text):
    """Ask like a pupil reading the question: (answer, confidence, how)."""
    r = ask(mind, text)
    how = r.get("source")
    if r.get("source") == "understood":                      # the language region translated it
        last = None
        for m in r["meaning"]:
            if m.get("need_fact"):
                return None, 0.0, f"needs a fact it doesn't know: {m['say']}"
            last = ask(mind, m["say"], m.get("literal", False))
        r, how = (last or {}), f"language ({r.get('how')}) -> {(last or {}).get('source')}"
    if "error" in r or r.get("source") in ("unknown", None):
        return None, 0.0, r.get("error") or r.get("note") or "doesn't know"
    answer = r.get("answer")
    sure = r.get("confidence")
    if sure is None:
        h = str(r.get("how", ""))
        sure = 1.0 if h == "memory" or r.get("source") in ("memory", "knowledge", "compare") else \
            0.9 if h.startswith(("rule", "reasoned", "time cue")) else 0.85 if r.get("source") in ("steps", "plan", "equation") else 0.3
    return answer, float(sure), how


def same(got, expected):
    if got is None:
        return False
    a, b = str(got).strip().lower().rstrip(".!"), str(expected).strip().lower().rstrip(".!")
    if a == b:
        return True
    try:
        return compose.to_value(a) == compose.to_value(b)
    except (ValueError, ZeroDivisionError):
        return False


def take_exam(mind, items):
    """On a copy of the brain, so taking an exam teaches it nothing."""
    pupil = copy.deepcopy(mind)
    rows = []
    for topic, question, expected in items:
        got, sure, how = answer_of(pupil, question)
        rows.append({"topic": topic, "question": question, "expected": expected,
                     "got": None if got is None else str(got), "ok": same(got, expected), "sure": round(sure, 2), "how": how})
    score = sum(r["ok"] for r in rows) / len(rows)
    predicted = sum(r["sure"] for r in rows) / len(rows)
    return {"score": score, "predicted": predicted, "rows": rows}


def feedback(exam):
    """Descriptive feedback (Estonia): strengths, what to work on, next step."""
    topics = {}
    for r in exam["rows"]:
        t = topics.setdefault(r["topic"], [0, 0])
        t[0] += r["ok"]
        t[1] += 1
    strengths = [t for t, (ok, n) in topics.items() if ok == n]
    work_on = [f"{t} ({ok}/{n})" for t, (ok, n) in topics.items() if ok < n]
    wrong = [f"{r['question']} -> {r['got']} (right: {r['expected']}; {r['how']})" for r in exam["rows"] if not r["ok"]]
    return {"strengths": strengths, "work_on": work_on, "mistakes": wrong}


# ---- the teacher -------------------------------------------------------------------------------
def special_case(form, word):
    """The teacher's own special patterns (taught as their own rules)."""
    from .english import _cvc, _long
    consonant_y = word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou"
    if form == "plural":
        return word.endswith(("s", "x", "z", "ch", "sh")) or consonant_y
    if form == "third":
        return word.endswith(("s", "x", "z", "ch", "sh", "o")) or consonant_y
    if form == "past":
        return word.endswith("e") or consonant_y or _cvc(word)
    if form == "ing":
        return (word.endswith("e") and not word.endswith("ee")) or _cvc(word)
    if form in ("comparative", "superlative"):
        return word.endswith("e") or consonant_y or _cvc(word) or _long(word)
    if form == "adverb":
        return consonant_y or word.endswith(("le", "ic"))
    return False


def judge_english_rule(english, form, rule):
    """Accept a rule the brain noticed if it is right for the regular words the teacher knows that it
    would decide (irregular words are exceptions to remember, not evidence against a rule)."""
    key = KEY.get(form, {})
    right = total = 0
    stronger = [r for r in english.rules.get(form, []) if not r.get("rejected") and r["specific"] > rule["specific"]]
    for word, answer in key.items():
        if word in IRREGULAR.get(form, ()):
            continue
        if not rule["shape"] and special_case(form, word):
            continue                      # a default rule ("add -ed") isn't judged on the special cases (stop, carry)
        if english._context(word, rule) and not any(english._context(word, r) for r in stronger):
            total += 1
            right += english._apply(word, rule) == answer
    return total > 0 and right / total >= 0.9, right, total


def settle_english_rules(mind, log):
    while True:
        idea = mind.language.english.notice()
        if not idea:
            return
        ok, right, total = judge_english_rule(mind.language.english, idea["form"], idea["rule"])
        mind.language.english.accept_rule(idea["form"], idea["rule"], ok)
        log(f"    noticed rule: {idea['rule']['name']}  -> teacher {'confirms' if ok else 'rejects'} ({right}/{total} right)")


def settle_math_rule(mind, reply, log):
    idea = reply.get("proposed_rule")
    if idea:
        lhs, rhs = idea["rule"].split(" = ", 1)
        ok = rules.agrees_with_math(*rules.parse_rule(lhs, rhs)[:2])
        handle(mind, {"action": "rule", "rule": idea["rule"], "accept": ok})
        log(f"    noticed rule: {idea['rule']}  -> teacher {'confirms' if ok else 'rejects'}")
    for idea in reply.get("proposed_solving_rule") or []:
        examples = [e for e in mind.arithmetic.equation_examples if e[0] == idea["shape"]]
        ok = all(compose.true_value(idea["how"].replace("a", f"({k})").replace("c", f"({t})")) == compose.to_value(a)
                 for _, k, t, a in examples)
        handle(mind, {"action": "solving_rule", "shape": idea["shape"], "how": idea["how"], "accept": ok})
        log(f"    noticed how to find the missing number in {idea['shape']}: {idea['how']}  -> teacher {'confirms' if ok else 'rejects'}")


def teach_word_problem(mind, problem, bar_model, log):
    """It tries; right -> its reading is confirmed; wrong -> the teacher shows the bar model."""
    expected = answer_of(copy.deepcopy(mind), bar_model)[0] if not bar_model.startswith("plan:") else None
    got, _, how = answer_of(mind, problem)
    if expected is None:
        expected = answer_of(copy.deepcopy(mind), bar_model)[0]
    right = same(got, expected)
    handle(mind, {"action": "learn_phrase", "text": problem, "meaning": [{"say": bar_model}]})
    log(f"    word problem: {'right' if right else f'wrong ({got}); teacher shows the model {bar_model}'}")
    return right


def teach(mind, lessons, log):
    tally = {"tried": 0, "right first time": 0}
    for item in lessons:
        kind = item[0]
        if kind == "auto":
            r = handle(mind, {"action": "auto", "problem": item[1]})
            tally["tried"] += 1
            tally["right first time"] += r.get("tries", 1) == 1
        elif kind == "teach":
            r = handle(mind, {"action": "teach", "problem": item[1], "answer": item[2]})
            tally["tried"] += 1
            tally["right first time"] += bool(r.get("agreed"))
            if r.get("source") == "english" and r.get("own_answer") not in (None, item[2]) and r.get("kind") == "form":
                log(f"    {item[1]}: it said '{r['own_answer']}', teacher: '{item[2]}'")
            settle_math_rule(mind, r, log)
        elif kind == "say":
            handle(mind, {"action": "teach", "problem": item[1]})
        elif kind == "fact":                          # stated plainly: straight into the knowledge region
            handle(mind, {"action": "teach", "problem": item[1], "answer": item[2], "literal": True})
        elif kind == "word":
            tally["tried"] += 1
            tally["right first time"] += teach_word_problem(mind, item[1], item[2], log)
    settle_english_rules(mind, log)
    return tally


def remediate(mind, exam, log):
    """Teach exactly what it got wrong (the right answers), then practise."""
    for r in exam["rows"]:
        if r["ok"]:
            continue
        q, a = r["question"], r["expected"]
        if any(op in q for op in "+-*/x") and not any(c.isalpha() for c in q.replace("x", "")):
            handle(mind, {"action": "teach", "problem": q, "answer": a} if "?" not in q
                   else {"action": "teach", "problem": q.split("=")[0].strip(), "answer": f"{q.split('=')[1].strip()} = {a}"})
        elif r["how"] and str(r["how"]).startswith("needs a fact"):
            log(f"    (missing fact: {r['how']})")
        elif any(w in q.lower() for w in ("plural of", "past of", "ing of", "third of", "article of", "opposite of",
                                         "synonym of", "word class of", "comparative of", "superlative of",
                                         "adverb of", "negative of", "(")) or q.lower().startswith("is "):
            handle(mind, {"action": "teach", "problem": q, "answer": a})
        else:
            log(f"    word problem to practise: {q}")
    settle_english_rules(mind, log)


def run_level(mind, level, log=print):
    report = []
    for subject in SUBJECTS:
        part = CURRICULUM[level][subject]
        exam_a, exam_b = part["exams"]
        log(f"\n== {level} {subject}: {part['about']}")
        pre = take_exam(mind, exam_a)
        log(f"  readiness (pre-test, no learning): {pre['score']:.0%}")
        t0 = time.time()
        tally = teach(mind, part["lessons"], log)
        handle(mind, {"action": "sleep", "rounds": 50})
        log(f"  lessons: {tally['tried']} items, {tally['right first time']} right first time ({time.time() - t0:.0f}s)")
        final = take_exam(mind, exam_a)
        log(f"  self-assessment: predicts {final['predicted']:.0%}   exam: {final['score']:.0%} ({al(final['score'])})")
        attempts = [{"exam": "A", "score": final["score"], "predicted": final["predicted"]}]
        fb = feedback(final)
        if final["score"] < MASTERY:
            log(f"  below mastery. Work on: {', '.join(fb['work_on'])}")
            for m in fb["mistakes"]:
                log(f"    - {m}")
            remediate(mind, final, log)
            handle(mind, {"action": "sleep", "rounds": 50})
            final = take_exam(mind, exam_b)
            attempts.append({"exam": "B", "score": final["score"], "predicted": final["predicted"]})
            fb = feedback(final)
            log(f"  retake (parallel exam B): predicts {final['predicted']:.0%}   exam: {final['score']:.0%} ({al(final['score'])})")
            for m in fb["mistakes"]:
                log(f"    - {m}")
        report.append({"level": level, "subject": subject, "about": part["about"], "readiness": round(pre["score"], 3),
                       "score": round(final["score"], 3), "grade": al(final["score"]),
                       "predicted": round(final["predicted"], 3), "attempts": attempts,
                       "mastered": final["score"] >= MASTERY, "strengths": fb["strengths"],
                       "work_on": fb["work_on"], "mistakes": fb["mistakes"], "date": date.today().isoformat()})
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("level")
    ap.add_argument("--state", default=str(Path(__file__).resolve().parent.parent / "brain_state"))
    ap.add_argument("--dry-run", action="store_true", help="teach a copy and save nothing")
    args = ap.parse_args()
    mind = Mind.load(args.state)
    report = run_level(mind, args.level)
    if not args.dry_run:
        mind.report["report"] = [r for r in mind.report.get("report", []) if r["level"] != args.level] + report
        mind.report["level"] = args.level
        mind.save(args.state)
    sys.stdout.buffer.write(("\nREPORT " + json.dumps(report, ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
