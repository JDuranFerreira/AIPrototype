"""The frame learner: which small explanations a sentence's words are credited with.

Extracted from storyreader.py (size plan step 5, 2026-10-09); storyreader re-exports every name
here so old imports keep working. The campaign flags stay defined on storyreader (the CF
runners setattr them there); the three methods that read them do a late import at call time.
"""
import re
from fractions import Fraction

from .coordination import Coordination
from .model import Lin
from .expressions import _RULED, change_cell, evaluate, expressions, show_work, tool_ops, uses, write
from .perception import (singular, _BEFORE_Q, _DELTA_Q, _FLY_AWAY, _FUNCTION, _IN_VERBS, _NOUN_SHAPE_MAX,
                         _NO_BEFORE_Q, _NO_DELTA_Q, _OUT_VERBS, _RATE_PHRASE, _RATE_Q, _TIME_UNITS,
                         _TOTAL_Q, _VERB_WORDS)
from .request import what_is_asked
from .scope import _scales_content_total, _self_owned, by_owner, counts_thing, scope_owner


TRUST = {3: 1.0, 2: 0.97, 1: 0.9, 0: 0.85}     # a word in its frame > the word anywhere > the frame shape > anything


# ---- reading the request (extracted to scope.py, 2026-10-09; re-exported here) ---------------------
from .scope import (  # noqa: F401  (re-export)
    _term_unit, counts_thing, _term_owner, _group_owner, scope_owner, by_owner,
    _self_owned, _scales_content_total,
)


