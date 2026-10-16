# Brain vs qwen comparison (2026-10-10)

Same problems for everyone. Brain = `brain_state/` as taught (S3 round 1, code v4),
read with no language model. Models = Ollama `qwen3:0.6b` (0.9 GB) and `qwen3:8b`
(5.6 GB), temperature 0, no thinking. New harness: `benchmarks/run_code_llm.py`
(the old `run_llm_per_problem.py` takes only the LAST number of a reply, which
cannot grade ordered lists like "2, 4, 7, 9" — the new one grades the full list).

## 1. Code exam (44 fresh questions: words, traps, tools/lists, plan: programs)

| | words /18 | traps /10 | tools/lists /4 | plan: /12 | total /44 | time/problem | hardware |
|---|---|---|---|---|---|---|---|
| **brain** | **18** (15 checked) | 9 (reader guesses) | **4** (checked) | **12** (all checked) | **43** | **~5 ms** | CPU |
| qwen3:8b | 14 | **10** | 3 | 1 strict / **5 lenient** | 28 strict / 32 lenient | ~2.0 s | GPU 5.6 GB |
| qwen3:0.6b | 3 | 0 | 1 | 1 | 5 | ~2.4 s | GPU 0.9 GB |

Reading the table:

- **Plain word problems + traps (28 items, the models' home turf): 8b 24, brain 27.**
  8b is perfect on the traps (10/10 — it reads the request); the brain gets 9/10
  (its miss is a guess, never a claim). On words 8b drops rounding/multi-step
  ones the brain's tools cover (253 divup 5 -> 41; 12 divup 4 -> 4; 3*4*2 -> 12;
  three-step 56 with narration).
- **Running programs is where they part.** The brain executes all 12 plans with
  every step checked by undoing (91 checks in the lesson run). 8b narrates
  instead of executing: its 17-number trace on the wave-defense program never
  resolves to an answer. Lenient re-grade (its LAST number counts) lifts 8b to
  5/12 — all of them short 1–2 step programs; it scores **0/4 on the deep
  loop+and/or programs** (150, 155, 120, rank). 0.6b stays 1/12 either way.
- 0.6b collapses everywhere except 5 items (11%): no traps at all (0/10).

## 2. ASDiv grade 1 (97 test problems; saved model answers re-graded on the test half)

| | right /97 | shape |
|---|---|---|
| qwen3:0.6b | 87 (89.7%) | answers everything |
| qwen3:8b | 81 (83.5%) | answers everything |
| **brain** | **31 claims, 31 right (100% true)**; always-answering 47 | claims a third, all true |

Different shapes, stated plainly: the models answer everything at ~85%; the
brain claims a third of the set and every claim is true. Raw right-answer rate
is still 3x the brain's always-answering (48.5%) — reading real sentences is
still the gap (§6 item 8.3 in HANDOFF).

## 3. Cost

Brain ~5 ms/problem on CPU with ~1 M weights in the reader; models ~2 s/problem
on GPU (0.9–5.6 GB). Roughly 400x per problem, before hardware.

## Files

- `results/code_qwen3-0.6b_nothink.json` (5/44), `results/code_qwen3-8b_nothink.json`
  (28/44) — fresh runs this session.
- `results/asdiv1_qwen3-0.6b_nothink.json`, `results/asdiv1_qwen3-8b_nothink.json`
  — earlier runs, re-graded here on the odd-index test half (87, 81).
- Grading scripts (scratchpad): test-half re-grade, category split, lenient
  last-number re-grade for plan: items.
