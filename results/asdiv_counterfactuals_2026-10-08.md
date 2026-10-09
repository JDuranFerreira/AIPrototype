# ASDiv grade-1 test: counterfactuals and root causes (2026-10-08)

All runs read-only against `brain_state/` (byte-identical before/after; baseline = `brain_state_backup_before_asdiv_teach_g1`).
Runner: `benchmarks/asdiv_buckets.py 1 test brain_state <flags>`, guards: `benchmarks/_tmp_guard.py P1..P6 <flags>`.
Gate: >30% right (>=29 of 97) with >=80% of claims true.

## Counterfactuals (ASDiv g1 test, 97 problems)

| configuration | right (claimed) | claims | % true | answers produced | world exams P1..P6 |
|---|---|---|---|---|---|
| baseline | 9 | 11 | 82% | 22 | 96.0 / 91.2 / 89.5 / 90.2 / 88.3 / 83.5 |
| `nogate` (request gate off) | 9 | 11 | 82% | 22 | - |
| `nodoubt` (doubt memory off) | 18 | 33 | 55% | 22 | - |
| `both` | 18 | 35 | 51% | 24 | - |
| `names` (unknown capitalised word = name) | 9 | 11 | 82% | 21 | - |
| `newnoun` (heard word = possible new noun) | 8 | 11 | 73% | 27 | **90.7 / 80.0 / 78.4 / 79.5 / 78.9 / 76.0 (regressed)** |
| `newnoun2` (as above, but only a word no frame ever used) | 9 | 11 | 82% | 26 | **96.0 / 91.2 / 89.5 / 90.2 / 88.3 / 83.5 (neutral)** |
| `knownnodoubt` (doubt only unfamiliar words) | 17 | 31 | 55% | 22 | - |
| `newnoun2` + `nodoubt` | 19 | 36 | 53% | 26 | - |
| `newnoun2` + `knownnodoubt` | 18 | 33 | 55% | 26 | - |

Ceilings measured: baseline can produce a correct answer in **22/97 (22.7%)**; with `newnoun2`, **26/97 (26.8%)**.
The 30% gate is unreachable by any confidence/gate tuning — more correct readings are required first.

## Root causes (each reproduced and traced)

1. **Question-blocked 44/97 have no value at all** (26 of them: every statement wrote nothing).
   `Clause.labels()` is empty because the clause has no `T` slot: a word that has been *heard*
   (`known()` counts `frames.heard`, e.g. 'had' 42,675, 'cherries' 8) but never learned as a thing
   loses `nounish()`'s unknown-word fallback (`storyreader.py:424`, `not lex.known(w)`), stays an `L`
   literal, so no frame can apply. Words the brain has never heard keep the fallback and do get a `T`.
   Counterfactual `newnoun2` (heard + never used in any learned frame -> possible new noun) fixes this
   with **zero world-exam regression**; the naive version regresses ~10 points because after-number
   positions also hold verbs ('six left').

2. **Doubt memory is saturated**: 500 words stored, 425 at the max count of 8 (`because`, `blue`, `add`,
   `basket`, `bag`...). `Doubts.confirmed()` only clears a word when a *teacher agrees*; self-reads never
   confirm, so counters only grow. `checks.answer = {checked: 8637, passed: 0}` - confirmations never
   landed. Doubt-off recovers 9 correct claims but drops precision 82% -> 55%.

3. **Statement side cannot read two ASDiv shapes** (traced in `benchmarks/_probe_change.py`):
   - "More plums were added to the basket" writes **nothing** (no frame), so "Now there are 21"
     overwrites the start -> answers 21, want 4.
   - comparative before base: "Adam has five more apples than Jackie" + "Jackie has nine" resolve to
     one ownerless cell -> 9, never 14 (the school only tells base-then-comparative).
   - "Sam had 9 math problems" - multi-word nouns give `T=[]`, labels empty.

4. **Vocabulary**: `_sure` requires every word known; 30 test problems contain a word unknown to the
   brain, and only 6 of those 38 words also occur in the dev half. `known` = heard-only words block the
   new-noun fallback (see 1), which is the real vocabulary blocker - not missing word teaching.

5. ASDiv dev-half teaching (`teach_asdiv.py 1 600 3` and `1 600 1`, weights 3 and 1) moved dev right
   3 -> 13 but test right 9 -> 7/9 and claims precision 82% -> 44/50%. It teaches *claiming*, not
   reading. Rejected; `brain_state` restored (0/25 MD5 mismatches).

