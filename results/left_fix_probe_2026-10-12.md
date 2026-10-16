# _LEFT_FIX probe (2026-10-12)

## Question
Why does "6 left", "some left" not trigger departure? The word "left" after a number should mean "departed".

## Diagnosis
Traced "6 left" clause:
- Perception: `[('N', 6), ('L', 'left')]` — "left" tagged as L (literal), not V (verb)
- Frame table has `left|*` with `expr=N1` (departure) at c=0.694
- But candidate filtered by threshold 0.7 (c=0.694 < 0.7)
- Also: `_self_owned` filter removes candidates where owner==thing

## Root Causes
1. **Threshold 0.7**: `left|*` has c=0.694 < 0.7, filtered out
2. **No verb frame**: "left" never learned as departure verb (only as remainder "left over")
3. **WORDLESS block**: _LEFT_FIX logic was inside `if not clause.nums` block, skipped for "6 left" (has number)

## Fix Design
1. Add `_LEFT_FIX` flag (mirrors `_FLY_FIX`)
2. Add departure logic in `apply()` BEFORE main filter, OUTSIDE WORDLESS block
3. Detect bare "left" (not "left over", not stative)
4. Case 1: promote existing `left|*` candidate (c=0.694 → 0.9)
5. Case 2: create departure from `sit.thing` when no candidates
6. Relax threshold 0.7 → 0.65

## Probes
- "Tom has 12 apples. Six left." → 6 ✓
- "A waiter had 18 customers. If six left, how many?" → 12 (waiter not person, vocabulary issue)
- "18 cookies. 6 left." → 12 ✓

## Threshold Trade-off
- 0.7: 31/31 g1 (100%), but "left" fails
- 0.65: 31/32 g1 (97%), "left" works
- Gate: ≥29 right at ≥80% → both pass (31/31=100%, 31/32=97%)