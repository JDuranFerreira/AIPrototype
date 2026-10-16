# Multi-op teacher probe (2026-10-12)

Question chosen by the user: lift the single-op limit in `expressions()` — it blocks
every S3 zero kind and the rejected average-of-three / two-step-equation kinds.

Live code is the monolith `brainlike/storyreader.py` (2,726 lines). The `model.py` /
`expressions.py` / `scope.py` / `perception.py` / `frames.py` files from the 10-09 size
plan are orphaned (nothing imports them); the refactor never switched callers over.
Multi-op work goes in `storyreader.py` (+ `primary.py` teacher), not the orphans.

## Probe: what the teacher can explain today

`benchmarks`-style probe (20 tales/kind, `explain(tale)` final line has a sum or bare
answer). Script: `C:\Users\Jose\AppData\Local\Temp\opencode\probe_multiop.py`.

| kind | explained /20 | note |
|---|---|---|
| interest | 0 | `money + money*rate*years/100` — 4 ops, deepest |
| volume | 0 | `l*w*h` — 2 ops |
| threestep | 6 | `(each*want)-give` — 2 ops; 6 coincide with a single-op reading |
| ratio | 15 | 5 bare are an atom-availability gap, not an op gap (see below) |
| average, proportion, convert, circle, discount, twostep, groups, speed | 20 | teacher fine; exam zeros there are reading failures, not teacher failures |

Ratio bare case (`4 pencils make 5 pies … 10 pies → 8`): `explain()` builds atoms only
from end cells + question numbers + unit facts. `4` and `5` live only in sentence 1,
so `(4/5)*10` is unformable at explain time. The answering path has the same atoms
(`clause.atoms(sit, question=True)`), so ratio questions need sentence numbers as
question atoms — a separate, smaller fix from chaining.

Average-2 works today via half-terms (`x/2 + y/2`); average-3 needs thirds, which do
not exist — it needs its own special form like unitary.

## Design (follows the unitary precedent: special forms gated by ops, not general n-op)

1. **Chained two-step** (`_TWO_STEP` flag, off default): second layer combining each
   first-layer single-op value once more with a base atom (`(a*b)-c`, `(a*b)*c`,
   `(a+b)-c`, …). Covers volume + threestep + ratio remainder. Cap: only `+ - *`
   on the outer step, first-layer values memoised; measure the hot-path cost
   (`expressions()` did 30M calls/lesson before the 10-04 caches).
2. **Interest special form** (like `(a/b)*c`): `money + money*rate*years/100` with
   `evaluate` / `show_work` (percent_steps exists; working = yearly rate then total;
   check by undoing) / `uses` / `tool_ops` / `_plainest` + `KIND_RULE` entries
   (`ratio`, `interest`, `volume`, `threestep`, currently missing).
3. **Gating in `candidates()`**: chained forms must NOT trip the `"u"`-only
   `startswith("(")` rule — gate on their own flag. `plain()` tie-break prefers
   single-op (already counts atoms + `(`/`2`/`~`/ruled penalties; extend).
4. **Guards**: flag-off runs byte-identical (guard P1–P6 + ASDiv g1 31/31 + kg 389/400
   + recipes 0/0/200 + code exam 43/44); flag-on measured counterfactual-first on
   copies, `brain_state/` MD5 unchanged (read-only until an explicit teach).

Deferred: average-of-three (`(a+b+c)/3` form), two-step/dividing equations
(`divides` verb untaught — lexicon work first), non-clock durations, 12-hour wrap,
coin values, baker/clown creditable injection, floor/ceiling tools.