## Reading errors that remain once doubt releases answers (17 of 36 claims wrong)

comparative (Ellen/Marin 9 want 15, Brian/Paul 7 want 11), change/remaining (plums 21 want 4, birds 4
want 3, muffins 55 want 18, book 11 want 6), coins (pennies 0 want 13), 'taken out' (marbles 2 want 0).

## Files

- `benchmarks/asdiv_buckets.py` - bucket diagnostic + counterfactual flags
  (`nogate`, `nodoubt`, `both`, `names`, `newnoun`, `newnoun2`, `knownnodoubt`,
  `deltafix`, `cellsfix`, `topicfix`, `namesfix`).
- `benchmarks/_tmp_guard.py` - world exam + real stories + ASDiv guard runner (with patchers).
- `benchmarks/_probe_change.py` - school vs ASDiv change-story clause-by-clause trace.
- `benchmarks/_probe_blocked.py` - why each of the 44 blocked problems produced no value.
- `benchmarks/_probe_keys.py`, `_probe_known.py` - frame keys and known/thing/noun state per word.
- `benchmarks/_tmp_wrongclass.py` - failure classes by story type.
- `benchmarks/_tmp_delta.py` - the delta-shaped questions in a split, want/got/claim each.
- `benchmarks/_tmp_deltatrace.py` - clause trace of the delta stories with the reading off/on.
- `benchmarks/_tmp_clausegap.py` - clause-by-clause writes for the rows a doubt release would claim.
- `benchmarks/_tmp_celldiff.py` - row-level off/on diff of any g1 counterfactual.
- `benchmarks/_tmp_namesdiff.py` - row-level off/on diff for `_NAMES_FIX` on any grade (arg = grade).
- `benchmarks/_tmp_comparediag.py`, `_tmp_compare_trace.py` - comparative rows and clause traces.
- `benchmarks/_tmp_conniediff.py`, `_tmp_qprobe.py` - base-before-comparative trace, Q clause internals.
- `benchmarks/_tmp_beforeq.py`, `_tmp_beforetrace.py` - before-questions in a split; cells + Q atoms per story.
- `benchmarks/_tmp_chairsneg.py` - the -9 difference row: cells, atoms, candidate expression.
- `benchmarks/_tmp_birdsneg.py` - the flies-away row: cells and answer per fly-flag.
- `benchmarks/_tmp_rateq.py`, `_tmp_listcells.py`, `_tmp_listdebug.py` - rate/list-sum rows: cells, candidates, injection debug.- `benchmarks/_tmp_namesdiff.py` also diffs any grade for any `_FLAG` (second arg).

## Change/remaining reading fix (landed later the same day)

`newnoun2` was landed first (this morning), then the change/remaining class was attacked as one
counterfactual (traces: `_tmp_changetail.py`, `_probe_keys.py`, `_tmp_g1diff.py`, `_tmp_p3diff.py`).

Mechanisms found for the 26 change/remaining rows (14 wrong + 12 blocked): (a) a transfer-verb
statement acting on an already-known quantity gets read as a plain overwrite (`filled 8` -> boxes = 8
want 5, `read 11` -> 11 want 6) or as a fresh cell of the wrong owner (`bought 2 more` -> 2 want 13),
and (b) words like `cherries`, `shirts`, `customers` that exist in the learned frames but never echo as
nouns stay literal (`L`), so `had N <word>` has no `T` slot and writes nothing.

Splitting the fix and measuring each half:

| part | worlds P1-P6 | real stories | g1 answers | verdict |
|---|---|---|---|---|
| nouns: weak-frame heard words get the new-noun chance | flat | unchanged | 26 (g3 46 -> 43) | **dropped** |
| verbs: OUT/IN transfer on an already-known cell | flat (P2 91.2 -> 91.4) | P1 +1, P2 +1, P4 +3, P3 0 differ, P5/P6 0 | **26 -> 29** (claims 9 -> 11 at 100% true) | **landed** |

Refinements measured and required before landing: `grew`/`cooked`/`gained` are *creator* verbs, not
arrivals ("Sally grew 6, Fred grew 4, in all" is summed per person) and `added` must stay out: '9
blocks more are added' is read += correctly by the fix, but the school's Q reading `X + X at first`
then double-counts (95 + 86 = 181 unless the reading stays the lucky overwrite). Dropping those three
verbs from `_IN_VERBS` restores the P3 real stories 13/13 while keeping the g1 gains.

