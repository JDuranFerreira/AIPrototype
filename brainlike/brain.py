"""The arithmetic region: specialist modules, memory, rules and sleep.

With sections=True (the default for the brain you teach) every operation has
its own section: addition, subtraction and multiplication. Only the addition
section ever learns or answers addition, and so on, so knowledge never mixes.
With sections=False a learned router decides instead (used in the experiment
in train.py).

Awake:  known problem -> answer straight from memory (almost no compute).
        new problem   -> the router wakes ONE module, which guesses. After
                         each "no" it learns from the mistake and guesses
                         again, until the teacher says "yes". The answer is
                         then written to memory.
Asleep: memories are replayed to the modules (like the hippocampus teaching
        the cortex). Every module is tested on each memory, the best one
        practises it, and the router learns to send that kind of problem
        there. That competition is what makes modules specialise.
"""
import json
from pathlib import Path

import numpy as np

from . import compose, monitor, rules, task
from .parts import Module, Router


SECTIONS = ["addition", "subtraction", "multiplication"]      # one per operator in task.OPS


class Brain:
    def __init__(self, n_modules=4, n_hidden=24, seed=0, lr=0.05, sections=False,
                 prune=0.0, prune_by="use", router_day=0.0, decay=0.0, margin=1.0, hidden_per_op=None):
        self.rng = np.random.default_rng(seed)
        self.lr = lr
        self.sections = sections
        self.prune = prune              # share of the quietest connections cut each night (0 = never)
        self.prune_by = "use"          # what makes a connection "quiet": what it carries, or its size
        self.router_day = router_day    # how much the router learns from awake outcomes (0 = only in sleep)
        self.decay = decay              # unused weights go quiet, so pruning has something to cut
        self.margin = margin            # how hard a wrong answer is pushed away
        if sections:
            n_modules = len(task.OPS)
        # a brain can give more tissue to the work that is hard (multiplication needs it): the
        # sections then have different sizes instead of all being the same
        sizes = ([int(s) for s in hidden_per_op] if sections and hidden_per_op
                 else [n_hidden] * n_modules)
        self.router = Router(task.INPUT_SIZE, n_modules, self.rng)
        self.modules = [Module(task.INPUT_SIZE, sizes[i % len(sizes)], task.N_ANSWERS, self.rng)
                        for i in range(n_modules)]
        self.memory = {}
        self.rules = {}           # "n/n = 1" -> {lhs, rhs, taught, examples} or {..., rejected}
        self.solving = {}         # missing numbers: "a+?=c" -> "c-a" (see equations.py)
        self.equation_examples = []   # [shape, known, total, answer] the teacher answered

    # ---- size ---------------------------------------------------------------
    @property
    def uses_router(self):
        return len(self.modules) > 1 and not self.sections

    @property
    def total_params(self):
        return (self.router.n_params if self.uses_router else 0) + sum(m.n_params for m in self.modules)

    @property
    def active_params(self):
        """Weights actually used to answer one new problem."""
        return (self.router.n_params if self.uses_router else 0) + self.modules[0].n_params

    @property
    def active_connections(self):
        """Connections actually used to answer one new problem, after pruning: this is the work."""
        return (self.router.connected() if self.uses_router else 0) + self.modules[0].n_connected

    def section_name(self, k):
        return SECTIONS[k] if self.sections else f"module {k}"

    # ---- awake --------------------------------------------------------------
    def first_guess(self, problem):
        """What the brain would say first, without memory or learning."""
        x = task.encode(problem)
        k = self._route(x)
        return task.to_answer(int(self.modules[k].guess_probs(x).argmax())), k

    def _route(self, x):
        if self.sections:          # the operator symbol decides: + always goes to addition
            return int(x[2 * task.N_DIGITS:].argmax())
        return self.router.choose(x) if len(self.modules) > 1 else 0

    def next_guess(self, problem, mistakes=()):
        """The module's best guess that isn't a known mistake."""
        x = task.encode(problem)
        k = self._route(x)
        p = self.modules[k].guess_probs(x)
        p[[task.to_index(m) for m in mistakes]] = -1   # never repeat a known mistake
        idx = int(p.argmax())
        return {"answer": task.to_answer(idx), "module": k, "confidence": float(p[idx])}

    def feedback(self, problem, guess, correct, mistakes=()):
        """The teacher said yes or no to `guess`: learn from it. On yes, the
        answer and the mistakes made on the way are written to memory."""
        x = task.encode(problem)
        k = self._route(x)
        self.modules[k].learn(x, task.to_index(guess), correct, self.lr,
                              decay=self.decay, margin=self.margin)
        if self.router_day and self.uses_router:
            self.router.reinforce(x, k, self.lr * self.router_day, good=correct)
        if correct:
            self.memory[problem] = {"answer": guess, "tries": len(mistakes) + 1,
                                    "mistakes": list(mistakes), "module": k}

    def recall(self, problem):
        """Only what it KNOWS about a single-digit fact: memory or a rule. No guessing."""
        if problem in self.memory:
            return self.memory[problem]["answer"], {"source": "memory"}
        by_rule = rules.apply_to(self, problem)
        if by_rule is not None and by_rule[0].denominator == 1:
            return int(by_rule[0]), {"source": "rule", "rule": by_rule[1]}
        return None

    def recall_or_guess(self, problem):
        """One single-digit fact: from memory if taught, then a rule it trusts
        (7*0 -> n*0 = 0), else the module's first guess."""
        if problem in self.memory:
            return self.memory[problem]["answer"], {"source": "memory"}
        by_rule = rules.apply_to(self, problem)
        if by_rule is not None:
            return int(by_rule[0]), {"source": "rule", "rule": by_rule[1]}
        g = self.next_guess(problem)
        ruled_out = []
        while len(ruled_out) < 40:              # number sense throws out guesses that can't be right
            s = monitor.sense(problem, g["answer"])
            if not s or s["ok"]:
                break
            ruled_out.append(g["answer"])
            g = self.next_guess(problem, ruled_out)
        return g["answer"], {"source": "module", "module": g["module"], "confidence": g["confidence"]}

    def work_out(self, problem):
        """A big problem (10*10, 1+1+1, 7/2): break it into single-digit facts.
        Returns the exact answer (a Fraction) and the facts used, each marked
        memory or module."""
        worker = compose.Worker(self.recall_or_guess, rules.active(self), recall=self.recall)
        answer = worker.run(problem)
        return answer, list(worker.steps.values())

    def remember(self, problem, answer, mistakes=(), free=False):
        """Store something the teacher confirmed that the modules don't learn
        directly: a big problem (answer kept exact, like '7/2'), or with
        free=True any question at all ('capital of France' -> 'Paris')."""
        answer = str(answer) if free else compose.fmt(compose.to_value(answer))
        self.memory[problem] = {"answer": answer, "tries": len(mistakes) + 1,
                                "mistakes": [str(m) for m in mistakes], "module": None}
        if free:
            self.memory[problem]["free"] = True

    def solve(self, problem, checker=task.check, learn=True, on_try=None):
        problem = task.normalize(problem)
        if problem in self.memory:
            fact = self.memory[problem]
            if on_try:
                on_try(1, fact["answer"], True, "memory")
            return {"answer": fact["answer"], "tries": 1, "source": "memory",
                    "module": fact["module"], "mistakes": []}

        mistakes = []
        while True:
            g = self.next_guess(problem, mistakes)
            guess, k = g["answer"], g["module"]
            ok = checker(problem, guess)
            if on_try:
                on_try(len(mistakes) + 1, guess, ok, f"module {k}")
            if learn:
                self.feedback(problem, guess, ok, mistakes)
            if ok:
                break
            mistakes.append(guess)
        return {"answer": guess, "tries": len(mistakes) + 1, "source": f"module {k}",
                "module": k, "mistakes": mistakes}

    # ---- asleep -------------------------------------------------------------
    def sleep(self, rounds=20, balance=0.5):
        """Replay memories so modules learn general rules, not just facts.

        balance > 0 gives a small handicap to modules that are already taking
        many memories, so one module can't grab everything.

        Pruning happens here, at the end of the night: the weakest connections of
        the modules that practised are cut (prune=0.1 cuts a tenth each night),
        which is what keeps the brain small without losing what it learned.
        """
        if not self.memory:
            return
        items = [(p, f) for p, f in self.memory.items() if f["module"] is not None]   # single-digit facts
        n = len(self.modules)
        for _ in range(rounds):
            self.rng.shuffle(items)
            load = np.zeros(n)
            for problem, fact in items:
                x = task.encode(problem)
                idx = task.to_index(fact["answer"])
                k = 0
                if self.sections:
                    k = self._route(x)     # each section only replays its own operation
                elif n > 1:
                    # practise in the module the router really uses, so what is
                    # learned is found again when awake...
                    k = self.router.choose(x)
                    # ...but nudge the router toward whichever module is best at it
                    skill = np.array([m.guess_probs(x)[idx] for m in self.modules])
                    share = load / max(load.sum(), 1)
                    best = int((skill - balance * share).argmax())
                    load[best] += 1
                    self.router.learn(x, best, self.lr)
                self.modules[k].learn(x, idx, True, self.lr,
                                      decay=self.decay, margin=self.margin)
                fact["module"] = k
        for m in self.modules:                     # the night's pruning
            m.prune(self.prune, self.prune_by)

    # ---- persistence --------------------------------------------------------
    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        weights = {"router_W": self.router.W, "router_b": self.router.b}
        for i, m in enumerate(self.modules):
            weights.update(m.state(f"m{i}_"))
        np.savez(folder / "weights.npz", **weights)
        (folder / "memory.json").write_text(json.dumps(self.memory, indent=1), encoding="utf-8")
        (folder / "rules.json").write_text(json.dumps(self.rules, indent=1), encoding="utf-8")
        (folder / "solving.json").write_text(json.dumps({"rules": self.solving, "examples": self.equation_examples},
                                                        indent=1), encoding="utf-8")
        meta = {"n_modules": len(self.modules), "n_hidden": self.modules[0].b1.size, "lr": self.lr,
                "sections": self.sections}
        (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    @classmethod
    def load(cls, folder):
        folder = Path(folder)
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        brain = cls(meta["n_modules"], meta["n_hidden"], lr=meta["lr"], sections=meta.get("sections", False))
        data = np.load(folder / "weights.npz")
        brain.router.W, brain.router.b = data["router_W"], data["router_b"]
        for i, m in enumerate(brain.modules):
            m.load(data, f"m{i}_")
        brain.memory = json.loads((folder / "memory.json").read_text(encoding="utf-8"))
        if (folder / "rules.json").exists():
            brain.rules = json.loads((folder / "rules.json").read_text(encoding="utf-8"))
        if (folder / "solving.json").exists():
            solving = json.loads((folder / "solving.json").read_text(encoding="utf-8"))
            brain.solving, brain.equation_examples = solving["rules"], solving["examples"]
        return brain