class Frames:
    def __init__(self, data=None, coordination=None):
        d = data or {}
        self.coord = coordination if coordination is not None else Coordination()
        if d.get("rules") and not self.coord.rules:      # old layout / bare engine file: the tools it was taught
            self.coord.rules.update(d["rules"])
        self.table = {"S": d.get("S", {}), "Q": d.get("Q", {})}     # kind -> key -> {"n": .., "m": {pair: count}}
        self.pron = d.get("pron", {})                               # word -> {"n": .., "boy": .., "girl": ..}
        self.heard = d.get("heard", {})                             # words heard in stories
        self.nouns = d.get("nouns", {})                             # words it met as things (after a number)
        # the same tallies kept per KIND OF SITUATION (kindergarten, P1, P2, real P1, ...), as for words: each
        # situation where a meaning could apply has a say in how sure it is, however many lessons it had
        self.by_situation = d.get("by_situation", {})               # situation -> kind -> key -> {n, m, o}
        self.situation = "chat"                                     # where it is now (set by the lessons)
        self.units = d.get("units", [])                             # unit facts the teacher taught (P5)
        # sureness results are cached per (kind, key, meaning); credit() is the only place the tables
        # change, so it bumps the revision and empties the cache (see sureness)
        self._rev, self._sure_cache = 0, {}

    @property
    def rules(self):
        return self.coord.rules                       # the taught tools live in the coordination region

    @property
    def ops(self):
        return "".join(self.rules)

    def bind(self, coordination):
        """Hand the region's coordination to this engine (Mind._bind): the tools, their cue words and
        their rewards belong to the coordination region, not to the frames."""
        if coordination is None or coordination is self.coord:
            return
        coordination.take_over(self.coord)
        self.coord = coordination

    def ops_for(self, clause):
        """The rules it may use in this clause: which tools the coordination region allows here."""
        words = {it[1] for it in clause.items if it[0] in ("L", "T")} if clause is not None else set()
        return self.coord.allowed(words)

    BALANCED = True                                                  # judge meanings per situation (else pooled)
    BLOCKING = False                                                 # a word that already explains it blocks the rest
    APPEARED = True                                                  # a thing that just appeared: changes were wrong
    WORDLESS = True                                                  # a sentence with no number needs a word to act
    LAST = -1                                                        # which changed thing stays in mind (-1: last)
    TRACK = True                                                     # a sentence it can't act out still says what it's about
    SAY = 50                                                         # chances a situation needs for a full say

    def state(self, prune=True):
        table = {}
        for kind, keys in self.table.items():
            table[kind] = {}
            for k, e in keys.items():
                n = e["n"]
                m = {p: c for p, c in e["m"].items() if not prune or n < 10 or _sure(e, p) >= 0.3}
                if m or n >= 3:
                    table[kind][k] = {"n": n, "m": m, "o": {p: o for p, o in e.get("o", {}).items() if p in m}}
        by = {}
        for name, kinds in self.by_situation.items():
            by[name] = {}
            for kind, keys in kinds.items():
                by[name][kind] = {}
                for k, e in keys.items():
                    kept = table[kind].get(k)
                    if kept is None:
                        continue
                    by[name][kind][k] = {"n": e["n"], "m": {p: c for p, c in e["m"].items() if p in kept["m"]},
                                         "o": {p: o for p, o in e["o"].items() if p in kept["m"]}}
        return {**table, "pron": self.pron, "heard": self.heard, "nouns": self.nouns, "by_situation": by,
                "rules": self.rules, "units": self.units}

    # -- pronouns --
    def pronoun(self, w):
        p = self.pron.get(w)
        if not p or p["n"] < 3:   # a pronoun goes anywhere a name goes
            return None
        # Common pronouns that may not have many frame types but are definitely pronouns
        if w.lower() in ("he", "she", "it", "they", "them", "him", "her", "his", "hers", "its", "their", "theirs", "we", "us", "our", "ours", "i", "me", "my", "mine", "you", "your", "yours"):
            for g in ("boy", "girl", "thing"):
                if p.get(g, 0) / p["n"] >= (0.9 if g != "thing" else 0.85) and \
                        all(p.get(o, 0) / p["n"] <= 0.5 for o in ("boy", "girl", "thing") if o != g):
                    return g
        # For other words, require at least 3 frame types
        if len(p.get("frames", ["", "", ""])) < 3:
            return None
        for g in ("boy", "girl", "thing"):
            if p.get(g, 0) / p["n"] >= (0.9 if g != "thing" else 0.85) and \
                    all(p.get(o, 0) / p["n"] <= 0.5 for o in ("boy", "girl", "thing") if o != g):
                return g
        return None

    def observe_pronouns(self, clause, involved_genders):
        for it in clause.items:
            if (it[0] == "L" and it[1].isalpha()) or (it[0] == "P" and it[3]):
                p = self.pron.setdefault(it[1], {"n": 0})
                p["n"] += 1
                for g in involved_genders:
                    p[g] = p.get(g, 0) + 1
                frames = p.setdefault("frames", [])
                if clause.sig not in frames and len(frames) < 5:
                    frames.append(clause.sig)

    # -- learning --
    def credit(self, kind, clause, pairs, atoms, weight=1, appeared=()):
        """Each word in its frame (and the frame shape) is credited with the explanations that came true.
        It also counts, for every explanation it knows for that key, whether it was POSSIBLE this time
        (its numbers and cells were there): a meaning is judged only where it could have applied."""
        labels = set(clause.labels()) | {"ANS"} | {f"F:{x}" for x in clause.labels() if x in atoms}
        here = self.by_situation.setdefault(self.situation, {}).setdefault(kind, {})
        keys = clause.keys()
        for p in pairs:                                   # every confirmed explanation that used a tool:
            for op in tool_ops(p.split("=", 1)[-1]):      # the coordination region earns a reward for it
                self.coord.reward(op, True)
        if self.BLOCKING:
            keys = self._unblocked(kind, keys, pairs)
        for _, k in keys:
            e = self.table[kind].setdefault(k, {"n": 0, "m": {}, "o": {}})
            h = here.setdefault(k, {"n": 0, "m": {}, "o": {}})
            e.setdefault("o", {})
            e["n"] += weight
            h["n"] += weight
            for p in pairs:
                e["m"][p] = e["m"].get(p, 0) + weight
                h["m"][p] = h["m"].get(p, 0) + weight
            for p in e["m"]:
                target, expr = p.split("=", 1)
                if target in labels and all(a in atoms or (a == target and a in appeared) for a in uses(expr)):
                    e["o"][p] = e["o"].get(p, 0) + weight
                    h["o"][p] = h["o"].get(p, 0) + weight
        # the tables just changed: every sureness computed before this sentence is now wrong, so the
        # cache goes and the revision moves on (sureness reads nothing else that can change)
        self._rev += 1
        self._sure_cache.clear()

    def _unblocked(self, kind, keys, pairs):
        """Blocking (as in Rescorla-Wagner): if a word in its frame already explains what happened, the other
        words of the sentence learn nothing from it ('2 toys were removed': 'removed' explains it, so 'were' is not
        taught that it takes things away). The frame shape still learns, so a sentence of new words is never lost."""
        explain = []
        for rank, k in keys:
            e = self.table[kind].get(k)
            if rank == 3 and e and e["n"] >= 5 and any(p in e["m"] and self.sureness(kind, k, e, p)[0] >= 0.8
                                                       for p in pairs):
                explain.append(k)
        if not explain:
            return keys
        words = {k.split("|")[0] for k in explain}
        return [(rank, k) for rank, k in keys if k in explain or rank <= 1 or (rank == 2 and k.split("|")[0] in words)]

    def sureness(self, kind, k, e, p):
        """How sure a meaning is -> (sure, count, chances). Cached: candidates() asks about the same
        (kind, key, meaning) over and over while it reads a story (it was 2M calls in one lesson, each
        walking every situation), and credit() invalidates the whole cache whenever the tables change."""
        hit = self._sure_cache.get((kind, k, p))
        if hit is not None and hit[0] == self._rev:
            return hit[1]
        out = self._sureness(kind, k, e, p)
        self._sure_cache[(kind, k, p)] = (self._rev, out)
        return out

    def _sureness(self, kind, k, e, p):
        """How sure a meaning is: count / (chances + 1). Balanced: worked out in every situation where it could
        have applied, and averaged, each situation weighted by its evidence up to a full say (SAY chances), so a
        stage with thousands of lessons can't outvote one with hundreds. -> (sure, count, chances)"""
        cnt = e["m"][p]
        chances = max(e.get("o", {}).get(p, e["n"]), cnt)
        if not self.BALANCED or not self.by_situation:
            return cnt / (chances + 1), cnt, chances
        num = den = 0.0
        rest_m, rest_o = cnt, e.get("o", {}).get(p, 0)
        parts = []
        for kinds in self.by_situation.values():
            h = kinds.get(kind, {}).get(k)
            if h:
                m, o = h["m"].get(p, 0), h["o"].get(p, 0)
                rest_m, rest_o = rest_m - m, rest_o - o
                parts.append((m, o))
        parts.append((max(rest_m, 0), max(rest_o, 0)))   # 'earlier': what it learned before it kept situations apart
        for m, o in parts:
            o = max(o, m)
            if not o:
                continue
            w = o / (o + self.SAY)
            num += w * m / (o + 1)
            den += w
        if not den:
            return cnt / (chances + 1), cnt, chances
        return num / den, cnt, chances

    def _word_keys(self):
        cached = getattr(self, "_word_keys_cache", None)
        size = sum(len(t) for t in self.table.values())
        if cached is None or cached[0] != size:
            cached = (size, {k.split("|", 1)[0] for t in self.table.values() for k in t if "|" in k})
            self._word_keys_cache = cached
        return cached

    def _word_footprint(self, w):
        """How strongly the learned frames ever used the word at all (sum of its row sizes). A verb that has
        been taught in hundreds of stories is huge; a word that drifted in on a few lessons is not a verb."""
        cached = getattr(self, "_foot_cache", None)
        size = sum(len(t) for t in self.table.values())
        if cached is None or cached[0] != size:
            fp = {}
            for t in self.table.values():
                for k, e in t.items():
                    if "|" not in k:
                        continue
                    fp[k.split("|", 1)[0]] = fp.get(k.split("|", 1)[0], 0) + e["n"]
            cached = (size, fp)
            self._foot_cache = cached
        return cached[1].get(w, 0)

    def is_noun(self, w):
        from .storyreader import (  # late: the CF runners set these on storyreader
            _CHANGE_FIX,
            _CHANGE_FIX_NOUN,
        )
        if self.nouns.get(w, 0) >= 2 or self.nouns.get(singular(w), 0) >= 2:
            return True
        # A word the story has only ever HEARD (never perceived, no learned frame has ever used it) may still be
        # the new noun it never got to meet. A word with a grammar job ('six left', 'had 11') stays literal, and
        # so does any word some learned frame has ever used, so verbs are not read as things in noun positions.
        if w in _FUNCTION or self.pronoun(w) or self.heard.get(w, 0) == 0:
            return False
        keys = self._word_keys()[1]
        if w not in keys:
            return True
        # Counterfactual: a word the frames have only used a LITTLE (and that is no known verb) still gets the
        # new-noun chance, so 'cherries', 'shirts', 'customers' become things instead of invisible literals.
        # The rule stays OFF unless the runner switches _CHANGE_FIX on.
        if (_CHANGE_FIX or _CHANGE_FIX_NOUN) and w not in _VERB_WORDS and self._word_footprint(w) <= _NOUN_SHAPE_MAX:
            return True
        return False

    def word_property(self, w):
        """Learned property of a word from its frames. 
        Returns a set of properties: 'det', 'glue', 'break', 'between', 'small', 'where', 'not_noun', 'verb', 'prep'"""
        from .storyreader import singular
        w_singular = singular(w)
        props = set()

        # Known as a noun (after number, taught as thing) - check singular form
        if self.is_noun(w_singular):
            props.add("noun")
            return props  # nouns don't get other properties

        # Check frames where this word appears (rank 3: word in its frame, signature has _ marker)
        # Use original word form for frame lookup (frames are stored under original forms)
        frame_keys = [k for k in self.table.get("S", {}) if k.startswith(w + "|") and "_" in k.split("|", 1)[1]]
        frame_keys_q = [k for k in self.table.get("Q", {}) if k.startswith(w + "|") and "_" in k.split("|", 1)[1]]
        all_frames = frame_keys + frame_keys_q

        if not all_frames:
            return props

        # Analyze frame shapes to infer word category
        # Rank 3 key format: "word|sig_with_underscore" where _ marks word position in sig
        # sig uses P,N,T,D for person, number, thing, day
        # Examples: "the|_PNT" (at start before P_N_T), "has|P_NT" (after P, before N_T)

        pos_patterns = []
        for fk in all_frames:
            if "|" not in fk:
                continue
            sig = fk.split("|", 1)[1]  # signature with _ marking position
            if "_" not in sig:
                continue
            # Split signature at _: before = sig[:pos], after = sig[pos+1:]
            pos = sig.index("_")
            before = sig[:pos]
            after = sig[pos+1:]
            pos_patterns.append((before, after))

        # Classify based on dominant frame position
        # Count frames by position type
        start_NT = 0      # _N, _T, _NT... (frame start before N/T) -> determiner
        start_P = 0       # _P, _PN... (frame start before P) -> break/prep
        start_other = 0   # _D, _other -> prep
        after_P = 0       # P_... (after person) -> verb
        after_content = 0 # PNT_, NT_, T_... (after content) -> preposition
        between_content = 0 # between N/T/P elements
        total_weight = 0

        for fk in all_frames:
            if "|" not in fk:
                continue
            sig = fk.split("|", 1)[1]
            if "_" not in sig:
                continue
            pos = sig.index("_")
            before = sig[:pos]
            after = sig[pos+1:]
            weight = self.table["S"].get(fk, {}).get("n", 1)
            total_weight += weight

            if not before:
                # Frame start
                if after and after[0] in ("N", "T"):
                    start_NT += weight
                elif after and after[0] == "P":
                    start_P += weight
                elif after and after[0] in ("D",):
                    start_other += weight
                else:
                    start_other += weight
            elif before and before[-1] == "P":
                # After person
                after_P += weight
            elif before and before[-1] in ("N", "T", "D"):
                # After content word (thing, number, day)
                after_content += weight
                # Check for between pattern
                if after and after[0] in ("N", "T", "P") and before[-1] != after[0]:
                    between_content += weight
            else:
                after_content += weight

        # Primary classification based on dominant pattern - winner takes all for primary
        primary = None

        # Noun check (using singular form for noun lookup)
        if self.is_noun(w_singular):
            primary = "noun"

        # Special cases for known function words
        if w in ("is", "are", "was", "were", "am", "be", "been", "left", "removed", "taken", "got", "gotten", "found", "made", "won", "lost", "drops", "dropped", "broke", "broken", "ate", "eaten", "sold", "spent", "bought", "picked", "used", "threw", "thrown", "gave", "given", "took", "taken", "picked", "received", "collected", "got", "gets", "got"):
            primary = "verb"
        elif w in ("his", "her", "their", "my", "your", "our", "its", "every", "each", "all", "both", "some", "any", "another"):
            primary = "det"  # determiners including quantifiers
        elif w in ("then", "now"):
            primary = "break"
        elif w in ("more", "less", "fewer"):
            primary = "between"
        elif w in ("with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "per"):
            primary = "prep"

        # Determine primary category from dominant frame position (if not special-cased)
        if not primary and total_weight > 0:
            ratios = {
                "det": start_NT / total_weight,
                "verb": after_P / total_weight,
                "prep": (start_P + start_other) / total_weight,  # exclude after_content for prep
                "break": start_P / total_weight,
                "between": between_content / total_weight,
            }

            # Prepositions that appear between content: don't classify as "between"
            # The "between" category is for comparatives (more/less), not prepositions
            prep_words = {"with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "about", "into", "onto", "upon", "over", "under", "above", "below", "between", "among"}
            if w in prep_words:
                ratios["between"] = 0  # force zero

            # Find dominant category above threshold
            candidates = [(cat, ratio) for cat, ratio in ratios.items() if ratio >= 0.35]
            if candidates:
                primary = max(candidates, key=lambda x: x[1])[0]

        # Fallback: glue for high-frequency connectors
        if not primary and self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
            clause_connect = 0
            for fk in all_frames:
                if "|" not in fk:
                    continue
                sig = fk.split("|", 1)[1]
                if "_" not in sig:
                    continue
                pos = sig.index("_")
                before = sig[:pos]
                after = sig[pos+1:]
                if before and after and before[-1] in ("N", "T", "P", "D") and after[0] in ("N", "T", "P", "D"):
                    clause_connect += self.table["S"].get(fk, {}).get("n", 1)
            if clause_connect / total_weight >= 0.3:
                primary = "glue"

        # Small: high frequency, many frames, no primary category
        if not primary and self.heard.get(w, 0) > 2000 and len(all_frames) >= 15:
            primary = "small"

        props = set()
        if primary:
            props.add(primary)
            if primary == "prep":
                props.add("where")

        # Secondary categories (compatible only)
        if primary == "det":
            # Determiners can also be "break" if they start clauses (each, every)
            if total_weight > 0 and start_P / total_weight >= 0.3:
                props.add("break")
        elif primary == "verb":
            # Verbs can be "glue" if high-frequency connectors
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                props.add("glue")
        elif primary == "prep":
            # Prepositions can be "between" if between content (but not for known preps)
            prep_words = {"with", "by", "from", "to", "for", "of", "at", "in", "on", "as", "about", "into", "onto", "upon", "over", "under", "above", "below", "between", "among"}
            if total_weight > 0 and between_content / total_weight >= 0.2 and w not in prep_words:
                props.add("between")
            # Can be "glue" if clause connector
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                clause_connect = 0
                for fk in all_frames:
                    if "|" not in fk:
                        continue
                    sig = fk.split("|", 1)[1]
                    if "_" not in sig:
                        continue
                    pos = sig.index("_")
                    before = sig[:pos]
                    after = sig[pos+1:]
                    if before and after and before[-1] in ("N", "T", "P", "D") and after[0] in ("N", "T", "P", "D"):
                        clause_connect += self.table["S"].get(fk, {}).get("n", 1)
                if clause_connect / total_weight >= 0.3:
                    props.add("glue")
        elif primary == "break":
            # Break words can be "glue" if also connector
            if self.heard.get(w, 0) > 500 and len(all_frames) >= 10:
                props.add("glue")
        elif primary == "between":
            # Between words can be "prep/where" if also prepositional
            if total_weight > 0 and (start_P + start_other) / total_weight >= 0.3:
                props.add("prep")
                props.add("where")

        # Not noun: appears in noun-like positions but not noun/verb/det/prep
        if not self.is_noun(w_singular) and self.heard.get(w, 0) > 100:
            noun_like = start_NT + after_P
            if total_weight > 0 and noun_like / total_weight >= 0.3:
                if primary not in ("noun", "verb", "det", "prep"):
                    props.add("not_noun")

        return props

    def met_things(self, clause):
        """The words it saw as things are thing words from now on, even once they are familiar."""
        # Function words that should never be marked as nouns even if they appear in T positions
        NOT_NOUNS_MET = {"and", "or", "but", "so", "then", "of", "to", "for", "with", "in", "on", "at", "by", "from", "the", "a", "an", "his", "her", "their", "my", "your", "our", "its", "this", "that", "these", "those", "each", "every", "some", "any", "all", "both", "more", "less", "few", "many", "much", "fewer", "same", "other", "another", "such", "what", "which", "who", "whom", "whose", "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "do", "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must"}
        for it in clause.items:
            if it[0] == "T":
                for w in it[1].split(" of "):
                    if w not in NOT_NOUNS_MET:
                        self.nouns[w] = self.nouns.get(w, 0) + 1

    def hear(self, toks):
        """The ear hears every word of a sentence (before perception has worked out what they are)."""
        for w in toks:
            if w.isalpha():
                self.heard[w] = self.heard.get(w, 0) + 1

    def observe_statement(self, clause, before, after):
        """What did this clause do? Every small explanation the scene makes true."""
        atoms = clause.atoms(before, learning=True)
        exprs = expressions(atoms, self.ops_for(clause))
        pairs, appeared = [], set()
        for label in clause.labels():
            key = clause.cell(label)
            v = after.read(*key)
            if v is None:
                continue
            if self.APPEARED and label not in atoms and before.read(*key) is None:
                f = after.read(*key, first=True)
                if f is not None and f.known and v.known and f.c == v.c:
                    appeared.add(label)                 # it just appeared with this many: nothing was taken or added
            same = label in atoms and atoms[label].c == v.c
            # nothing changed: 'now she has 21' when she has 21. It can't have DONE something to it, so explanations
            # that use it ('twice 21 minus 21') are coincidences, not meanings
            pairs += [f"{label}={e}" for e in exprs.get(v.c, []) if e != label and not (same and label in uses(e))]
            if same:                                          # it says nothing new about now: maybe about the start
                f = after.read(*key, first=True)
                pairs += [f"F:{label}={e}" for e in exprs.get(f.c, []) if e != label and label not in uses(e)]
        if pairs:
            self.credit("S", clause, sorted(set(pairs)), atoms, appeared=appeared)
        return pairs

    def observe_question(self, clause, sit, answer, weight=1):
        # Enrich question clause with dimension adjectives for area/perimeter/volume
        if hasattr(sit, 'dimensions') and sit.dimensions:
            qtext = " ".join([it[1] for it in clause.items if it[0] == "L"])
            if any(w in qtext.lower() for w in ("area", "perimeter", "volume", "cubic")):
                owners = [p for p in clause.P if p is not None]
                for owner in owners:
                    for (ot_owner, ot_thing), dim_map in sit.dimensions.items():
                        if ot_owner == owner and dim_map:
                            new_T = []
                            for noun, adjs in clause.T:
                                if noun == ot_thing:
                                    for dim in dim_map.keys():
                                        new_T.append((ot_thing, (dim,)))
                                else:
                                    new_T.append((noun, adjs))
                            clause.T = new_T
                            break
        atoms = clause.atoms(sit, question=True, learning=True)
        exprs = expressions(atoms, self.ops_for(clause))
        pairs = [f"ANS={e}" for e in exprs.get(Fraction(answer), [])]
        if pairs:
            self.credit("Q", clause, sorted(set(pairs)), atoms, weight)
        return pairs

    # -- understanding --
    def candidates(self, kind, clause, atoms):
        """Every meaning its words and frame suggest that can apply here, surest first. Sure = how often it
        came true when it was possible, a little less sure with little evidence (count / (chances + 1)).
        A word in its own frame wins a tie over the word anywhere, which wins over the bare frame shape."""
        print(f"DEBUG candidates: kind={kind}, clause.keys()={[k for _,k in clause.keys() if 'cubic' in k]}")
        labels = set(clause.labels()) | {f"F:{x}" for x in clause.labels() if x in atoms} if kind == "S" else {"ANS"}
        out = []
        allowed = self.ops_for(clause)             # the same rules for every key of this clause
        for rank, k in clause.keys():
            e = self.table[kind].get(k)
            if not e or e["n"] < (2 if rank else 1):
                continue
            for p in e["m"]:
                target, expr = p.split("=", 1)
                if target not in labels or any(a not in atoms for a in uses(expr)):
                    continue
                if expr.startswith("(") and "u" not in allowed:
                    # Allow chained two-step expressions with plain operators (+, -, *)
                    # even without unitary tool: (a*b)*c, (a+b)*c, etc.
                    from .expressions import _CHAINED
                    ch = _CHAINED.match(expr)
                    if not (ch and ch.group(2) in "+-*" and ch.group(4) in "+-*"):
                        continue
                if any(o in expr for o in "#$!") and not any(o in allowed for o in "#$!" if o in expr) or \
                        (len(uses(expr)) == 2 and uses(expr)[0] == uses(expr)[1] and "q" not in allowed):
                    continue
                c, cnt, chances = self.sureness(kind, k, e, p)
                if (rank >= 2 and (c < 0.7 or cnt < 2)) or (rank == 1 and c < 0.5):
                    continue
                c *= TRUST[rank] * (0.99 if "~" in expr or any(o in expr for o in _RULED) else 1) * \
                    (0.995 if "2" in expr.replace("N2", "") else 1)
                # on a tie the plainer explanation wins: minus over difference, no doubling over doubling
                out.append({"rank": rank, "c": c, "n": chances, "key": k, "target": target, "expr": expr})
        # Rectangle area fallback: if area frames exist but the atoms have multiple dimension cells
        # (e.g., P1.T2 with 'long', P1.T3 with 'wide'), also check for rectangle area frame
        if kind == "Q":
            for rank, k in clause.keys():
                if k.startswith("area|") or k.startswith("area_rect|"):
                    # Check if atoms have multiple dimension cells for the same owner/thing
                    dim_cells = [a for a in atoms if a.startswith("P") and ".T" in a]
                    if len(dim_cells) >= 2:
                        if k.startswith("area|"):
                            rect_key = "area_rect|" + k.split("|", 1)[1]
                        else:
                            rect_key = k
                        e = self.table[kind].get(rect_key)
                        if e and e["n"] >= 1:
                            # Find the rank of rect_key in clause.keys()
                            rect_rank = 0
                            for r, k2 in clause.keys():
                                if k2 == rect_key:
                                    rect_rank = r
                                    break
                            if rect_rank == 0:
                                rect_rank = rank  # fallback to original rank
                            for p in e["m"]:
                                target, expr = p.split("=", 1)
                                if target not in labels or any(a not in atoms for a in uses(expr)):
                                    continue
                                if expr.startswith("(") and "u" not in allowed:
                                    continue
                                if any(o in expr for o in "#$!") and not any(o in allowed for o in "#$!" if o in expr) or \
                                        (len(uses(expr)) == 2 and uses(expr)[0] == uses(expr)[1] and "q" not in allowed):
                                    continue
                                c, cnt, chances = self.sureness(kind, rect_key, e, p)
                                if (rect_rank >= 2 and (c < 0.7 or cnt < 2)) or (rect_rank == 1 and c < 0.5):
                                    continue
                                c *= TRUST[rect_rank] * (0.99 if "~" in expr or any(o in expr for o in _RULED) else 1) * \
                                    (0.995 if "2" in expr.replace("N2", "") else 1)
                                out.append({"rank": rect_rank, "c": c, "n": chances, "key": rect_key, "target": target, "expr": expr})
        plain = lambda x: len(uses(x["expr"])) + x["expr"].startswith("(") + ("2" in x["expr"].replace("N2", "")) + ("~" in x["expr"]) + \
            any(o in x["expr"] for o in _RULED) + (len(set(uses(x["expr"]))) < len(uses(x["expr"])))
        out.sort(key=lambda x: (-round(x["c"], 2), -x["rank"], plain(x), -x["n"]))   # a tie: the plainer one
        return out

    def apply(self, clause, sit, asked=None):
        """Act a statement out. -> what it did, or None if it has no idea.
        `asked` (the request read from the question) is accepted but deliberately NOT used to pick
        the statement's meaning: what a sentence says cannot depend on what is asked afterwards --
        'Mia collected another 4 oranges' is an addition whatever the question wants, and reading it
        as a plain 4 because the question asks what is left destroyed the kindergarten exam and P1
        (measured 2026-10-07: exam 234/400, P1 78%). The request gate belongs on the ANSWER's
        readings (Frames.answer), one layer down, where it is checked against the question clause."""
        from .storyreader import (  # late: the CF runners set these on storyreader
            _CHANGE_EVENT,
            _CHANGE_FIX,
            _CHANGE_FIX_CELLS,
            _CHANGE_FIX_OWNERLESS,
            _CHANGE_FIX_TOPIC,
            _CHANGE_FIX_VERB,
            _CHANGE_PROMOTE,
            _FLY_FIX,
            _RATE_FIX,
        )
        atoms = clause.atoms(sit)
        cands = self.candidates("S", clause, atoms)
        # a change to something it hasn't heard of yet ('Paco ate 19 cookies'): he must have had some
        # out of order: it may need an amount it hasn't heard yet ('6 more than Marin', 'Paco ate 19'):
        # it keeps an unknown for it, which a later sentence can find
        counted = {it[1] for it in clause.items if it[0] == "T" and len(it) > 3} | ({sit.thing[0]} if sit.thing else set())
        missing = {lb: Lin(0, {"?": 1}) for lb in clause.labels() if lb not in atoms and "@" not in lb
                   and clause.cell(lb) and clause.cell(lb)[1] in counted and sit.read(*clause.cell(lb)) is None}
        if missing:
            wider = [x for x in self.candidates("S", clause, {**atoms, **missing})
                     if sum(a in missing for a in uses(x["expr"])) == 1 and re.fullmatch(
                         r"(?:N\d[+-][A-Z][\w.@:]*|[A-Z][\w.@:]*[+-]N\d)", x["expr"]) and "@" not in x["expr"]]
            if wider and wider[0]["rank"] >= 2 and (not cands or cands[0]["rank"] <= 1 or
                                                      wider[0]["c"] > cands[0]["c"] + 0.05):
                for a in uses(wider[0]["expr"]):
                    if a in missing:
                        start = sit.unknown()
                        sit.cells[clause.cell(a)] = [start, start]
                atoms = clause.atoms(sit)
                cands = self.candidates("S", clause, atoms)
        if not clause.nums and self.WORDLESS:  # no number in it: only a word that means it can change amounts
            cands = [x for x in cands if x["rank"] >= 2]   # ('she ate half'), not the general sentence shapes
        # A cell where a thing owns its own noun is a slot error, not a meaning: 'each jar has 12
        # sandwiches' read as `jar's jar = 12` (the frame's first thing sat in the content slot) made
        # 'how many jars are there' add 72+12. A jar cannot hold jars -- the reading is dropped and
        # the next one is tried; if nothing else fits, the statement is simply not understood.
        # Scaling the sentence's number by the CONTENT total is the same kind of error: 'each car
        # holds 5 people' with 253 people in mind infers 1265 cars (measured 2026-10-07). The sentence
        # says how many content go in ONE container; the legitimate direction (per-container times the
        # container count, '12 per jar times 72 jars' -> all the content) passes through.
        cands = [x for x in cands if not _self_owned(clause, x["target"])
                 and not _scales_content_total(clause, x["target"], x["expr"])]
        if not cands:                          # it has no idea what happened, but it notes what the sentence is about
            if self.TRACK and clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                sit.subject = clause.persons[0]
            if self.TRACK and clause.things:   # 'Zoe thinks of a number': 'it' is the number from now on
                sit.thing = (clause.things[-1][0], ())
            return None
        if _RATE_FIX and len(clause.nums) == 1:       # a rate: 'ate 5 apples every hour'
            m = _RATE_PHRASE.search(" ".join(re.findall(r"[a-z]+", clause.text().lower())))
            n = atoms.get("N1")
            best = evaluate(cands[0]["expr"], atoms)
            if m and n is not None and n.known and (best is None or not best.known or best.c < 0):
                cell = clause.cell(cands[0]["target"].replace("F:", ""))
                if cell and cell[0] == m.group(1):             # the frame put it where the unit owns it
                    if cell in sit.cells:
                        sit.cells[cell][1] = Lin(n.c)          # the per-unit amount is positive and known
                    else:
                        sit.cells[cell] = [Lin(0), Lin(n.c)]   # nothing before the day, like the teacher's first=0
                    done = [{"rank": 1, "c": 0.8, "n": 0, "key": "rate",
                             "target": cands[0]["target"], "expr": "N1", "value": Lin(n.c)}]
                    if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                        sit.subject = clause.persons[0]
                    elif clause.thing_subject and not clause.persons:
                        sit.subject = clause.thing_subject
                    sit.thing = (cell[1], ())
                    return done
        if _CHANGE_EVENT and clause.nums:          # an event cell takes more of the same, not a departure
            evverb2 = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                            or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
            if evverb2 and (evverb2 in _OUT_VERBS or (_FLY_FIX and evverb2 in _FLY_AWAY)) and cands[0]:
                evcell2 = cands[0]["target"].replace("F:", "")
                evkey2 = clause.cell(evcell2) if not evcell2.startswith("F:") else None
                if evkey2 in sit.events:
                    evacc = f"{evcell2}+N1"
                    evhave = next((i for i, x in enumerate(cands)
                                   if x["expr"] == evacc and x["target"] == cands[0]["target"]), None)
                    if evhave is None:
                        cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "*",
                                         "target": cands[0]["target"], "expr": evacc})
                    else:
                        cands.insert(0, cands.pop(evhave))
        if (_CHANGE_FIX or _CHANGE_FIX_VERB) and clause.nums:     # a change-family verb on a quantity it already knows
            verb = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                         or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
            if verb and cands[0] and re.fullmatch(r"N\d+", cands[0]["expr"]):
                sign = "-" if verb in _OUT_VERBS or (_FLY_FIX and verb in _FLY_AWAY) else "+"
                cell = cands[0]["target"].replace("F:", "")
                expr = f"{cell}{sign}N1"
                key = clause.cell(cell) if not cell.startswith("F:") else None
                cur = sit.read(*key) if key else None
                if cur is not None and cur.known:
                    if _CHANGE_EVENT and sign == "-" and key in sit.events:
                        # an event cell TALLIES what went out of it: more going out ADDS to the tally
                        # ('gave away 11' then 'gave away 3 more' -> 14 given, not a balance of 8).
                        expr = f"{cell}+N1"
                    have = next((i for i, x in enumerate(cands)
                                 if x["expr"] == expr and x["target"] == cands[0]["target"]), None)
                    if have is None:
                        cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "*", "target": cands[0]["target"],
                                         "expr": expr})
                    elif _CHANGE_PROMOTE and have > 0:
                        # LANDED 2026-10-09 (measured): the frame table already teaches the departure
                        # ('she READ 11 of the pages' -> P1.T1-N1) but the plain overwrite outranks
                        # it ('read|P_NT' 0.89 vs 'read|*' 0.75), so the meaning the change verb
                        # REQUIRES loses on sureness alone. Move it ahead of the overwrite.
                        cands.insert(0, cands.pop(have))
                elif (cur is None or not cur.known) and _CHANGE_FIX_OWNERLESS:
                    # CF: the clause's own target is an owner the story never gave that noun
                    # ('two marbles are taken out OF THE BASKET' -> basket's marble, empty) while the
                    # story's marbles live in the ownerless cell -- depart from/arrive at the LONE
                    # ownerless known cell of the same noun; never another owner's (the rejected
                    # cellsfix hit other owners' quantities).
                    lone = [k for k, c in sit.cells.items()
                            if k[0] is None and k[1] == key[1] and k[2] == key[2]
                            and c[1].bind(sit.bound).known]
                    n = atoms.get("N1")
                    if len(lone) == 1 and n is not None and n.known:
                        k1 = lone[0]
                        f = sit.cells[k1][1].bind(sit.bound)
                        new = Lin(f.c - n.c) if sign == "-" else Lin(f.c + n.c)
                        if f.known and new.c >= 0:
                            sit.write(*k1, new)
                            done = [{"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": cands[0]["target"], "expr": expr, "value": new}]
                            if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                                sit.subject = clause.persons[0]
                            elif clause.thing_subject and not clause.persons:
                                sit.subject = clause.thing_subject
                elif (cur is None or not cur.known) and (_CHANGE_FIX or _CHANGE_FIX_CELLS or _CHANGE_FIX_TOPIC):
                    # CF (rejected 2026-10-08, flags stay off): the frame's own target holds nothing yet
                    # ('2 marbles are taken out OF THE BASKET' targets the basket's cell, but the story's
                    # marbles live in the ownerless one) -- depart from the KNOWN cell of the same noun
                    # instead. Fixes ASDiv marbles but hits other owners' quantities: worlds -2..3pt.
                    found = change_cell(sit, key, topic=bool(_CHANGE_FIX or _CHANGE_FIX_TOPIC))
                    n = atoms.get("N1")
                    if found and n is not None and n.known:
                        f = sit.cells[found][1].bind(sit.bound)
                        new = Lin(f.c - n.c) if sign == "-" else Lin(f.c + n.c)
                        if f.known and new.c >= 0:
                            sit.write(*found, new)
                            done = [{"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": cands[0]["target"], "expr": expr, "value": new}]
                            if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
                                sit.subject = clause.persons[0]
                            elif clause.thing_subject and not clause.persons:
                                sit.subject = clause.thing_subject
                            sit.thing = (clause.cell(done[self.LAST]["target"].replace("F:", ""))[1], ())
                            return done
        best = cands[0]
        group = [x for x in cands if x["key"] == best["key"]] if best["rank"] >= 2 else [best]
        chosen, cells = [], []
        for x in group:
            cell = x["target"].replace("F:", "")                     # one meaning per cell: now OR its start
            base = cell.split("@")[0]
            clash = any(c == cell or (c.split("@")[0] == base and ("@" in c) != ("@" in cell)) for c in cells)
            if clash or (best["rank"] >= 2 and x["c"] < 0.7):       # a total and one of its parts: not both
                continue
            cells.append(cell)
            chosen.append(x)
        # the sentence's own number, kept where its own frame puts it: when the surest reading INFERS
        # a total by scaling ('each car holds 5 people' -> there are 1265 cars), the frame shape's
        # literal reading ('car's people = 5') still says what the sentence actually said, so the story
        # keeps that too. First in: the word's own write stays the last thing changed (LAST = -1).
        if best["rank"] >= 2 and not re.fullmatch(r"N\d+", best["expr"]):
            for x in cands:
                if x["rank"] != 1 or not re.fullmatch(r"N\d+", x["expr"]):
                    continue
                cell = x["target"].replace("F:", "")                  # one meaning per cell, as above
                base = cell.split("@")[0]
                clash = any(c == cell or (c.split("@")[0] == base and ("@" in c) != ("@" in cell))
                            for c in cells)
                if clash:
                    continue
                chosen.insert(0, x)
                break
        done = []
        evverb = next((it[1] for it in clause.items if it[1] in _OUT_VERBS or it[1] in _IN_VERBS
                       or (_FLY_FIX and it[1] in _FLY_AWAY)), None)
        evout = evverb is not None and (evverb in _OUT_VERBS or (_FLY_FIX and evverb in _FLY_AWAY))
        evwords = set(re.findall(r"[a-z]+", clause.text().lower())) if _CHANGE_EVENT else set()
        values = [(x, evaluate(x["expr"], atoms)) for x in chosen]
        for x, v in values:
            if v is not None:
                evkey = clause.cell(x["target"].replace("F:", ""))
                evfresh = evkey not in sit.cells
                write(sit, clause, x["target"], v)
                if _CHANGE_EVENT and evkey and v.known and not x["target"].startswith("F:"):
                    evcell = sit.cells.get(evkey)
                    # a clause that also states a balance ('he spent a TOTAL of $700', 'initially
                    # had 34') writes that balance, not a tally -- only a bare change statement
                    # ('gave away 11', 'sold 12') starts an event cell
                    if evout and evfresh and not evwords & {"had", "has", "have", "is", "are",
                                                            "was", "were", "initially", "originally",
                                                            "before", "now", "still", "total",
                                                            "altogether", "together"}:
                        # a change statement CREATED this cell: it tallies what went out of it,
                        # it is not a balance ('a clown gave away 11' -> 11 given, nothing told now)
                        sit.events[evkey] = v.c
                    elif evout and evkey in sit.events and evcell and evcell[1].known:
                        sit.events[evkey] = evcell[1].c      # the tally runs with the cell's now
                    elif evverb is None and evkey in sit.events and evcell and evcell[1].known:
                        # a stative write ('now he has 3') stands on a balance the story never told:
                        # at first the cell held the tally more (sold 12; now has 3 -> at first 15)
                        sit.cells[evkey][0] = Lin(evcell[1].c + sit.events[evkey])
                        del sit.events[evkey]
                    elif evkey in sit.events and evcell and evcell[1].known:
                        # an arrival (or any other write) reusing the cell for a different quantity
                        # ('spent $2' then 'bought for $7 each') breaks the tally: drop the mark
                        del sit.events[evkey]
                done.append({**x, "value": v, "work": show_work(x["expr"], atoms)})
        if clause.persons and (sit.subject is None or sit.gender.get(sit.subject) == "thing"):
            sit.subject = clause.persons[0]
        elif clause.thing_subject and not clause.persons:
            sit.subject = clause.thing_subject
        if done:                               # the last thing it changed stays in mind (as when it learns)
            sit.thing = (clause.cell(done[self.LAST]["target"].replace("F:", ""))[1], ())
        elif clause.things:
            sit.thing = (clause.things[-1][0], ())
        return done or None

    def answer(self, clause, sit, rivals=None, atoms_out=None):
        """The surest meaning for this question. `rivals` (a list) is filled with the value of the next
        reading that genuinely competes, and `atoms_out` (a dict) with the numbers it used, so the
        prefrontal can doubt and check without a second pass."""
        from .storyreader import (  # late: the CF runners set these on storyreader
            _BEFORE_FIX,
            _CHANGE_EVENT,
            _CHANGE_FIX,
            _CHANGE_FIX_DELTA,
            _LIST_FIX,
            _NONNEG_FIX,
            _RATE_FIX,
        )
        atoms = clause.atoms(sit, question=True)
        if atoms_out is not None:
            atoms_out.update(atoms)
        # The request gate: the question says what the answer must be a count OF, so only readings
        # that could count that noun may answer it -- and no count of things is between none and one
        # (a dollars-per-pen rate is not an answer to 'how many pens'). If the gate leaves nothing,
        # the reader says it doesn't understand (like the taught recipes do), instead of guessing.
        asked = what_is_asked(clause.text())
        thing = singular(asked["thing"] or "") if asked["kind"] != "money" else singular(asked["thing"] or "")
        cands = self.candidates("Q", clause, atoms)
        if thing:
            keep = [x for x in cands if counts_thing(clause, x["expr"], thing)]
            # ('^' groups-needed counts the bottom noun and '/' a top counted out of bottoms, so the
            # correct '253 people ^ 5 per car' survives through that general rule -- no special case.)
            # The owner scope: 'how many people are in ONE CAR' wants the people of one car, so only
            # readings that live in car-owned cells may answer it (the total, 253, does not). It is a
            # preference, not a veto: with no scoped reading left it keeps what the count gate kept.
            owner = scope_owner(clause, thing)
            if owner:
                scoped = [x for x in keep if by_owner(clause, x["expr"], owner)]
                keep = scoped or keep
            cands = keep
        # The total question: 'how many muffins does first grade bake IN ALL' asks over every cell
        # of that noun (18 + 20 + 17 across three class owners), but the question's own slots only
        # reach one of them -- so the sum of the cells themselves is written as a candidate. Only
        # cells with a NAMED owner count: ownerless cells are the context's own total (or another
        # quantity in the same unit, like the pool's length), not parts of a list.
        if _LIST_FIX and thing and _TOTAL_Q.search(" ".join(re.findall(r"[a-z]+", clause.text().lower()))):
            total, vals = None, []
            for key in sit.cells:
                if key[1] != thing or key[0] is None:
                    continue
                v = sit.read(*key)
                if v is None or not v.known:
                    continue
                vals.append(v.c)
                total = v.c if total is None else total + v.c
                if len(vals) >= 8:
                    break
            # a part next to its own total ('each plate has 4' + the inferred 28) must not be added
            # to that total: when one cell's value divides another's, these are whole-and-parts, so
            # the total question falls back to its usual single-cell reading. Two cells are also
            # too easy to misread (a per-herd part next to a written total); a genuine list has
            # at least THREE owners' parts.
            parts = any(a and a < b and (b / a).denominator == 1 for a in vals for b in vals)
            if len(vals) >= 3 and not parts:      # the expression grammar holds two terms, so the
                v = Lin(total)                    # sum of many cells is written as one atom
                atoms["Z"] = v
                if atoms_out is not None:
                    atoms_out["Z"] = v
                cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "total",
                                 "target": "ANS", "expr": "Z"})
        # The rate question: '5 apples every hour' left the per-unit amount in a TIME-OWNED cell, and
        # 'at the END OF 3 hours' supplies the unit count -- the answer is their product. The learned
        # 'in N days' key offers this for its own phrasing; this covers the other time phrasings, and
        # only when the thing's own cell is owned by a time word (a rate lives under its unit).
        if _RATE_FIX and thing and "N1" in atoms and atoms["N1"].known:
            text = " ".join(re.findall(r"[a-z]+", clause.text().lower()))
            if _RATE_Q.search(text) and set(text.split()) & _TIME_UNITS:
                slot = next((s for s in sorted(atoms) if re.fullmatch(r"P\d+\.T\d+", s)
                             and atoms[s].known and clause.cell(s)
                             and clause.cell(s)[0] in _TIME_UNITS), None)
                if slot:                             # the cell that holds the rate lives under its unit
                    expr = f"N1*{slot}"             # ('hour's apple' x 3 hours)
                    if counts_thing(clause, expr, thing):    # the learned 'end of' key holds this too,
                        cands = [x for x in cands if x["expr"] != expr]   # but AFTER its doubling guess
                        cands.insert(0, {"rank": 2, "c": 0.95, "n": 0, "key": "rate",
                                         "target": "ANS", "expr": expr})
        # The event question: a cell a change statement CREATED with no balance told only tallies
        # what went out of it ('a clown gave away 11, then 3 more' -> the cell holds 14 GIVEN, not a
        # balance). A change question over such a cell wants that tally -- the now-minus-first
        # difference of a tally (14-11) is not the amount given. 'give away TOTAL' still asks for
        # that tally, but the direction requests ('left', 'before', 'at first', 'in a year') are
        # other readings of the same cells and stay out.
        if _CHANGE_EVENT and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if (words & _DELTA_Q and
                    not words & {"left", "remain", "remains", "before", "first", "start", "begin",
                                 "beginning", "now", "more", "need", "have", "has", "had", "are",
                                 "is", "there", "still", "in", "each", "again", "all"}):
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")) or clause.cell(base) not in sit.events:
                        continue
                    if thing and not counts_thing(clause, base, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "event",
                                     "target": "ANS", "expr": base})
                    break
        # The change question: 'how many WERE ADDED / did he eat / did she give' wants the changed
        # amount, not the quantity as it stands now. When a cell it wrote twice is known both now and
        # at first, the answer is the difference -- and the plain 'it is now' reading of that same cell
        # (which ignores the question's own verb) is dropped rather than kept as a rival opinion.
        if (_CHANGE_FIX or _CHANGE_FIX_DELTA) and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if words & _DELTA_Q and not words & _NO_DELTA_Q:
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")):
                        continue
                    if _CHANGE_EVENT and clause.cell(base) in sit.events:
                        continue    # a tally's now-minus-first is not the amount given: the event
                                    # block above already offered the tally itself
                    a, b = atoms[base], atoms[name]
                    if not (a.known and b.known) or a.c == b.c:
                        continue
                    expr = f"{base}~{name}"
                    if thing and not counts_thing(clause, expr, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "change",
                                     "target": "ANS", "expr": expr})
                    break
        # The before question: 'how many oranges were in the basket BEFORE some were taken' wants the
        # quantity as it started, not as it stands now. The cell keeps its at-first value (the F:
        # atom), so the answer is that first value and the plain now-reading of the same cell is
        # dropped -- the delta question's trade, in the other direction.
        if _BEFORE_FIX and re.search(r"[a-z]+", clause.text()):
            words = set(re.findall(r"[a-z]+", clause.text().lower()))
            if words & _BEFORE_Q and not words & _NO_BEFORE_Q:
                for name in atoms:
                    if not name.startswith("F:") or name[2:] not in atoms:
                        continue
                    base = name[2:]
                    if base.startswith(("N", "K")):
                        continue
                    a, b = atoms[base], atoms[name]
                    if not (a.known and b.known) or a.c == b.c:
                        continue
                    if thing and not counts_thing(clause, name, thing):
                        continue
                    cands = [x for x in cands if x["expr"] != base]
                    cands.insert(0, {"rank": 1, "c": 0.8, "n": 0, "key": "before",
                                     "target": "ANS", "expr": name})
                    break
        best = spared = None
        for x in cands:
            if best is not None and (x["rank"] < 1 or x["c"] < best[2] - 0.12):
                continue                      # it cannot rival the surest reading: don't even work it out
            v = evaluate(x["expr"], atoms)
            if v is not None:
                v = v.bind(sit.bound)
                if v.known:
                    said = {**x, "work": show_work(x["expr"], atoms)}
                    if _NONNEG_FIX and v.c < 0:
                        continue          # no quantity (nor difference of quantities) is negative
                    if thing and v.c != 0 and v.c < 1:
                        spared = spared or (v.c, said, x["c"])
                        continue              # not a count of things; kept only as a last resort
                    if best is None:
                        best = (v.c, said, x["c"])
                    elif rivals is not None and v.c != best[0]:
                        rivals.append((v.c, x["c"]))  # a reading that competes, with its sureness
                        break
        best = best or spared
        return (None, None) if best is None else (best[0], best[1])

    def summary(self):
        meaningful = {}
        for kind in ("S", "Q"):
            star = self.table[kind].get("*", {"n": 0, "m": {}})
            for k, e in self.table[kind].items():
                if k.startswith("*") or "|*" in k or e["n"] < 3:
                    continue
                p, cnt = max(e["m"].items(), key=lambda kv: (_sure(e, kv[0]), kv[1]), default=(None, 0))
                if not p or cnt < 3 or _sure(e, p) < 0.75:
                    continue
                shape = self.table[kind].get("*|" + k.split("|", 1)[1].replace("_", ""))
                if shape and shape["m"] and p == max(shape["m"], key=lambda q: (_sure(shape, q) >= 0.5, shape["m"][q])):
                    continue                                   # the frame does that anyway: a grammar word here
                meaningful[k] = p
        pronouns = {w: self.pronoun(w) for w in self.pron if self.pronoun(w)}
        return meaningful, pronouns


def _sure(e, p):
    """How often an explanation came true when it was possible."""
    if not e or not e.get("n"):
        return 0
    cnt = e["m"].get(p, 0)
    return cnt / max(e.get("o", {}).get(p, e["n"]), cnt, 1)
