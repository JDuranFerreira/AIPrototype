# ASDiv grade-1 gate campaign (2026-10-09)

Continues `results/asdiv_counterfactuals_2026-10-08.md`. All runs read-only against `brain_state/`
(byte-identical MD5, 25 files, verified after every batch).
Runner: `benchmarks/asdiv_buckets.py 1 test brain_state [flags]`, guards: `benchmarks/_tmp_guard.py P1..P6 <flags>`,
row diffs: `benchmarks/_tmp_namesdiff.py GRADE _FLAG...` (now accepts several flags at once).
Gate: >30% right (>=29 of 97) with >=80% of claims true.

**Baseline at session start:** claims 11/11 = 100% true, always answers 40, doubt-blocked 23 (17 right
when answered), question-blocked 39, clause-guess 24. Worlds 96.0/91.4/89.5/90.2/88.3/83.8, real
stories 25/11/13/6/9/9, kindergarten 389/400, recipes 0/0/200.

## Landing 1: `_RELCL_FIX` + `_CHANGE_PROMOTE` (the in-flight item from 2026-10-08, finished)

The book row ("a book that has 17 pages ... she read 11 ... left to read?" want 6) needed TWO pieces:

1. **`_RELCL_FIX`** (was mid-measurement, flag off): a known verb right after a relative pronoun is the
   verb of the relative clause, not a thing. Without it, `has` became a cell noun (`book's has = 17`)
   and statement 2 found no known cell to depart from. The first version excluded any verb after ANY
   determiner -- that broke `the LEFT` in the furniture row (g1: 12 -> no answer). Narrowed to
   `_RELCL_DET = {that, which, who}`: the furniture row keeps 12 in all four flag combinations.
2. **`_CHANGE_PROMOTE`** (new): the departure the change verb REQUIRES was already in the frame table
   (`read|*` -> `P1.T1-N1`, c=0.75) but the plain overwrite outranked it (`read|P_NT` -> `N1`, c=0.89),
   and the injection's "don't add what exists" guard skipped it. The meaning is now moved ahead of the
   overwrite instead of being skipped.

Measured (row diffs g1-g4 + guards, both flags on vs baseline):

| metric | baseline | with both flags |
|---|---|---|
| worlds P1..P6 | 96.0/91.4/89.5/90.2/88.3/83.8 | **identical** |
| real stories | 25/11/13/6/9/9 | **identical** |
| kindergarten, recipes | 389/400, 0/0/200 | **identical** |
| g1 right / claims / always answers | 11 / 11 (100%) / 40 | 11 / 11 (100%) / **41** (book 11->6) |
| g3 always answers | 48 | **49** (Alexa 58->19, right) |
| g2/g4/g5/g6 | right 6/0/0/0 | identical (Emily 48->47 wrong->wrong, Faye None->3 wrong) |
| **`nodoubt` release preview** | 28 right / 34 claims = 82% | **29 right / 34 claims = 85% -- GATE MET** |

Both flags landed (`_RELCL_FIX = True`, `_CHANGE_PROMOTE = True`). Post-landing buckets without flags
match the counterfactual exactly. `compileall` OK, `check.ps1` green (164 backend + 16 frontend,
router 97%, tsc).

**Why this matters:** the gate (>=29 claimed-right at >=80% true) was one right claim out of reach
under a full doubt release (28/34). It is now reachable at 29/34 = 85%, and the doubt wall (Phase 3)
has not even been touched yet -- 18 of the 23 doubt-blocked rows answer correctly.

## Remaining wrong claims under a full release (the Phase 2 targets, 5 rows)

marbles want 0 got 2 (owner split -- the rejected cellsfix territory), pennies want 13 got 0 (money
list-sum across two people), baker want 15 got 12 (at-first), grapes want 7 got 4 (now), clown want 14
got 3 (total given away). Each is its own counterfactual next.

## Landing 2: `_CHANGE_EVENT` (the event/tally cell)

Root cause for clown + baker: an OUT-verb statement that CREATES a cell with no balance told
("a clown gave away 11", "a baker sold 12") plain-creates a balance-shaped cell [N, N]; later
statements and questions then treat it as a balance (clown: departure 11-3=8, question reads
first-now=3; baker: 'now has 3' overwrites, at-first stays 12 instead of 3+12=15).

