"""The whole brain, in regions that never mix their knowledge. The partition is
by FUNCTION, the way the brain is (not by subject or by where the data came from):

  language    words, word meanings, sentence frames, grammar, word relations,
              reading stories, learned phrases       -> brain_state/language/
  knowledge   facts about the world, from scenes or told (one region, two sources)
                                                     -> brain_state/knowledge/
  memory      the stories it lived through, replayed in sleep -> brain_state/memory/
  arithmetic  numbers only: single-digit facts in three sections (addition,
              subtraction, multiplication), bigger problems it has solved,
              rules, and the written methods        -> brain_state/arithmetic/
  prefrontal  the planner and working memory                        -> prefrontal/
  coordination the TOOLS (worked procedures: groups, percent, common factors, ...),
              which of them it was taught, where each may be used (cue words),
              how well each pays off (rewards), and which way of answering
              (the strategy)                                        -> coordination/
  monitor     confidence, number sense and doubts (nothing stored: it watches
              the other regions)

The report card (levels, subjects, exams) is bookkeeping, NOT a region -> brain_state/report/
"""
import json
import re
import shutil
from pathlib import Path

from . import compose, monitor, rules, task
from .brain import SECTIONS, Brain
from .english import English
from .index import Index
from .reading import Reading
from .language import Language, key
from .reader import Reader
from .planner import CAPACITY, Doubts, WorkingMemory
from .coordination import Coordination, TOOLS, ARITH_TOOLS
from .strategy import Strategy


class Knowledge:
    """The knowledge region: facts about the world, from one of two sources —
    'facts' are told directly ("capital of france" -> "Paris"); 'scene' is the
    little semantic network learned from scenes and stories (a puppy is a young dog).
    Both live in the same region."""

    def __init__(self, facts=None, scene=None, units=None):
        self.facts = facts or {}          # "capital of france" -> "Paris"
        self.scene = scene                # WorldKnowledge, shared with the reading engine
        self.units = units or []          # unit facts told in P5 ("1 kg is 1000 g"), shared with the frames
        self.changed = 0                  # how many times a fact was stored or dropped: the index watches this

    def get(self, question):
        return self.facts.get(key(question))

    def remember(self, question, answer):
        self.facts[key(question)] = str(answer).strip()
        self.changed += 1

    def forget(self, question):
        forgot = self.facts.pop(key(question), None) is not None
        self.changed += forgot
        return forgot
    def count(self):
        scene = len(self.scene.isa) + sum(len(p) for p in self.scene.props.values()) if self.scene else 0
        return len(self.facts) + scene

    def state(self):
        return {"facts": self.facts, "units": self.units,
                "scene": self.scene.state() if self.scene else {"isa": {}, "props": {}, "young": {}}}


class Memory:
    """The memory region: the stories it lived through, replayed in sleep. The
    reading engine fills it; here it is a region of its own."""

    def __init__(self, episodes=None, seen_episodes=None):
        self.episodes = episodes if episodes is not None else {}
        self.seen_episodes = seen_episodes if seen_episodes is not None else {}

    def count(self):
        return sum(len(box) for box in self.episodes.values())

    def state(self):
        return {"episodes": self.episodes, "seen_episodes": self.seen_episodes}


LEARNS = {
    "addition": "single-digit + facts (0+0 … 9+9), by trial and error",
    "subtraction": "single-digit − facts (0-0 … 9-9), by trial and error",
    "multiplication": "single-digit × facts (0*0 … 9*9), by trial and error",
}
METHODS = ["column addition with carry", "column subtraction with borrow", "long multiplication",
           "long division", "exact fractions and decimals"]


DIVISIONS = [f"{q * d}/{d}" for d in range(1, 10) for q in range(10)]     # 0/1 ... 81/9: every single-digit answer


