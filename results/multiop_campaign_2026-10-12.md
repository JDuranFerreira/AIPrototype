# Multi-op campaign (2026-10-12): chained two-steps + dimension cells, both landed

Goal (user-chose): lift the single-op limit in `expressions()` — it blocks the S3 zero
kinds. Probe: `results/multiop_probe_2026-10-12.md` (interest 0/20, volume 0/20,
threestep mostly bare at the teacher).

## Landing 1: `_TWO_STEP` — chained two-step explanations `(a*b)-c`

`brainlike/storyreader.py`: `expressions()` also builds one plain pair worked out plus
one more plain outer step (`+ - *` both layers; max 12 base atoms; ~2.2x per call when
on, zero when off). `evaluate` / `uses` / `tool_ops` (`()` — no tools) /
`candidates` gate exemption parse it; parsing is unconditional (like `_UNITARY`),
generation flag-gated. Inner division excluded, so the unitary tool's `u` gate cannot
be bypassed. `primary.py`: teacher renders chained sums, `KIND_RULE` gains
volume/threestep. `show_work` stays `None` (same as plain ops — exact arithmetic needs
no undoing check); `counts_thing` passes chained leniently (logged open item: a
noun-aware rule belongs with the first real-brain teach).

## Landing 2: `_DIM_DESC` — dimension adjectives are cell descriptions

`long/wide/high` (and `cubic` for the question) work like colours: `9 cm long` and
`7 cm wide` land in different cells instead of overwriting each other. Perception:
unit nouns grab a trailing dimension word; dimensions before nouns count as adjs.
Teller (`primary.py`) uses the heard words as scene descs (`long/wide/high`, length
puts conditional on the verb saying `long`; mass `weighs/holds` unchanged). Questions
that name no description (`how many CUBIC cm`) keep the story's own unit descriptions
as extra slots — only when the asked description matches nothing and only for taught
unit nouns (fruit colours etc. untouched). Cost of the Q fallback: nil (fires almost
nowhere except volume).

## Rejected on measurement: the `sit.thing` desc carry

Carrying descs into the inherited thing-slot broke 3 claimed ASDiv rows (Isabel
claimed right→wrong 3→93 via a 0.006-margin bogus `would|now+first` meaning; Annie a
new wrong claim; candy a lost right claim). Root cause: subset cell reads
(`desc <= d`) had made bare slots accidentally right, and precision removed the
accident. The carry buys volume nothing (statements use own slots, the Q uses the
fallback), so it was reverted to the exact originals. After the revert: g3 zero diffs,
g2 one unclaimed guess wiggle (`long sleeve` now distinguished, None→27, still
unclaimed — tolerated per campaign standard).

## Measured (copies of the real brain, micro-lesson 40 tales/kind, fresh 40/kind exam)

| kind | flag off | flag on |
|---|---|---|
| volume | 0/40 | **40/40** (`(long*wide)*high` learned at 0.976) |
| length | 35/40 | **40/40** |
| threestep | 0/40 | 0/40 — acting gap, not arithmetic (sentence numbers don't survive to the question; the taught `three steps` recipe covers it in chat) |

## Guards (all clean — the land condition)

- Worlds P1–P6: 99.5/94.0/91.7/92.3/89.5/87.5 → **99.8/94.4/91.9/92.7/89.7/87.5** (up or flat); real stories identical at every level.
- ASDiv g1 test **31/31 = 100%** (buckets byte-identical incl. blocked breakdown); g2–g6 right/claims identical (g2 25/44, g3 25/57, g4 5/15, g5 1/7, g6 4/9).
- Kindergarten **389/400**, recipes **0 better / 0 worse / 200 unchanged**, `brain_state/` MD5 unchanged (25 files, read-only throughout).
- Post-landing rerun without flags: g1 **31/31**.

## Open (not this campaign)

- threestep/ratio/interest in the reader need sentence numbers as question atoms (recipes cover them via `{n}` roles); interest also needs a 4-op form or two taught steps.
- Noun-aware `counts_thing` for chained readings (with the first real-brain teach).
- Average-of-three (`(a+b+c)/3`), dividing equations (`divides` untaught), floor/ceiling tools.

## The real brain taught volume (2026-10-12, cont.)

Backup `brain_state_backup_before_volume/` first (25 files, MD5-identical verified).
Targeted lesson mirroring `primary.lessons()`: 100 fresh volume tales (situation S2,
try-first 9/10 right during the lesson), `remember` each, then `sleep(1000)` — saved
(48 s). No report-card entry (not a round).

- Volume exam (60 fresh tales, never learned): **0/60, 0 understood → 60/60 right,
  60/60 understood, 60/60 claims 100% true.**
- S2 world exam, same items before/after: **77.0% → 79.4%** (volume 0/20 → 20/20,
  the only kind that moved; understood 84% → 86%). Set 2 is harder than the round-1
  set B (89.1%) — same-items comparison is the honest one.
- ASDiv grade-1 test **31/31 = 100%** (claims identical; unclaimed guess churn ±1:
  Litter Patrol fixed, one new unclaimed guess).
- Worlds P1–P6 all up-or-flat (99.8/94.4/91.9/92.8/89.7/87.6); ASDiv g2–g6 same or
  tighter (g3 claims 57→55, rights fixed at 25); kindergarten 389/400; recipes
  0/0/200.
- Cost, stated plainly: P3 real stories 28→27 — `Skittles` transfer-all row
  (want 8, got 4, claimed). Neither state understands its transfer sentence; the
  backup's 8 was luck (doubling a collapsed ownerless cell) and sleep dilution
  re-ranked two non-understanding readings. No systematic bias (chained code never
  touches `*2` generation or credits). Net: +60 volume at 100% claimed vs one
  flipped real row — kept deliberately (contrast S3r2, which was net-negative and
  rolled back).
- Changed files 4/25: `language/reading.json` (frames + lesson counts),
  `memory/memory.json` (new S2 episodes), `prefrontal/doubts.json` (sleep real-episode
  replays), `coordination/coordination.json` (tool rewards). Report card untouched.