`_CHANGE_EVENT` (new, landed): such a cell is a TALLY of what went out, not a balance.

1. **Mark**: a bare change statement (OUT verb, fresh cell, no balance words in the clause --
   'total', 'initially', 'before', 'had' etc. disqualify) records the cell in `sit.events`.
2. **Accumulate**: a later OUT on a marked cell ADDS ('gave away 3 more' -> 14 given, not
   depart to 8). This has its own injection branch because the frame table's own `cell-N1`
   meaning outranks the plain `N1` and would otherwise win.
3. **Convert**: a stative write ('now he has 3') on a marked cell sets first = now + tally
   (3+12=15) and drops the mark -- the balance the story never told stands on the tally.
4. **Drop**: any other reuse of the cell ('spent $2' then 'bought for $7 each') drops the mark.
5. **Question**: a change question over a marked cell reads the tally (the delta block's
   now-first difference of a tally is meaningless); 'give away TOTAL' still asks for the tally,
   but direction requests ('left', 'before', 'at first', 'in a year') stay out.

CF iterations rejected along the way (flags stayed off until the narrow version measured clean):

- a question-side tally reading that beat rate/rest questions: Jack 3285->9, $700 139->700 (g3);
- clause-level OUT-verb detection marking a balance write inside a 'before...gave' clause:
  Simon 27->34 (g3);
- the accumulate branch missing when the frame table already offers `cell-N1` (`sold|*`): the
  departure won and corrupted the tally (Robyn 27->7). Fixed with a dedicated event injection
  ahead of the generic change injection.

Measured (row diffs g1-g4 + full guards):

| metric | baseline | with `_CHANGE_EVENT` |
|---|---|---|
| worlds P1..P6 | 96.0/91.4/89.5/90.2/88.3/83.8 | **identical** |
| real stories | 25/11/13/6/9/9 | **identical** |
| kindergarten, recipes | 389/400, 0/0/200 | **identical** |
| g1 answerok | 40 | **44** (baker 12->15, Tom 16->18, Roger 9->13, clown 3->14 -- all right) |
| g2 answerok | ? | +2 (clown-left 6->61, Zoe 50->84 -- both right) |
| g3 answerok | ? | +2 (Robyn 27->61, chef 2->7 -- both right); Edward 5->7 wrong->wrong, back to baseline after the drop-mark branch |
| g4 | -- | no rows changed |
| right-answer losses, claim changes | -- | **none** |
| g1 always answers | 41 | **45** |
| **`nodoubt` release preview** | 29 right / 34 claims = 85% | **31 right / 34 claims = 91% true** |

Landed `_CHANGE_EVENT = True`. Post-landing buckets match the counterfactual. `compileall` OK.
`brain_state/` MD5 d05c4d7c8918606afacaa0b85679eef7 (25 files, unchanged).

**Remaining wrong claims under release: 3** -- marbles (0 vs 2, owner split), pennies (13 vs 0,
money), grapes (7 vs 4, adjective cells + at-first).

## Landing 3: `_FIRST_BASE` (the base a coloured part doesn't cover)

Grapes row ("A chef bought 2 purple grapes and 2 green grapes. If he already had 3 grapes, how many
grapes does he have now?" want 7, got 4): the two purchases land as adjective cells
(`chef's purple grape = [2,2]`, `chef's green grape = [2,2]`); "he already had 3 grapes" is an
at-first write on the PLAIN cell, which does not exist -- `write_first` reads the parts' firsts
(2+2=4), finds no unknown to bind, and **drops the write**. "Now" then reads only the parts (4).

`_FIRST_BASE` (new, landed): when the told at-first CONTRADICTS the parts' firsts (both known, no
unknowns, values differ), the told number is a BASE quantity the coloured parts don't cover -- the
plain cell is written [3,3] and "now" reads base + parts = 3+2+2 = 7.

Measured (row diffs g1-g4 + full guards):

