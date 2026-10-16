# Three tasks: brain vs qwen, same fresh problems (2026-10-12, user asked)

36 hand-written items, new numbers and phrasing, never taught, never in any exam:
12 math (groups → unitary → volume/ratio/threestep/average), 12 language (pronouns,
transfers, comparisons acted out), 12 code (6 word-tasks + 6 `plan:` programs with
`if`/`for`/`and`, all checked step by step). Brain in normal mode (learns nothing,
~5 ms/problem CPU); qwen3:0.6b and qwen3:8b at temperature 0, no thinking, asked for
the final number only. Runner: `benchmarks/compare_tasks3.py`; raw data:
`results/three_tasks_2026-10-12.json`.

| | math /12 | language /12 | code /12 | total /36 |
|---|---|---|---|---|
| **brain** | **9** | **9** | **10** | **28** |
| qwen3:0.6b strict / lenient | 0 / 9 | 4 / 10 | 2 / 8 | 6 / **27** |
| qwen3:8b strict / lenient | 4 / 6 | 8 / 9 | 6 / 7 | 18 / **22** |

Strict = the reply is exactly the answer (the brain always answers exactly).
Lenient = the reply's LAST number is the answer (precedent: `results/qwen_comparison_2026-10-10.md`).
Strict punishes narration: 0.6b shows its work and usually ends right (math 0→9);
lenient rewards rambling that lands right. Both grades stated; neither is the whole
truth. Note the inversion: lenient 0.6b (27) beats lenient 8b (22) — the small model
works things out loud and finishes right, the big one answers tersely and is wrong
more often (8b math 6/12 lenient: share-7, marbles-33, notebooks-32, ratio-6,
average-90, desks-19).

Reading it honestly:

- **Math**: brain 9 (misses: 9×7 answered 7 — wrong request direction; 15+3×6
  answered 15 — second part dropped; 4×6−5 answered 5). 8b gets the plain ones
  (63, 10, 60, 280) but no unitary/ratio/average/leftover shape except none.
- **Language**: brain 9, 8b 8 lenient (9 with strict-ish terseness on the easy ones).
  Both drop pronoun/transfer variants; brain's misses answer 2 (a part instead of
  the whole); 8b's miss by one (13 for 12, 6 for 5).
- **Code**: brain 10/12 (misses: 96/8 → 44 and 150+60 → 60, both reader guesses on
  phrasings its recipes don't cover). Models can't execute loops: 0.6b runs the two
  `if`-only programs (2/6 strict and lenient) and nothing with a `for` (counter,
  nested: last numbers 3, 3); 8b runs the two short straight-line programs (2/6),
  0 on the counter loop, the nested loop, the and/or-gate and the 3-step chain.
  Same shape as 10-10: running programs is where they part.

Cost: brain ~5 ms/problem on CPU; models ~0.2–0.4 s/problem on GPU (0.9–5.6 GB).
State untouched by the comparison (`ask` doesn't save; drift since is the re-teach
plus the sweep, both logged).
