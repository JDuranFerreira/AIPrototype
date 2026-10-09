"""The index: cue words that say WHERE an answer lives (the hippocampus' index).

The brain keeps its facts in regions that never mix: "capital of france" -> "Paris" sits in the
knowledge region, a single-digit fact in the arithmetic region, a story in memory. To answer a
question the brain should not have to wake every region and read every entry: a few cue words are
enough to know which region holds the answer and under which key. So every stored fact gets an
index entry, the words of its question pointing at (region, key).

Rules that keep it honest:
  * the index is BUILT from what is actually stored - never written by hand;
  * a match must contain EVERY word that identifies the stored key, plus at most a few extra words
    ("please tell me what the capital of france is" still finds it; "what is the capital of
    spain" does not drift onto France);
  * a miss is a miss: the old exact search still runs, so the index can never lose a fact.
"""
import re

# words that say nothing about what a memory is about
NOTHING = {"what", "whats", "is", "are", "was", "were", "the", "a", "an", "of", "in", "on", "at", "to",
           "and", "or", "do", "does", "did", "can", "could", "will", "would", "should", "me", "you",
           "please", "tell", "give", "say", "know", "it", "its", "this", "that", "there", "my", "your",
           "his", "her", "their", "our", "for", "from", "by", "with", "about", "how", "much", "many",
           "now", "s", "t"}

_WORD = re.compile(r"[a-z]+(?:-[a-z]+)*")


def cues(text):
    """The words that identify a memory: 'What is the capital of France?' -> ('capital', 'france')."""
    seen = []
    for w in _WORD.findall((text or "").lower()):
        if w not in NOTHING and w not in seen:
            seen.append(w)
    return tuple(seen)


class Index:
    """cue word -> the entries that word can be found in, plus each entry's cue set for the match.

    Entries are stored by number, not by repeating their text under every cue word: the index is
    itself kept small, because an index that costs more memory than the memories is not worth having.
    """

    def __init__(self, by_cue=None, entries=None):
        self.by_cue = {c: list(v) for c, v in (by_cue or {}).items()}   # cue -> [entry ids]
        self.entries = [(r, k, tuple(cs)) for r, k, cs in (entries or [])]
        self._ids = {(r, k): i for i, (r, k, _) in enumerate(self.entries)}

    def __len__(self):
        return len(self.entries)

    def add(self, region, key, cue_text=None):
        cs = cues(cue_text if cue_text is not None else key)
        if not cs:
            return
        if (region, key) in self._ids:                     # already indexed: keep one entry per key
            i = self._ids[(region, key)]
            self.entries[i] = (region, key, cs)
        else:
            i = len(self.entries)
            self.entries.append((region, key, cs))
            self._ids[(region, key)] = i
        for c in cs:
            ids = self.by_cue.setdefault(c, [])
            if i not in ids:
                ids.append(i)

    def forget(self, region, key):
        i = self._ids.pop((region, key), None)
        if i is None:
            return
        for c in self.entries[i][2]:
            self.by_cue[c] = [j for j in self.by_cue.get(c, []) if j != i]

    def find(self, question, max_extra=3):
        """Every stored entry whose cue words are all in this question -> [(region, key)].

        Closest match first, so the brain tries the most likely place first.
        """
        q = set(cues(question))
        if not q:
            return []
        shared = {}
        for c in q:
            for i in self.by_cue.get(c, ()):                # only the entries this question's words point at
                shared[i] = shared.get(i, 0) + 1
        out = []
        for i in shared:
            region, key, need = self.entries[i]
            need = set(need)
            if need and need <= q:                          # every word that identifies the entry is present
                extra = len(q - need)
                if extra <= max_extra:
                    out.append((extra, -len(need), region, key))
        out.sort()
        return [(region, k) for _, _, region, k in out]

    def where(self, question, max_extra=3):
        return self.find(question, max_extra)

    def probes(self, question):
        """How many stored entries a lookup for this question opens: the ones its cue words point at."""
        q = set(cues(question))
        return len({i for c in q for i in self.by_cue.get(c, ())})

    def trim(self, max_df=32):
        """Drop the cue words that are in too many memories ("number", "answer") from the index.

        Such a word points at hundreds of places, so opening them all costs more than reading the
        shelf - it is not an index any more. They stay in each entry's cue set, so a memory that needs
        one of those words can still be MATCHED; it just cannot be FOUND by it.
        Returns (dropped cue words, entries left unfindable).
        """
        df = {c: len(ids) for c, ids in self.by_cue.items()}
        dropped = [c for c, count in df.items() if count > max_df]
        for c in dropped:
            self.by_cue.pop(c, None)
        reachable = {i for ids in self.by_cue.values() for i in ids}
        return len(dropped), len(self.entries) - len(reachable)

    def state(self):
        return {"entries": [[r, k, list(cs)] for r, k, cs in self.entries],
                "by_cue": {c: ids for c, ids in self.by_cue.items() if ids}}

    @classmethod
    def load(cls, data):
        return cls((data or {}).get("by_cue"), (data or {}).get("entries"))

    @classmethod
    def build(cls, knowledge=None, arithmetic=None, memory=None, episodes=False, max_df=32):
        """Build the index from what the brain actually stores right now.

        Episodes (the stories it lived through) are only indexed when asked for: a story title is a
        whole sentence, so indexing every one of them is expensive and nothing looks them up by cue
        words yet. Told facts and arithmetic facts are always indexed - those are what get asked for.
        """
        idx = cls()
        for k in (knowledge or {}).get("facts", {}):
            idx.add("knowledge", k)
        for k in (arithmetic or {}).get("facts", {}) or {}:
            idx.add("arithmetic", k)
        if episodes:
            for box, stories in (memory or {}).get("episodes", {}).items():
                for title in stories:
                    idx.add("memory", f"{box}/{title}")
        idx.trim(max_df)
        return idx