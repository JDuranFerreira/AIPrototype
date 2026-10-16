# Clock campaign (2026-10-10)

P1 kind `clock` read 21/60 on every state back to pre-S2 (S2's 18/20 was one
lucky exam seed): chronic, not a regression. Two shapes, two fixes, both
measured counterfactual-first and landed only with clean guards. `brain_state/`
untouched throughout (code flags only).

## Diagnosis (traces)

- Backward ("The film starts at 7. It ends at 11. How many hours does it
  last?"): statements read fine, but the question has NO frame (`did: []`).
- Forward-end ("The show starts at 7. It lasts 2 hours. At what o'clock does it
  end?"): "lasts 2 hours" is read as a REMAINDER (`show's o'clock left over
  after groups of 2` = 7 % 2 = 1, `how: '*|PPNT'`, sure False) — the P3
  leftover meaning the table learned for "last". The end question then reads
  the corrupted cell (got 1, want 9).

## Landing 1: `_LASTS_FIX` (the statement)

"It lasts N hours" with a numeral + hour-word advances a KNOWN o'clock cell
(`cell+N1`, rank 1 / 0.8, inserted or promoted like the _CHANGE_FIX family).

Measured: clock tales 21/60 -> 34/60 (13 fixed, 0 broke over 56 unique tales);
worlds P1–P6 +0.1..0.8pt (none down), real stories identical, ASDiv g1–g6
identical incl. 31/31, kg 389/400, code 45/46 (same pens miss), recipes 0/0/200.

## Landing 2: `_LAST_Q` (the question)

"How many hours does it last" asks now-minus-first (`slot-F:slot`, rank 2 /
0.95 like _RATE_FIX) over a known o'clock cell whose now and first differ.
Sits after the request gate with the rate/event questions.

Measured with _LASTS_FIX: clock tales 36/96 -> 96/96 over 5 seeds (60 fixed,
0 broke, every fix `understood every sentence`); worlds P1–P6 +0.9..2.6pt
(P1 96.9->99.5, P2 91.0->94.0, P3 89.5->91.7, P4 90.0->92.3, P5 88.5->89.5,
P6 86.0->87.5), real stories identical, ASDiv g1–g6 identical incl. 31/31,
kg 389/400, code 45/46, recipes 0/0/200. Post-landing rerun without flags
matches: g1 31/31 = 100%.

## Left open

Backward questions beyond o'clock ("how long did it take" with day cells),
12-hour wrap (ends past 12 needs mod — unexpressible), "last" as adjective
("last day") never fires the statement fix (no numeral) by design.