Landed in `brainlike/storyreader.py` (flag `_CHANGE_FIX_VERB = True`, `_IN_VERBS`, `_OUT_VERBS`):
after the plain `= N1` meaning wins and the target cell already holds a known quantity, a change-family
verb gets the self-referential departure (`X - N`) or arrival (`X + N`) reading instead.
`_CHANGE_FIX_NOUN` stays off (measured g1-neutral, g3-negative).

After landing (full guards, read-only state):
- worlds P1-P6 **96.0 / 91.4 / 89.5 / 90.2 / 88.3 / 83.5** (P2 +0.2, never worse)
- real stories **25 / 11 / 13 / 6 / 9 / 9** of 60 (was 24/10/13/3/9/9)
- ASDiv g1 **right 11, claims 11 (100% true), always answers 29** (was 9/11/26)
- kindergarten **389/400** (was 387/400), recipes 0 better / 0 worse / 200 unchanged
- `compileall`, `check.ps1` (164 backend + 16 frontend, router 97%), `npm run build` green

Remaining change/remaining work (each its own counterfactual next): the delta question (landed
below), the before-total question ("to begin with / before" when the departure is a part),
list-of-parts sums (total/altogether across cells), and the weak-frame noun-echo question (rejected
here because it sank g3 answers 3, not because it was wrong).

## Delta question reading (landed later the same day)

The change verb part above made the *statements* write the right cells, but a question like
"How many plums were ADDED?" still read the cell as it stands now (21, want 4). The cells already
keep both values (`atoms(question=True)` adds `F:` = the cell at first when it differs), so the
reading is the difference -- and the naive `it is now` reading of that same cell is dropped rather
than kept as a rival that would just block the claim.

Wiring (`_CHANGE_FIX_DELTA`, landed): in `Frames.answer`, when the question words contain a
change-family doing-verb (`_DELTA_Q`), the question does NOT ask for what is left / before / a total
(`_NO_DELTA_Q`), and some cell it wrote twice is known now and at first with `now != first`, insert
`cell~F:cell` (`~` = bigger minus smaller, so the sign any doing-verb wants) at the front, gated by
the count-of-thing request, and drop the plain `cell` reading.

Measured (counterfactual then landed; full guard suite identical before/after the flag flip):

| | before delta | with delta |
|---|---|---|
| worlds P1-P6 | 96.0 / 91.4 / 89.5 / 90.2 / 88.3 / 83.5 | **same** |
| real stories | 25 / 11 / 13 / 6 / 9 / 9 | **same** |
| g1 right / claims / correct answers | 11 / 11 / 29 | 11 / 11 / **31** |
| g2 answers, g3 claims | 26, 10 | **27**, 9 (lost a wrong claim: precision up) |
| kindergarten, recipes | 389/400, 0/0/200 | **same** |

Row level (traced in `benchmarks/_tmp_deltatrace.py`): plums 21 -> **4**, Adam 8 -> **10**, both now
correct; `batteries`/`shoes` (list-of-parts) do not fire -- no cell has first != now there, so the
currently-claimed 19 stays; Hilt (rate x time) excluded by `_NO_DELTA_Q` (`had`).

The two correct delta answers are still not *claimed*: plums is doubt-blocked on `basket` and Adam on
`delete` (unheard word + clause-guess). The reading now produces 31/97 correct values; the doubt
memory (425/500 words frozen at count 8, `confirmed()` never fires on self-reads) and the heard-count
gate are the next wall, not the reading.

## The cell-fallback reading -- REJECTED (measured the same day)

