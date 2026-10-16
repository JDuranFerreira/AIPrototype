# Re-landing the lost 2026-10-10..10-12 campaign fixes (2026-10-16)

**What happened:** an unlogged evening session on 2026-10-15 (4–8 pm) reverted
`brainlike/storyreader.py` to the git-HEAD monolith (commit c9347b1, 2026-10-09
11:39) and left a final self-built 2,953-line version that **broke the grade-1
gate (8 right / 12 claims = 67% true)**. With it went:

- the 10-09-evening `_COIN_DOUBT` landing,
- the 10-07tier `clock` fixes `_LASTS_FIX` / `_LAST_Q` (2026-10-10),
- the 10-12 campaign fixes `_M_ATOMS` (+ riders), `_KNOWN_NOUN`, `_LEFT_FIX`
  (+ threshold 0.7→0.65), `_DIM_DESC`, and the `_TWO_STEP` wiring,
- the 10-09 refactor's 770-line `storyreader.py` shell (still lost; the split
  files `frames.py`/`perception.py`/`scope.py`/`expressions.py` survive),
- the S3 teller in `primary.py`, the inc tool in `coordination.py`, and the
  code-lesson v4/v5 material in `coding.py` — teaching-side, re-landing separately.

**The recovery plan (this doc):** checkpoint first (commit `680c289`, code
pipeline = the HEAD monolith, which itself already holds the 10-08/09 gate
campaign landings 1–6), then re-land every lost fix on the green base, one at
a time, each gated on the full battery:

```
.venv\Scripts\python benchmarks\_tmp_guard.py P1 P2 P3 P4 P5 P6   # worlds + real + ASDiv buckets
.venv\Scripts\python benchmarks\_tmp_kindergarten.py              # expect baseline
.venv\Scripts\python benchmarks\recipes_regression.py             # expect 5/5, 0/0/200
```

`brain_state/` stays byte-identical throughout (read-only; verified by MD5
comparison against `brain_state_backup_2026-10-16_precheck/` after every batch).

**Green baseline before this work (HEAD monolith code + the taught state of
2026-10-15):** worlds 96.7 / 91.2 / 89.5 / 89.8 / 88.2 / 86.0; real stories
35/22/28/18/17/17 of 60; ASDiv g1 32 right / 33 claims = 97% true; kg 384/400;
recipes 5/5, 0/0/200. (Logged 10-12 numbers differ slightly — kg 389, g1
35/36 — because the taught state and later-school lessons drifted; the ACTION
measurements below are all against THIS baseline.)

## Landing 1: `_COIN_DOUBT` — re-landed

From `results/asdiv_gate_campaign_2026-10-09.md` item 7. A story naming **2+
distinct coin nouns** (`penny/pennies/dime/dimes/nickel/nickels/quarter/quarters`)
withholds its claim ("money of mixed coins needs their values, which I was
never taught") — claim-time only, in `StoryReader.doubt_about`, answer path
untouched.

- Re-landed in `brainlike/storyreader.py` (`_COIN_DOUBT = True` + `_COIN_WORDS`,
  the check first in `doubt_about`).
- **Firing verified directly:** a claimed-path call with two coin nouns returns
  the money doubt; a no-coin story returns no doubt.
- **Current measured effect: zero** (honest note). On the evolved taught state
  the pennies row no longer claims at all — the S2-era money lessons gave the
  dollar question a frame that is not sure enough to claim, so the row answers
  via the `guessed` path, which `doubt_about` never sees. The 10-12-era table
  differs from the 10-09 one it was measured on (claims 33 vs 32; the claimed-wrong
  row is now the G3 clown row, not pennies). So the coin doubt is an honest
  safety net, not a live win right now — kept because if a mixed-coin story ever
  forms a claim again, it must be withheld.
- **Battery:** worlds P1–P6 96.7/91.2/89.5/89.8/88.2/86.0 (P6 identical to the
  pre-landing check; claims are unchanged by construction — answers untouched),
  g1 buckets unchanged (32/33), kg 384/400, recipes 0/0/200 — everything
  unchanged, `brain_state` byte-identical (MD5-compared), compileall OK.
