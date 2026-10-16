# Blocked-rows campaign 1/2: known plural nouns (2026-10-12)

User goal: brain toward qwen level (~85% raw on ASDiv). Phase 1: the 62 blocked/guess
rows on grade 1 (buckets: 33 question-blocked + 29 clause-guess; claims 31/32).

## Diagnosis (traces for all 62, `blocked_dump.txt` in scratch)

Biggest sharp cluster: **heard-but-never-learned words locked out of noun slots**.
`lex.thing("shirts")` is None after 18 hearings — once a word is heard ≥3 times
without classification, `nounish()` can never take it (thing? no; in-story noun? no;
`is_noun`? refuses frame-used words; unknown-branch? known) and it sits in L
forever. "Tom has 12 shirts" dies while "Tom has 5 apples" works — thing, not name.
Same lock: lives, kittens, seashells, customers, cherries (footprints 22–424 in L).

## Landing 4: `_KNOWN_NOUN` — plural-looking words after numbers chunk as nouns

`brainlike/storyreader.py` `chunk()` only (statements and `how many` questions share
it). Gate: plural morphology (adverbs — away/still/more/each/left — never look
plural; verified item by item) + not function/verb/colour/person/pronoun/number/day
(both forms, so `mondays` stays a setting). Rejected alternative `_CHANGE_FIX_NOUN`
went g3-negative; this one is lexical + positional instead of footprint-based.

## Measured (copies first, then landed)

- Probes, zero learning: shirts 12 ✓, kittens 9 ✓, seashells 4 ✓, cherries 3 ✓
  (ate-departure fired), Edward lives 7 (right-guess), waiter 18 (right, `6 left`
  still dark — ellipsis without verb, next).
- Grade 1: **31/32 → 35/36 = 97%** (+4 claimed-right: cherries, walked-miles,
  kittens, seashells; +5 right-on-guess; no-Q-frame bucket 9 → 0; always-answering
  47 → 56). One new wrong claim: Roger-times (15+3 answered 15−3=12 — went+times
  arrival unlearned; perception right, frames wrong — deferred like pizza).
  Pizza fixed back to silence as a side effect.
- Grades 2/3/6 rights: 25→30, 25→33, 4→6. Worlds/real-story exams up broadly
  (P5/P6 worlds +6, real +8 — locked nouns lived in taught-kind tales too).
- Guards: kg 389/400, recipes 0/0/200, state MD5 unchanged (read-only throughout).
- Costs stated: g4/g6 claim precision down (rights flat/+2) — premature M/cell
  claims on untaught kinds (miles-wide/long area/perimeter now perceivable but
  never taught; age algebra; equations). Same out-of-gate status as ever (never
  ≥80%); the fix is teaching those procedures next (area = w×l is expressible now;
  perimeter 2(w+l) needs a new form — logged).

## Open (next in this campaign)

- Arrival-`left` ellipsis (`6 left`), transfer-all (Skittles), each-first groups
  (pizza), legs facts (3-op), area/perimeter school kinds, coin values.