Traced the rows a doubt release would newly claim (`benchmarks/_tmp_clausegap.py`): two more
statement-side gaps showed up. (a) verb forms: `taken` was not in `_OUT_VERBS`, so "two marbles are
taken out" never departed (added `taken`/`eaten` -- measured flat everywhere on their own, kept).
(b) the same quantity under two owners: statement 2 targets `basket's marble` (from "out OF THE
BASKET") while the story's marbles live in the ownerless cell, so the departure had no known cell to
act on. The counterfactual (`_CHANGE_FIX_CELLS`, `change_cell()`): when a change clause's own target
holds nothing yet, depart from / arrive at the known cell of the same noun (its owner first, then
the ownerless one, then a lone other), else -- with `_CHANGE_FIX_TOPIC` -- the story's topic cell
("1 flies away" -> the bird cell).

| guard | baseline | cellsfix (same noun) | topicfix (with topic) |
|---|---|---|---|
| worlds P1..P6 | 96.0 / 91.4 / 89.5 / 90.2 / 88.3 / 83.5 | **94.0 / 88.4 / 87.2 / 87.2 / 85.6 / 80.4** | same as cellsfix |
| real stories | 25/11/13/6/9/9 | 25/11/13/6/9/9 | 24/10/13/5/9/9 |
| g1 answers, g2 answers | 31, 27 | 32, 24 | 32, 24 |
| kindergarten | 389/400 | **379/400 (days 40 -> 30)** | 379/400 |

The ASDiv win (marbles want 0 got 0) is bought with 2-3 points on EVERY world exam and 10
kindergarten stories: the same noun under another owner gets hit instead of the clause's own.
**Rejected**; `_CHANGE_FIX_CELLS` / `_CHANGE_FIX_TOPIC` stay off (the code is kept behind the flags
as the measurement of why the obvious generalisation fails -- an owner-agnostic fallback is not a
reading, it is a guess). Row-level diff tool: `benchmarks/_tmp_celldiff.py`.

## The doubt wall, measured (not touched)

Re-measured the doubt-release counterfactuals on the post-reading-fix code (`_tmp_deltatrace.py`
shows the per-row blocks):

| configuration | right | claims | % true |
|---|---|---|---|
| as landed | 11 | 11 | 100% |
| `nodoubt` (doubt memory off) | 22 | 36 | 61% |
| `knownnodoubt` (doubt only unfamiliar words) | 21 | 33 | 64% |

Releasing doubt triples the correct claims (11 -> 21/22 of the gate's needed 29) but drags precision
to 61-64%, under the 80% bar: the readings behind those wrong claims are still wrong (comparative,
rate, list sums, `1 flies away`, a claimed **-9** on "how many chairs" -- a count can never be
negative). The gate needs both walls moved: more correct readings first, then a doubt release that
only lets the *checked* readings through (the tool-check pass exists but only marks `passed("tool")`;
it never clears a word -- `Doubts.confirmed` needs a teacher, and an exam has none).

## The comparative reads itself: known word as person -- LANDED

Row diagnosis (`_tmp_comparediag.py`, `_tmp_compare_trace.py`, `_tmp_compare_apply.py`): in
"Ellen has six more balls than Marin", `Ellen`/`Brian`/`Paul` sit in the pretrained word table
(`known=True` but `person=None`), so `perceive` refuses to tag them as new people (line: a word is
person only when `not lex.known(w)` and it sits in a subject slot). The clause keeps ONE cell (the
base person's, or ownerless), its sig is `N_TP`/`N_T`, the missing-mechanism picks the self-referential
`more|N_TP` -> `P1 = N1 + P1` reading, and the taught cross-person pair `more|PN_TP` ->
`P1.T1 = N1 + P2.T1` (n=1549) can never be offered. Result: Ellen 9 (want 15), Brian 7 (want 11),
both doubt-blocked; Connie/Juan likewise mismatched when the base statement runs first.

The fix (`_NAMES_FIX`, landed):

- **Rule C** -- in `clauses()`, a quantity clause containing `more/fewer/less ... than` tags its
  leading known name and the name after `than` as person (`_name_slot`: alpha, not `_FUNCTION`, not
  `_VERB_WORDS`, frames say not verb).
- **Rule S** -- the subject of any quantity clause is tagged person only when the word was *already*
  made a person earlier in this story (the comparative's second person coming back in its own
  statement: "Paul has seven plums"). Its pending ownerless counts (`sit.pending`) are claimed back
  when it converts, so a base statement written before the comparative still lands in the right cell.
- **Perceive line 592** -- an in-story person (`w in sit.people`) is re-tagged `P` even when the word
  is known, so the question "does JUAN have?" reads juan's cell instead of falling back to the
  subject-threaded connie cell. Flag-independent; measured neutral off-flag (worlds/kindergarten/
  recipes/g1-g6 byte-identical to baseline).

Measured (flag on vs off, one process via `_tmp_namesdiff.py` row diff):

| metric | baseline | namesfix |
|---|---|---|
| worlds P1..P6 | 96.0 / 91.4 / 89.5 / 90.2 / 88.3 / 83.5 | **identical** |
| real stories | 25/11/13/6/9/9 | identical |
| g1 right / claims / answers | 11 / 11 (100% true) / 31 | 11 / 11 / **33** (Ellen 9->15, Brian 7->11) |
| g2 | 5 / 8 / 27 | 5 / 8 / 27 |
| g3 | 4 / 9 / 46 | **5 / 8 / 47** (Adam +1 right claim; Belle/Laurie wrong claims dropped) |
| g4..g6 | 0/3/9, 0/1/1, 0/1/3 | identical |
| kindergarten | 389/400 (days 40) | 389/400 |
| recipes | 5/5, 0/0/200 | identical |

`check.ps1` green (164 backend + 16 frontend, router 97%), `npm run build` green.

Rejected sub-variant, recorded as the measurement of why the obvious generalisation fails: converting
**every** known subject (not just established persons) was g1-negative -- it splits the shared
ownerless cell that two-clause sums and differences read: "Marin has nine apples and Donald has two"
11 -> 9 (claimed wrong), Ryan's collected/lost/thrown chain 22 -> None, the Adam/Michele difference
claim lost, Allan/Jake 6 -> 2 (net right 11 -> 9, claims 11 -> 10). Rule S is therefore restricted
to already-established persons. Tools: `_tmp_namesdiff.py`, `_tmp_conniediff.py`, `_tmp_qprobe.py`.

## The before question reads the first value -- LANDED

`_tmp_beforeq.py` lists the questions asking for the amount BEFORE ("before", "to begin with", "in
the beginning"): 9 of 97 in g1 (right 1, claims 1), 6 of 162 in g2 (right 0). The pure ones were
reading the cell as it stands NOW (oranges 3 want 8, chef 4 want 19, rachel 4 want 7, ned 6 want
19) or not answering at all (book fair None want 6).

The fix (`_BEFORE_FIX`, landed): in `Frames.answer`, next to the delta block -- a question whose
words include a before-word (and no difference/left/total word) answers with the cell's at-first
atom (`F:cell`, the same machinery the delta question uses) and drops the plain now-reading of that
same cell. The delta guard `_NO_DELTA_Q` already excludes before-questions from the change reading,
so the two trades are disjoint.

Measured (row diff `_tmp_namesdiff.py 1 _BEFORE_FIX`):

| metric | off | on |
|---|---|---|
| g1 right / claims / answers | 11 / 11 / 33 | 11 / 11 / **35** (oranges 8, chef 19) |
| g2 answers | 27 | **28** |
| g3 answers | 47 | **48** |
| worlds P1..P6, real stories | 96.0/91.4/89.5/90.2/88.3/83.5, 25/11/13/6/9/9 | identical |
| kindergarten, recipes | 389/400, 5/5 + 0/0/200 | identical |

The g1 row diff shows ONLY the two intended rows -- no collateral. The four pure-before rows that
did NOT move are statement-side gaps, not question-reading gaps (`_tmp_beforetrace.py`): Rachel
"picked three from her tree" lands in the ownerless cell while "now the tree has four" lands
tree-owned (owner split -- no cell ever has first!=now; the two cells hold the parts), Ned's
gave-away ran with no base to depart from and "now has six" plain-overwrote (the rejected-cellsfix
territory), the book-fair noun never even became a `T` slot. The three difference-shaped
before-rows (chairs, Haley, clown) are excluded by the word sets; the claimed **-9** chairs row
stays open as its own bug. Tools: `_tmp_beforeq.py`, `_tmp_beforetrace.py`.

## Never claim a negative -- LANDED

With the doubt switched off, two claimed answers were nonsense negatives -- chairs **-9** (want 12)
and the fair **-12** -- plus negative *answers* hiding correct ones: the difference rows computed
`2*now-first` (plums -3 want 3, squirrels -4) instead of `first-now`. The filter (`_NONNEG_FIX`,
landed): no reading evaluating below zero is ever kept -- not even as the last-resort `spared`
value. A quantity in these stories, nor a difference of quantities, is negative; the negative
claimed only because nothing else worked out.

Measured (`_tmp_namesdiff.py 1 _NONNEG_FIX`, row diff):

| row | got off -> on |
|---|---|
| Sharon/Allan plums difference | -3 -> **3** (right) |
| furniture chairs difference | -9 -> **12** (right) |
| squirrels/nuts difference | -4 -> 4 |
| fair spent (list sum) | -12 -> None (no claim) |

Guard: worlds P6 **83.5->83.8** (P1-P5 flat), g1 answers **35->37** (plums+chairs right),
g2 right **5->6**, g3 claims 8->7 and g4 claims 3->2 (wrong claims removed), g6 answers +1,
kindergarten 389/400 + recipes flat, **no right-count losses**. Release precision:
`nodoubt` **70%->74%** (26 right / 35 claims); chairs -9 and fair -12 gone from the wrong list.
check.ps1 + npm build green. Flag default True.

## '1 flies away' reads as a departure -- LANDED

Under the doubt-off release, '4 birds are sitting on a branch. 1 flies away' claimed **4** (want 3):
the number's chunk() swallowed 'flies' as the plural noun 'fly' and built a separate noun cell
`(None, fly) 0 -> -1`, so the bird cell never changed. The fix (`_FLY_FIX`, landed) has three
measured parts: (a) `chunk()` no longer consumes a fly-verb directly followed by 'away'/'off' as a
counted noun (so the main loop sees it); (b) perceive tags that fly-verb as L -- only next to
'away'/'off', so a bare 'two flies sat' stays a noun; (c) the change-verb injection recognizes the
fly family as departures (`_FLY_AWAY`), so the frame departs from the story's own cell.

Measured: g1 row diff shows ONLY the birds row (4->3, answerok 0->1); worlds P1-P6 identical to
landed baseline, kindergarten 389/400 + recipes flat, g1 answers **37->38**; release precision
`nodoubt` **74%->76%** (26 right / 34 claims; birds off the wrong list). Trace tool:
`_tmp_birdsneg.py`; runners take `flyfix`.

## A total question sums the list -- LANDED (narrow)

The muffins row ("three classes bake 18, 20, 17 ... how many in all") answered 18: the question's
own slots reach one cell, no candidate can span three owners. `_LIST_FIX` writes the sum of the
cells straight into the candidate list. The dangerous part was narrowing it so it stops breaking
taught rows -- three rejected variants, measured:

| variant | measurement |
|---|---|
| sum EVERY cell of the noun | worlds -1pt every level (P1 96.0->94.8 ...), kg **389->382** (each 40->33), g3 answers 48->43 -- parts added to their own totals (4 + inferred 28) and same-unit quantities (pool 25m) |
| divisor guard only | worlds crash (zero-valued cell), g3 still 48->45: farm 60->77, butterflies 4764->29 (same owner, black+yellow dots) |
| named owners, >=2 cells | g1 muffins ok but g3 farm 60->77 (part 17 next to written total 60), butterflies 4764->29 |
| **LANDED: named owners, >=3 cells, no value dividing another, never ownerless** | g1 row diff **ONLY muffins 18->55**, g3 row diff **EMPTY**, worlds/kg (each 40/40)/recipes **identical**, g1 answers **38->39**, nodoubt precision **76%->79%** (27 right / 34 claims) |

The sum folds into ONE atom ('Z') because the expression grammar takes at most two terms
(`evaluate("Z0+Z1+Z2")` returns None). Traces: `_tmp_listcells.py`, `_tmp_listdebug.py`,
`_tmp_rateq.py`; runners take `listfix`.

## A rate is read from its unit -- LANDED

'Mrs. Hilt ate 5 apples every hour. How many apples had she eaten at the end of 3 hours?' answered 5.
Two bad readings, one in each half:

- The statement: key `ate|*` is a change verb, so 'ate 5 apples' became a DEPARTURE from an unknown
  base (`hour's apple = -5+unknown`) instead of the per-unit amount the sentence states.
- The question: key `of|*` read 'at the end of' as at-first-minus-now (0 - (-5) = 5), and the learned
  `end|*` key offered a doubling (`hour's apple*2` = 10) ahead of the right product (15, present but
  ordered last).

`_RATE_FIX` (a) in `apply`: a rate phrase (`every|each|per|a <time-unit>`) with ONE number whose own
reading came out unknown or negative writes the cell as POSITIVE and known -- but only when the frame
already put the cell under that unit word (`hour's apple`), and it sets first=0 like the teacher's own
rate rows; (b) in `answer`: an end-of-time question (`end of|after|within` + time word) multiplies the
question's number by whichever slot reads a TIME-OWNED cell (`N1*slot`), moved in front of the learned
doubling. The teacher's rate rows ('reads 5 books a day' / 'in 3 days') evaluate known+positive and keep
their learned keys untouched.

Measured: g1 row diff ONLY apples (5->15, +1 right answer), g3 diff EMPTY, worlds (all six levels and
the real stories) / kindergarten (days 40/40) / recipes identical, always-answers 39->40, release
precision `nodoubt` 79%->**82%** (28 right / 34 claims). Traces: `_tmp_rateq.py`; runners take `ratefix`.
The gate needs 29 claimed-right; the release is now one row/one right claim short.
