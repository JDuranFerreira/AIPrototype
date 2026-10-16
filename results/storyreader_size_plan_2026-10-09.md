# storyreader.py size-reduction plan (2026-10-09)

`brainlike/storyreader.py` is 2,671 lines and holds six concerns that grew there during the
reading campaigns. The gate is met; this is the Phase-4 cleanup, **a plan only — nothing is
extracted yet.** Precedent: `coordination.py` was split out the same way (2026-10-04) —
byte-identical guards, `storyreader` re-exports every old name so every import keeps working.

## Current map (measured 2026-10-09)

| lines | concern | what it is |
|---|---|---|
| 37–88 | `Lin`, `lower_truth` | the value-with-unknown type |
| 89–201 | `Situation` | the mental model (cells, first/current) |
| 202–895 | perception | `tokens`, `sentences`, `split_question`, `singular`, `plural_looking`, **`Lexicon`** (160), **`perceive`** (178), `clauses`, `unfamiliar`, change-family comment block |
| 896–1045 | `Clause` | one clause's slots and atoms |
| 1046–1262 | expressions | `expressions`, `show_work`, `evaluate`, `write`, `change_cell`, `tool_ops`, `uses` |
| 1263–1415 | request scope | `counts_thing`, `scope_owner`, `by_owner` + helpers (the request gate) |
| 1416–2321 | **`Frames`** (905) | the frame learner; monsters: `word_property` (199), `apply` (219), `answer` (166) |
| 2330–2671 | `StoryReader`, `learn_tale`, `learn_from_answer`, helpers | the whole-story reader and the teacher |

## Dependency facts (scanned, not assumed)

- `Frames` uses: `Lin`, `clauses`, `expressions`/`show_work`/`evaluate`, `tool_ops`/`uses`,
  `write`/`change_cell`, `counts_thing`/`scope_owner`/`by_owner`, `singular`.
- `Clause` uses: `Lin`, `expressions`, `singular`.
- `perceive` uses only `singular`/`plural_looking` (same module today).
- => **extract bottom-up or you get a cycle** (the exact trap that pushed `request.py` out
  standalone on 2026-10-05).

## The plan: five extractions, bottom-up, one at a time

Each step is landed only when the guard battery below is **byte-identical** to the pre-step run
and `brain_state/` MD5 is unchanged. `storyreader.py` re-exports every moved name
(`from brainlike.model import Lin, Situation  # re-export`), like `coordination.py` does today.

1. **`brainlike/model.py`** (~165 lines): `Lin`, `lower_truth`, `Situation`. No internal deps —
   the foundation everything else imports.
2. **`brainlike/expressions.py`** (~215 lines): `expressions`, `show_work`, `evaluate`, `write`,
   `change_cell`, `tool_ops`, `uses`. Imports `model`.
3. **`brainlike/scope.py`** (~150 lines): `counts_thing`, `scope_owner`, `by_owner`,
   `_term_unit`, `_term_owner`, `_group_owner`, `_self_owned`, `_scales_content_total`.
   Imports `model` + `expressions`.
4. **`brainlike/perception.py`** (~700 lines): `tokens`, `sentences`, `split_question`,
   `singular`, `plural_looking`, `Lexicon`, `perceive`, `_name_slot`, `clauses`,
   `_number_ahead`, `unfamiliar`, `Clause`. Imports `model` (+ `scope` only if `Clause` needs
   it — check at step time; the scan says it does not).
5. **`brainlike/frames.py`** (~905 lines): the `Frames` class. Imports all of the above plus
   `coordination` (already a separate module). **Optional split inside:** `word_property`
   (199 lines, the 10-07 word-kind classifier) → `brainlike/wordprop.py`, since it is a
   self-contained policy over the lexicon.

After step 5, `storyreader.py` keeps only `StoryReader`, `learn_tale`, `learn_from_answer`,
`_content_words`/`_words`/`_clause_at`/`_alternatives`/`_credit_clause`/`_reinforce` and the
re-export block: **target ~500 lines, -81%.**

## Order rationale

- Bottom-up because of the dependency scan above; `Frames` last because it is the biggest sink.
- `model.py` first: every later step imports it, and it has zero risk (pure types).
- Do NOT start with `Frames` even though it is the biggest — it would import from
  `storyreader` while `storyreader` re-exports it = cycle.

## Verification battery (run before/after every step; must be byte-identical)

```
.venv\Scripts\python.exe -m compileall -q brainlike
.venv\Scripts\python.exe benchmarks\_tmp_guard.py P1 P2 P3 P4 P5 P6
.venv\Scripts\python.exe benchmarks\asdiv_buckets.py 1 test <abs>\brain_state
.venv\Scripts\python.exe benchmarks\_tmp_kindergarten.py     # expect 389/400
.venv\Scripts\python.exe benchmarks\recipes_regression.py    # expect 5/5, 0/0/200
```
Plus the concatenated-bytes MD5 of `brain_state/` (must stay
`d05c4d7c8918606afacaa0b85679eef7`, 25 files) and — if the AgenticOS tree is present —
`C:\AgenticOS\scripts\check.ps1`.

Caches to watch while moving code (their invalidation points must move with them):
`storyreader.uses` module memo, `Frames._sure_cache` (emptied in `credit()` — the only writer),
`WordLearner._links` (invalidated from `observe()`). `Frames.bind` wiring stays as-is.

