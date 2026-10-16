"""Reading the request: what may answer 'how many X?'

Extracted from storyreader.py (size plan step 3, 2026-10-09); storyreader re-exports every name
here so old imports keep working. The gate keeps a reading that computes dollars-per-pen from
answering a question about pens.
"""
import re

from .expressions import _EXPR, _UNITARY, uses
from .perception import singular, _WHERE, _NOT_NOUNS


# ---- reading the request: what may answer 'how many X?' -------------------------------------------------

def _term_unit(clause, label):
    """The noun a single term counts ('P1.T1' -> 'pen'); None for numbers and unknowns."""
    if label.startswith("F:"):
        label = label[2:]
    if not label.startswith("P"):
        return None
    cell = clause.cell(label)
    return cell[1] if cell else None


def counts_thing(clause, expr, thing):
    """Could this reading's value be a count of `thing`, the noun the question asks about?
    'How many pens cost 15 dollars?' must not be answered by dollars-per-pen. This looks only at
    what the terms ARE counts of, never at their values; a term that says nothing ('N1', a cell it
    cannot find) may count anything, and so may a whole expression it cannot parse."""
    u = _UNITARY.match(expr)
    if u:
        a, b, c = u.groups()
        unit = _term_unit(clause, c) or _term_unit(clause, a)   # (a/b)*c counts c of them, else of a's kind
        return unit is None or unit == thing
    m = _EXPR.match(expr)
    if not m:
        return True
    t1, op, t2 = m[1], m[3], m[4]
    if not op:
        unit = _term_unit(clause, t1)
        return unit is None or unit == thing
    ua, ub = _term_unit(clause, t1), _term_unit(clause, t2)
    if op == "/":
        return ub is None or ub != thing        # a top counted out of bottoms: counts the top noun
    if op in "&^":                              # full groups / groups needed: a count of the bottom noun
        # '253 people ^ 5 people-per-car' -> 51 cars: the bottom rate lives in a car-owned cell, so
        # the result counts the container's noun, not the content's noun. Checking the bottom term's
        # noun alone (e.g. 'person' in P2.T2) would wrongly reject this needed-total reading.
        ub_owner = _term_owner(clause, t2)
        return ub_owner is None or ub_owner == thing
    if op == "%":
        return ua is None or ua == thing        # what is left over of the top noun
    if op == "!":
        return ub is None or ub == thing        # a percent of the bottom noun
    if ua and ub and ua != ub:                  # a sum or product of two kinds counts neither alone
        return thing not in {ua, ub}
    unit = ua or ub
    return unit is None or unit == thing


def _term_owner(clause, label):
    """The owner a single term lives in ('P2.T2' -> 'car'); None for numbers and unknowns."""
    if label.startswith("F:"):
        label = label[2:]
    if not label.startswith("P"):
        return None
    cell = clause.cell(label)
    return cell[0] if cell else None


def _group_owner(clause, t1, t2):
    """The container a total-divided-by-rate counts ('253 people ^ 5 per car' -> 'car').

    Total (ownerless people) grouped by a per-container rate (car-owned people) counts
    the containers, not the content. -> the owner noun, or None when this is not that
    shape (different contents, neither side owned, ...)."""
    c1 = clause.cell(t1[2:] if t1.startswith("F:") else t1) if t1.startswith(("P", "F:")) else None
    c2 = clause.cell(t2[2:] if t2.startswith("F:") else t2) if t2.startswith(("P", "F:")) else None
    if not c1 or not c2:
        return None
    (o1, n1), (o2, n2) = (c1[0], c1[1]), (c2[0], c2[1])
    if n1 != n2:
        return None
    if o1 is None and o2 is not None:
        return o2
    if o2 is None and o1 is not None:
        return o1
    return None


def scope_owner(clause, thing):
    """The noun the question locates its answer in: 'how many people are in ONE CAR' wants the people
    of one car, not all the people there are. -> the owner noun, or '' when the question does not
    narrow things down that way (the gate must only fire when the words themselves fired it)."""
    items = clause.items
    for i, it in enumerate(items):
        if it[0] != "L" or it[1] not in _WHERE:
            continue                                   # 'in', 'on', 'at', ... -- the question locates it
        for nxt in items[i + 1:i + 4]:                 # 'in one car', 'in the box', 'on each table'
            if nxt[0] == "T":
                owner = singular(nxt[1])
                return "" if not owner or owner == thing or owner in _NOT_NOUNS else owner
            if nxt[0] in ("V", "P", "T"):              # 'cost Tom', 'held are ...': not a location
                break
    return ""


def by_owner(clause, expr, owner):
    """True when every cell this reading touches belongs to `owner` -- and it touches at least one,
    so a pure-number reading ('N1*2') is not mistaken for a scoped one. Terms that are not cells
    (the question's own numbers) say nothing about the owner and are ignored."""
    def cell_of(label):
        label = label.replace("F:", "")
        if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
            return None
        return clause.cell(label)
    cells = [c for c in (cell_of(l) for l in uses(expr)) if c]
    return bool(cells) and all(c[0] == owner for c in cells)


def _self_owned(clause, target):
    """True when the reading writes to a cell where the owner IS the noun ('jar's jar'): a slot
    error, never a meaning -- no jar holds jars. Targets that are not cells pass through."""
    label = target.replace("F:", "")
    if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
        return False
    cell = clause.cell(label)
    return bool(cell) and cell[0] is not None and cell[0] == cell[1]


def _scales_content_total(clause, target, expr):
    """True when the reading infers an ownerless container count by scaling the sentence's own
    number with the CONTENT total ('each car holds 5 people' with 253 people in mind -> 1265 cars).
    The sentence says how many content go in one container; multiplying by all the content gives
    content-squared per container, never a container count (the legitimate direction -- per-container
    times the container count giving all the content, '12 per jar times 72 jars' -- passes through:
    there the multiplier counts the owner, not the content). Targets that are not ownerless cells,
    non-products, and products whose cell multiplier is not this clause's owned content pass through."""
    m = _EXPR.match(expr)
    if not m or m[3] != "*":
        return False
    label = target.replace("F:", "")
    if not re.fullmatch(r"P\d\.T\d(?:@D\d)?", label):
        return False
    cell = clause.cell(label)
    if not cell or cell[0] is not None:
        return False
    owner = cell[1]
    others = [a for a in uses(expr) if not re.fullmatch(r"N\d+", a)]
    if len(others) != 1 or not re.fullmatch(r"(?:F:)?P\d\.T\d(?:@D\d)?", others[0]):
        return False
    acell = clause.cell(others[0].replace("F:", ""))
    if not acell:
        return False
    contents = {c[1] for lb in clause.labels() for c in (clause.cell(lb),)
                if c and c[0] == owner and c[1] != owner}
    return acell[1] in contents