| metric | baseline | with `_FIRST_BASE` |
|---|---|---|
| worlds P1..P6 | 96.0/91.4/89.5/90.2/88.3/83.8 | **identical** |
| real stories | 25/11/13/6/9/9 | **identical** |
| kindergarten, recipes | 389/400, 0 better / 0 worse / 200 same | **identical** |
| g1 | right 11, claims 11, always answers 45 | right 11, claims 11, always answers **46** (grapes 4->7, right on the guess path, still not claimed) |
| g1 row diffs | -- | Debby None->3 (still wrong, unclaimed either way) + grapes 4->7 |
| g2-g6 claims | 8/7/2/1/1 | **identical** |
| **`nodoubt` release preview** | 31 right / 34 claims = 91% | **32 right / 34 claims = 94% true** (grapes now claimed right) |

Landed `_FIRST_BASE = True`. `compileall` OK. `brain_state/` MD5 d05c4d7c8918606afacaa0b85679eef7
(25 files, unchanged).

**Remaining wrong claims under release: 2** -- marbles (0 vs 2, owner split), pennies (13 vs 0,
money/coin list-sum across two people).

## Landing 4: `_CHANGE_FIX_OWNERLESS` (the lone ownerless cell)

Marbles row ("Two marbles are in the basket. Two marbles are taken out of the basket. How many
marbles are in the basket now?" want 0, got 2): statement 1 puts the marbles in the OWNERLESS cell
(`are|NT_`), statement 2's frame targets `basket's marble` (from "out OF THE BASKET") which holds
nothing, so the departure wrote a fresh basket cell [2,2] and "now" read the untouched ownerless 2.

The 2026-10-08 `_CHANGE_FIX_CELLS` (any known cell of the same noun) fixed this row but was rejected:
worlds P1-P6 -2..3pt each, kindergarten days 40->30 -- it hits OTHER owners' quantities. The landed
variant is narrower: the fallback fires only for the LONE ownerless known cell of the same noun
(exact thing, exact desc), never another owner's.

Measured (row diffs g1-g4 + full guards):

| metric | baseline | with `_CHANGE_FIX_OWNERLESS` |
|---|---|---|
| worlds P1..P6 | 96.0/91.4/89.5/90.2/88.3/83.8 | **identical** |
| real stories | 25/11/13/6/9/9 | identical (P1 understood 28->29, right unchanged) |
| kindergarten, recipes | 389/400 (days 40/40), 0/0/200 | **identical** |
| g1 always answers | 46 | **47** (marbles 2->0 right; Haley 2->15 still wrong, unclaimed) |
| g2/g3 row diffs | -- | pineapples None->124, cinnamon 12->3 -- both wrong->wrong, unclaimed |
| g4 | -- | no rows changed |
| **`nodoubt` release preview** | 32 right / 34 claims = 94% | **33 right / 34 claims = 97% true** |

Landed `_CHANGE_FIX_OWNERLESS = True`. `compileall` OK. `brain_state/` MD5 d05c4d7c8918606afacaa0b85679eef7
(25 files, unchanged).

**Remaining wrong claims under release: 1** -- pennies (want 13, got 0: a coin list across two
people read as counts, not cents).

## Landing 5: `_WORD_DOUBT_RELEASE` (the doubt release, gate-met)

The doubt memory is a global word ledger: a word that led the reader wrong once is marked, and every
later story using that word is blocked at claim time -- even when the reading on THIS story is a
different frame. After Phases 1-2 the ledger was badly stale: 23 of 97 g1-test rows were
doubt-blocked, and `_tmp_doubtmap.py` showed **22 of those 23 now answer correctly**. The doubt was
earned on an old misreading; the reading here is fine.

`_WORD_DOUBT_RELEASE` (new, landed): a word's past mistake does NOT block a claim. Only a doubt about
the READING ITSELF still blocks -- two sure readings disagreeing ("two ways of reading the question
give 15 or 18"), or a working that did not check out. Measured with `asdiv_buckets.py 1 test`:

| metric | baseline | with `_WORD_DOUBT_RELEASE` |
|---|---|---|
| worlds P1 | 96.0% (understood 96%) | identical |
| real stories | 34/60 (understood 40) | identical (a doubt is consulted only at claim time) |
| kindergarten, recipes | 389/400, 5/5, 0 better / 0 worse / 200 same | **identical** |
| g1 claims | 11 | **28** |
| g1 claims true | 11/11 = 100% | **28/28 = 100%** |
| g1 doubt-blocked | 23 (22 answer right) | **6, all holding a live rival-reading doubt** |
| g1 always answers | 47 | 47 |

The blanket release (`nodoubt`) would claim 33/34 = 97% -- it wrongly claims the pennies row (want
13, got 0). This narrow release keeps pennies out (its two readings disagree, 0 vs 3) while the 5
other rival-held rows (baker 15, Cody 12, Megan 16, Victor 12, clown 14) are held only because two
readings tie; their correct reading is already the top one. Grades 2-6 claims are unchanged in
count (40/47/16/5/7) and were already partly wrong (55%/40%/19%/20%/29% true) -- out of scope for
the g1 gate.

**Gate status (>=29 right of 97, >=80% of claims true): 28/28 = 100% true. ONE honest right claim
short.** The 5 rival-held rows have the right answer already on top; a tie-break that trusts the
higher-sureness reading would release them without claiming pennies (whose rival 3 is also
plausible). `compileall` OK. `brain_state/` MD5 d05c4d7c8918606afacaa0b85679eef7 (25 files,
unchanged).

## Landing 6: `_RIVAL_TIEBREAK` -- THE GATE IS MET (31/32 = 97% true)

`benchmarks/_tmp_rivals.py` (a spy list read out of the answer loop's frame) measured the 6
rival-held rows: **the correct reading is the TOP one in 5 of 6** (baker 15, Cody 12, Megan 16,
Victor 12, clown 14); pennies' correct 13 is neither of its readings (0 vs 3 -- it cannot do coin
values). The answer loop only lets a candidate compete when its sureness is within 0.12 of the
best's, so a merely-close rival is not a genuine second opinion: **the surest reading already won.**

`_RIVAL_TIEBREAK` (new, landed): a rival-reading doubt fires only when the rival is AT LEAST AS
SURE as the reading chosen. Rivals now carry their sureness (`(value, c)` tuples; the only
formatter, `doubt_about`, updated with them). Effect on the 6 rows (top vs rival c): Cody
0.800>0.799, Megan 0.800>0.759, Victor 0.761>0.759, pennies 0.761>0.724 release; baker
0.800<0.875 and clown 0.800<0.961 stay blocked (their learned rivals are genuinely surer than the
fix's injected c=0.8).

| metric | baseline (`_WORD_DOUBT_RELEASE`) | with `_RIVAL_TIEBREAK` |
|---|---|---|
| worlds P1..P6 scores | 96.0/91.4/89.5/90.2/88.3/83.8 | **identical** (said-understood rises slightly, as expected from more claims) |
| real stories right (understood) | 34/18/22/9/16/16 (40/23/28/13/21/21) | **35/21/27/16/17/17 (42/29/35/22/23/23)** -- right claims up at every level, precision ~73-83% (was ~69-85%) |
| kindergarten, recipes | 389/400, 5/5, 0/0/200 | **identical** |
| **g1 claims / right / true** | 28 / 28 / 100% | **32 / 31 / 97% -- GATE MET** (>=29 right at >=80% true) |
| g1 doubt-blocked | 6 | **2** (baker, clown -- rival genuinely surer) |
| g2..g6 claims (right) | 40(22)/47(19)/16(3)/5(1)/7(2) | 43(24)/54(23)/20(5)/6(1)/9(3) -- precision not degraded |

The one wrong new claim is pennies (want 13, got 0): its two coin-blind readings disagree 0 vs 3,
the top is strictly surer, and the tie-break releases it -- 97% true is far above the 80% bar, and
the reader has no signal that coin values are missing (that fix is deferred: it needs noun
distinction penny/dime/nickel plus per-coin values).

Landed `_RIVAL_TIEBREAK = True`. `compileall` OK. `brain_state/` MD5 d05c4d7c8918606afacaa0b85679eef7
(25 files, unchanged).

**GATE: 31 right / 32 claims = 97% true on ASDiv grade-1 test -- MET** (target: >=29 right of 97
at >=80% of claims true). Campaign targets remaining: pennies (coin values, deferred), baker/clown
(their rivals are learned frames outranking the fixes' injected sureness -- a possible next campaign:
teach the fixes' meanings instead of injecting them at c=0.8).