def division_section(a):
    """Division has no weights of its own: it is long division, built from the
    multiplication table (how many times does 8 fit?) and subtraction (what is
    left?). Its quality is measured on all 90 single-digit divisions."""
    right = sure = 0
    for p in DIVISIONS:
        answer, steps = a.work_out(p)
        right += answer == compose.true_value(p)
        sure += all(s["source"] != "module" for s in steps)
    div_rules = [name for name, r in a.rules.items() if not r.get("rejected") and "/" in r["lhs"]]
    solved = sum(1 for p, f in a.memory.items() if "/" in p)
    return {"name": "division", "built_from": ["multiplication", "subtraction"], "method": "long division",
            "learns": "nothing directly: it uses the multiplication table and subtraction",
            "solved": solved, "rules": div_rules, "weights": 0,
            "exam": {"right": right, "of": len(DIVISIONS), "all_known": sure}}


def new_arithmetic():
    return Brain(n_hidden=32, sections=True)


class Mind:
    """The whole brain, in regions that never mix their knowledge:

      language     words, word meanings, sentence frames, grammar, reading a
                   story, learned phrases                -> language/
      knowledge    facts about the world, from scenes or told  -> knowledge/
      memory       stories it lived through (replayed in sleep)  -> memory/
      arithmetic   numbers: facts, rules and written methods  -> arithmetic/
      prefrontal   plans and working memory                   -> prefrontal/
      coordination the tools, where each may be used, how well
                   each pays off, and which way to answer
                   (the strategy)                             -> coordination/
      monitor      confidence, number sense and doubts (nothing stored)

    The report card (levels, exams) is bookkeeping, not a region  -> report/
    """

    def __init__(self, arithmetic=None, knowledge=None, language=None, memory=None, working=None, strategy=None,
                 report=None, usage=None, english=None, reading=None, school=None, kindergarten=None,
                 coordination=None, doubts=None, mode=None):
        self.arithmetic = arithmetic or new_arithmetic()
        self.knowledge = knowledge or Knowledge()
        # the LANGUAGE region: phrases/patterns/reader (Language) + grammar (English) + the reading engine
        self.language = language or Language()
        self.language.english = english if english is not None else getattr(self.language, "english", None) or English()
        self.language.reading = (reading if reading is not None else
                                 (kindergarten if kindergarten is not None else
                                  getattr(self.language, "reading", None) or Reading()))
        self.memory = memory or Memory()
        self.working = working if working is not None else WorkingMemory()   # prefrontal
        self.coordination = coordination if coordination is not None else Coordination()  # tools + strategy
        if strategy is not None:           # the strategy chooser lives in the coordination region now
            self.coordination.strategy = strategy
        self.doubts = doubts if doubts is not None else Doubts()     # prefrontal: doubt and checking
        self.mode = mode if mode in ("normal", "training") else "normal"   # normal: it answers, training: it learns
        self._index = None            # the cue index, built on first use
        self._index_dirty = False
        self._index_stamp = 0         # the knowledge change count the index was built from
        self.index_hits = 0           # how many times it found a memory by its cue words alone
        self.report = report if report is not None else (school or {"level": None, "report": []})
        self.usage = usage or {}          # how questions got answered: {"memory": 12, "rule": 3, ...}
        self._bind()

    @property
    def strategy(self):
        """The strategy chooser: a component of the coordination region (the old name kept working)."""
        return self.coordination.strategy

    def _bind(self):
        """The reading engine owns the word learner, the scene facts, the memories and the unit
        facts; the knowledge and memory regions share the very same stores, so nothing is copied.
        The engine's taught tools are handed over to the coordination region (they are its own)."""
        self.knowledge.scene = self.language.reading.know
        self.memory.episodes = self.language.reading.episodes
        self.memory.seen_episodes = self.language.reading.seen_episodes
        self.knowledge.units = self.language.reading.frames.units
        self.language.reading.frames.bind(self.coordination)
        self.language.reading.doubts = self.doubts

    def install_reading(self, state):
        """Swap in a reading engine built from a saved Reading.state() dict (a dev tool:
        load a bare engine file into a fresh Mind), then re-share its stores so the
        knowledge and memory regions keep pointing at the new engine's stores."""
        from .reading import Reading
        self.language.reading = Reading(state)
        self._bind()
        return self

    # ---- the old names, kept so older code and benchmarks still work ----------
    @property
    def english(self):
        return self.language.english

    @property
    def kindergarten(self):
        return self.language.reading

    @property
    def school(self):
        return self.report

    # ---- persistence --------------------------------------------------------
    @classmethod
    def load(cls, state, language_options=None):
        state = Path(state)
        opts = language_options or {}
        if (state / "meta.json").exists():            # the old single-region layout
            mind = cls.migrate(state, opts)
            mind.save(state)
            return mind
        arithmetic = Brain.load(state / "arithmetic") if (state / "arithmetic" / "meta.json").exists() else None
        # LANGUAGE: phrases/patterns, grammar, and the reading engine (new files, else the old layout)
        lang = _read(state / "language" / "language.json", None)
        if lang is None:
            lang = _read(state / "language" / "phrases.json", {})
        english = _read(state / "language" / "english.json", None)
        if english is None:
            english = _read(state / "english" / "english.json", {})
        reading = _read(state / "language" / "reading.json", None)
        # KNOWLEDGE and MEMORY (new files, else the old kindergarten layout)
        knowledge = _read(state / "knowledge" / "knowledge.json", None)
        memory = _read(state / "memory" / "memory.json", None)
        old_kg = _read(state / "kindergarten" / "kindergarten.json", None)
        if reading is None and old_kg is not None:
            reading = {k: v for k, v in old_kg.items() if k not in ("knowledge", "episodes", "seen_episodes")}
        if knowledge is None:
            scene = old_kg.get("knowledge") if old_kg else None
            knowledge = {"facts": _read(state / "knowledge" / "facts.json", {}), "scene": scene}
        if memory is None:
            memory = {"episodes": (old_kg or {}).get("episodes", {}),
                      "seen_episodes": (old_kg or {}).get("seen_episodes", {})}
        report = _read(state / "report" / "report_card.json", None)
        if report is None:
            report = _read(state / "school" / "report_card.json", None)
        coord_data = _read(state / "coordination" / "coordination.json", None)
        if coord_data is None:            # old layout: the strategy file (the tools come from reading.json)
            coord_data = {"stats": {}, "strategy": _read(state / "strategy" / "stats.json", {})}
        coordination = Coordination(coord_data)
        engine_state = {**(reading or {}), "knowledge": knowledge.get("scene"),
                        "episodes": memory.get("episodes", {}), "seen_episodes": memory.get("seen_episodes", {})}
        if knowledge.get("units") is not None:
            engine_state["units"] = knowledge["units"]           # the region's copy wins (both hold the same list)
        mind = cls(arithmetic, Knowledge(knowledge.get("facts"), units=knowledge.get("units")),
                   Language(lang.get("phrases"), lang.get("patterns"), reader=Reader.load(state / "language"), **opts),
                   Memory(memory.get("episodes"), memory.get("seen_episodes")),
                   WorkingMemory(_read(state / "prefrontal" / "working_memory.json", {})),
                   None,                   # the strategy comes with the coordination region
                   report,
                   _read(state / "usage.json", {}),
                   English(english),
                   Reading(engine_state),
                   coordination=coordination,
                   doubts=Doubts(_read(state / "prefrontal" / "doubts.json", {})),
                   mode=_read(state / "mode.json", "normal"))
        # the cue index, if it was saved with the brain: same facts, so the same index. If the file is
        # missing or shorter than the facts (an older copy), the index rebuilds from the facts on first
        # use — and a miss always falls back to the exact search, so a stale file cannot lose a memory.
        saved = _read(state / "index" / "index.json", None)
        mind._index = Index.load(saved) if saved else None
        if mind._index is None or len(mind._index) < len(mind.knowledge.facts):
            mind._index = None
        else:
            mind._index_stamp = mind.knowledge.changed
        return mind
    # ---- the index: cue words that say where an answer lives ----------------------------------------
    # Built from what is actually stored (never hand written), kept fresh when facts change, and saved
    # with the brain. It only ever ADDS a way of finding something: a miss falls back to the old exact
    # search, so it can never lose a fact.

    @property
    def index(self):
        """Cue word -> the places that word can be found. Rebuilt when the facts change, so no
        caller has to remember to tell it."""
        if self._index is None or self._index_dirty or self._index_stamp != self.knowledge.changed:
            self._index = Index.build({"facts": self.knowledge.facts},
                                      {"facts": getattr(self.arithmetic, "memory", {})},
                                      {"episodes": self.memory.episodes},
                                      episodes=False)   # story titles are whole sentences; nothing
            self._index_dirty = False                   # looks them up by cue words yet
            self._index_stamp = self.knowledge.changed
        return self._index

    def reindex(self):
        """Force a rebuild on next use (for stores the index cannot watch by itself)."""
        self._index_dirty = True

    def recall_fact(self, question):
        """What it knows about this, if anything: the exact key first, then the index.

        -> (answer, how), where how is "exact", "index" or None. The index is what lets a question
        worded differently still find the memory, and it says which region holds it.
        """
        hit = self.knowledge.get(question)
        if hit is not None:
            return hit, "exact"
        for region, k in self.index.find(question):
            if region == "knowledge":
                found = self.knowledge.facts.get(k)
                if found is not None:
                    self.index_hits += 1
                    return found, "index"
        return None, None

    def where_is(self, question, max_extra=3):
        """Where an answer like this is stored -> [(region, key)], without waking a region to say so."""
        return self.index.find(question, max_extra)



    def save(self, state):
        state = Path(state)
        self.arithmetic.save(state / "arithmetic")
        rd = dict(self.language.reading.state())
        scene = rd.pop("knowledge")                                   # -> the knowledge region
        episodes, seen = rd.pop("episodes"), rd.pop("seen_episodes")   # -> the memory region
        _write(state / "language" / "language.json",
               {"phrases": self.language.phrases, "patterns": self.language.patterns})
        _write(state / "language" / "english.json", self.language.english.state())
        _write(state / "language" / "reading.json", rd, indent=None)
        _write(state / "knowledge" / "knowledge.json",
               {"facts": self.knowledge.facts, "units": self.knowledge.units, "scene": scene}, indent=None)
        _write(state / "memory" / "memory.json", {"episodes": episodes, "seen_episodes": seen}, indent=None)
        _write(state / "prefrontal" / "working_memory.json", self.working.state())
        _write(state / "prefrontal" / "doubts.json", self.doubts.state())
        _write(state / "coordination" / "coordination.json", self.coordination.state(), indent=None)
        _write(state / "mode.json", self.mode)
        _write(state / "report" / "report_card.json", self.report)
        _write(state / "index" / "index.json", self.index.state(), indent=None)   # where things live
        self.save_usage(state)

    def save_conversation(self, state):
        """Normal chat: keep the conversation's working memory (so "now add 5 to that" still works)
        without writing every learned store again."""
        _write(Path(state) / "prefrontal" / "working_memory.json", self.working.state())

    def save_usage(self, state):
        _write(Path(state) / "usage.json", self.usage)

    def count(self, how):
        self.usage[how] = self.usage.get(how, 0) + 1

    @classmethod
    def migrate(cls, state, opts):
        """Split an old brain into regions. Math stays in arithmetic (retrained
        into one section per operation, from its own memories), other facts
        move to knowledge, and the old files are kept in _before_regions/."""
        old = Brain.load(state)
        arithmetic = new_arithmetic()
        arithmetic.rules = old.rules
        knowledge = Knowledge()
        for problem, fact in old.memory.items():
            if not fact.get("free"):
                arithmetic.memory[problem] = dict(fact)
                continue
            m = re.match(r"^rules?\s+(.+)$", problem)       # "rules n*(-1)" = "-n" was a rule all along
            if m and rules.is_rule(m.group(1)):
                try:
                    rules.add(arithmetic, m.group(1), str(fact["answer"]))
                    continue
                except ValueError:
                    pass
            knowledge.remember(problem, fact["answer"])
        for problem, fact in arithmetic.memory.items():
            if fact["module"] is not None:
                fact["module"] = arithmetic._route(task.encode(problem))
        arithmetic.sleep(rounds=300)                  # the new sections learn from the old memories
        backup = state / "_before_regions"
        backup.mkdir(exist_ok=True)
        for name in ("meta.json", "weights.npz", "memory.json", "rules.json"):
            if (state / name).exists():
                shutil.move(str(state / name), str(backup / name))
        return cls(arithmetic, knowledge, Language(**opts))

    # ---- overview -----------------------------------------------------------
    def report_card(self):
        """The report card (levels, subjects, exams): bookkeeping, NOT a region."""
        return {"name": "report card", **self.report, "what": "levels, subjects and exam results"}

    def regions(self):
        a = self.arithmetic
        per_section = [0] * len(a.modules)
        big = 0
        for fact in a.memory.values():
            if fact["module"] is None:
                big += 1
            else:
                per_section[fact["module"]] += 1
        sections = [{"name": SECTIONS[i] if a.sections else f"module {i}", "facts": n, "of": 100,
                     "op": task.OPS[i] if a.sections else None,
                     "learns": LEARNS.get(SECTIONS[i], "") if a.sections else "",
                     "weights": a.modules[i].n_params} for i, n in enumerate(per_section)]
        active = rules.active(a)
        explaining = sum(compose.explains(lhs, rhs) for lhs, rhs, _ in active)
        return [
            {"name": "language", **self.language.summary(), "english": self.language.english.summary(),
             "reading": self.language.reading.summary(),
             "what": "words, grammar, sentence frames, reading stories, learned phrases"},
            {"name": "knowledge", "facts": len(self.knowledge.facts),
             "scene_facts": self.knowledge.count() - len(self.knowledge.facts),
             "unit_facts": len(self.knowledge.units),
             "what": "facts about the world, from scenes or told"},
            {"name": "memory", "episodes": self.memory.count(), "stages": len(self.memory.episodes),
             "what": "the stories it lived through, replayed in sleep"},
            {"name": "arithmetic", "sections": sections, "built_sections": [division_section(a)], "bigger_problems": big,
             "rules": len(active), "shortcut_rules": len(active) - explaining, "explaining_rules": explaining,
             "methods": METHODS, "what": "numbers: facts, rules and written methods"},
            {"name": "prefrontal", "working_memory": self.working.values, "capacity": CAPACITY,
             "doubt": self.doubts.summary(),
             "what": "plans, working memory, and doubt: it asks for a second opinion and checks its "
                     "working with a tool before saying it understood"},
            {"name": "coordination",
             "tools": [{"op": op, "does": does, "taught": op in self.coordination.rules}
                       for op, does in TOOLS.items()],
             "arith_tools": [{"op": op, "does": what, "taught": op in self.coordination.arithmetic}
                             for op, what in ARITH_TOOLS.items()],
             "choices": self.strategy.summary(),
             "rewards": self.coordination.summary(),
             "learned_cues": self.coordination.learned_cues(),
             "what": "the tools (worked procedures) and where to use them; which way to answer, "
                     "learned from rewards"},
            {"name": "monitor", "doubts": monitor.doubts(a), "weber": f"±{int(monitor.WEBER * 100)}%",
             "what": "confidence, number sense and doubts"},
        ]


def _read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(path, data, indent=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")        # write beside it and move it in one step, so a reader
    tmp.write_text(json.dumps(data, indent=indent, ensure_ascii=False, separators=None if indent else (",", ":")),
                   encoding="utf-8")
    tmp.replace(path)