## What this does NOT do

- No behaviour change, no new features, no flag flips. The pennies/baker/clown campaigns and
  control-flow capacity (§6 item 8.6) are separate work and stay out of this plan.

---

## AS BUILT (2026-10-09, same day): all five steps landed

Every step was gated on the verification battery (guard P1-P6 + ASDiv g1 buckets +
kindergarten + recipes) being **byte-identical** and `brain_state/` MD5 unchanged
(`d05c4d7c8918606afacaa0b85679eef7`). All gates passed.

| step | landed | lines out of storyreader |
|---|---|---|
| 1 | `model.py` (Lin, Situation, lower_truth, fmt) | -165 |
| 2 | `expressions.py` (expressions, show_work, evaluate, write, change_cell, tool_ops, uses) | -218 |
| 3 | `scope.py` (counts_thing, scope_owner, by_owner, ...) + `perception.py` started (singular, plural_looking, _WHERE, _NOT_NOUNS) | -178 |
| 4a | perception.py: tokens, sentences, split_question, Lexicon, _name_slot, clauses, _number_ahead, unfamiliar | -389 |
| 4b | perception.py: Clause | -146 |
| 5 | `frames.py` (TRUST, Frames, _sure) + the flag farm's static sets to perception.py | -924 |

**Final: storyreader.py 2,671 -> 770 lines (-71%).** New files: model.py 205,
expressions.py 232, perception.py 510, scope.py 159, frames.py 965.

### Deviations from the plan (measured, not optional)

- **The campaign flags (19 bools) and `perceive` STAY in storyreader.py.** The flags are the
  counterfactual surface (`setattr(sr, "_FLAG", True)` from every runner), and `perceive`
  reads 15 of them directly. Moving either would have broken the CF machinery silently.
  Instead: `Frames.is_noun` / `apply` / `answer` (now in frames.py) do a **late
  `from .storyreader import ...` at call time**, and `Situation.write_first` /
  `perception.clauses` likewise. Verified: `setattr(sr, "_CHANGE_EVENT", False)` now changes
  g1 claims 32 -> 33 (the CF reaches frames.py).
- **`_DELTA_Q` froze `_FLY_FIX` at its import-time value (True)** when moved to perception.py;
  this matches the old behaviour exactly (it was already frozen at import in storyreader).
- The scope extraction (step 3) needed the perception word-form helpers first, so 3 and 4
  were re-ordered slightly (singular moved before the rest of perception).

### Verification notes

- The static AST name-check missed one runtime NameError (`singular` shadowed inside frames);
  the byte-identical battery caught it. The battery is the real gate; the AST check is a
  fast pre-filter only.
- The step-5 splice briefly swallowed the scope re-export (it sat between TRUST and Frames);
  restored, re-verified byte-identical.

---

## COMPLETED (2026-10-09): all five steps landed and verified

Every step gated on the verification battery (guard P1-P6 + ASDiv g1 buckets +
kindergarten + recipes) being **byte-identical** and `brain_state/` MD5 unchanged
(`d05c4d7c8918606afacaa0b85679eef7`). All gates passed.

| step | landed | lines out of storyreader |
|---|---|---|
| 1 | `model.py` (Lin, Situation, lower_truth, fmt) | -165 |
| 2 | `expressions.py` (expressions, show_work, evaluate, write, change_cell, tool_ops, uses) | -218 |
| 3 | `scope.py` (counts_thing, scope_owner, by_owner, ...) + `perception.py` started (singular, plural_looking, _WHERE, _NOT_NOUNS) | -178 |
| 4a | perception.py: tokens, sentences, split_question, Lexicon, _name_slot, clauses, _number_ahead, unfamiliar | -389 |
| 4b | perception.py: Clause | -146 |
| 5 | `frames.py` (TRUST, Frames, _sure) + the flag farm's static sets to perception.py | -924 |

**Final: storyreader.py 2,671 → 770 lines (-71%).** New files: model.py 205,
expressions.py 232, perception.py 510, scope.py 159, frames.py 965.

### Deviations from the plan (measured, not optional)

- **The campaign flags (19 bools) and `perceive` STAY in storyreader.py.** The flags are the
  counterfactual surface (`setattr(sr, "_FLAG", True)` from every runner), and `perceive`
  reads 15 of them directly. Moving either would have broken the CF machinery silently.
  Instead: `Frames.is_noun` / `apply` / `answer` (now in frames.py) do a **late
  `from .storyreader import ...` at call time**, and `Situation.write_first` /
  `perception.clauses` likewise. Verified: `setattr(sr, "_CHANGE_EVENT", False)` now changes
  g1 claims 32 → 33 (the CF reaches frames.py).
- **`_DELTA_Q` froze `_FLY_FIX` at its import-time value (True)** when moved to perception.py;
  this matches the old behaviour exactly (it was already frozen at import in storyreader).
- The scope extraction (step 3) needed the perception word-form helpers first, so 3 and 4
  were re-ordered slightly (singular moved before the rest of perception).

### Verification notes

- The static AST name-check missed one runtime NameError (`singular` shadowed inside frames);
  the byte-identical battery caught it. The battery is the real gate; the AST check is a
  fast pre-filter only.
- The step-5 splice briefly swallowed the scope re-export (it sat between TRUST and Frames);
  restored, re-verified byte-identical.
