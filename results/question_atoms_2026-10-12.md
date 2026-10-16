# Question-atoms campaign (2026-10-12): M1, M2, ... — the shared blocker

User-chose follow-up to the multi-op campaign. Threestep/ratio/interest questions need
numbers that live in the sentences (`gives away 3`, `4 pencils make 5`), not in the end
cells or the question — the reader had no way to use them (recipes cover them in chat
via `{n}` roles, but the exam path could not).

## Landing 3: `_M_ATOMS` — each acted statement's numbers as M1, M2, ... (question only)

`Situation.story_nums` accumulates every acted statement's own known numbers in story
order; `apply` and `observe_statement` both append, so learning and answering build
identical histories (verified by construction: same text → same clause order; override
probes use discarded sits). `atoms(question=True)` adds them as M1... (known only,
index-stable with Nones skipped). Statements never see M (a sentence's meaning is
local — cross-sentence coincidences must not become statement meanings). The rest of
the machinery is label-agnostic (verified first in scratch): `_TERM`/`_CHAINED` parse
M labels, `evaluate`/`uses`/`tool_ops`/`by_owner` work unchanged, `counts_thing` is
lenient (M terms say nothing about nouns).

## Riding with it (same flag)

- **Unitary `va == vb` relax** (`expressions`): distinct atoms may share a value.
  Without it, want==made tales could never credit the unitary shape while opportunity
  counting still charged them (c stuck at 0.55, gate needs 0.7 — forensics: 22/40
  credited). Same-atom pairs stay skipped (`(x/x)*c` is true for every c: pure bloat).
- **Teller degenerate-tale fixes** (`primary.py`, ungated generation): ratio never asks
  for what the story says (want==made teaches ANS=M1 plain); threestep never gives away
  more than there are (negative counts are impossible, not a lesson).
- **Ratio plural-put bug** (`primary.py`): scenes said `stamps`, the reader hears
  `stamp` — statement learning silently matched nothing in 50 tales (Q learning worked:
  it matches told answers, not scenes). Now singular like every other put.

## The pollution incident and its two guards (all measured)

The first sleep with M on credited M-coincidences into pooled keys (12k pairs) and
per-situation keys (33k): g1 went 31/31 → 31/35 (89%). Repaired and guarded:
1. **`credit()` rank guard**: M-meanings only on rank-3 (word-in-frame) keys. M1 is
   crates in one tale and pencils in the next — frame-specific roles must not pool
   into `how|*`. One-time sweep purged existing rank≤2 M-pairs (12,121 + 32,676).
   Paige fixed back to honest silence; kinds unaffected (their learnings are rank-3).
2. **M count floor (cnt ≥ 10)** in `candidates()`: M roles need 10 payoffs (shoe
   totals from 9 chances died; real learnings are 40+).
3. **`/` noun refinement** in `counts_thing()`: a dividing top must also be of the
   asked kind when it says what it is (`2 chickens / 2` is not legs; `180 km / 3`
   still answers km). Legs row fixed.
4. A `sit.thing` desc carry was NOT needed (probes showed the fallback covers it).

One g1 row remains wrongly claimed (pizza, M2/M1=4): its higher readings were
correctly gated out (they count pizzas, Q asks slices) and its statements never acted
(each-first group phrasing is unlearned) — needs groups-phrasing work, deferred.
**Gate: 31/32 = 97% (≥29 at ≥80% met).**

## Real-brain teaches (backups first, both verified byte-identical)

- threestep+ratio (100 tales + sleep): threestep 0/60 → **60/60 claimed**; ratio
  60/60 right but 0 claimed (s1 meanings were never learned — plural-put bug era).
- ratio re-teach (150 tales + sleep, singular fixed): **60/60 claimed, 100% true**.
- S2 same-items 86.4% → **87.2%** (ratio 2/20 → 20/20); P2–P6 same-items all up
  (+0.3..+1.7, understood +4–6pp; mass/needed/square the movers); P1 identical-items
  zero diffs (sets 0+7); kindergarten 389/400; recipes 0/0/200.
- Costs, stated plainly: g1 100% → 97% (pizza, deferred above); ASDiv g3+ claim
  precision slipped out-of-gate (rights flat, +12 claims on g3 — diffuse sleep-
  consolidation churn, wins and losses, e.g. oven/Adam newly claimed-right, Hilt
  bread flipped on an N1-plain meaning); P3 real 28→27 (Skittles, from the volume
  teach — transfer-all un-understood in both states, old answer was doubling luck).
  Cross-session guard numbers also wobble with live backend chat writes to usage
  files — same-items static diffs are the robust measure, used throughout.

## Open (not this campaign)

- Interest: needs M-atoms (done) + a 4-op special form (or two taught steps).
- Pizza row (each-first group statements) + legs row needs (3-op + animal-leg facts).
- Noun-aware chained-`*` gate (M-transparent products).
- Average-of-three, dividing equations, floor/ceiling, coin values, baker/clown
  creditable injection, grade-2 gate.
