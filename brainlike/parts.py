"""Building blocks: small specialist modules ("brain regions") and a router
that decides which one to wake up."""
import numpy as np


def softmax(z):
    e = np.exp(z - z.max())
    return e / e.sum()


class Module:
    """A tiny specialist network. It only runs, and only learns, when the
    router picks it; the rest of the brain stays idle.

    Connections can be PRUNED (prune()): the weakest ones are cut during sleep
    and frozen there, the way a real brain drops the synapses it does not use.
    That makes the brain smaller in memory and in the work it does per problem,
    and it costs nothing in accuracy if what is cut really was unused.
    """

    def __init__(self, n_in, n_hidden, n_out, rng):
        self.W1 = rng.normal(0, np.sqrt(2 / n_in), (n_in, n_hidden))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0, np.sqrt(1 / n_hidden), (n_hidden, n_out))
        self.b2 = np.zeros(n_out)
        self.cut = np.zeros_like(self.W1, dtype=bool)        # connections cut (never grow back)
        self.cut2 = np.zeros_like(self.W2, dtype=bool)
        self.cuts = 0                                         # how many have been cut so far
        self.use1 = np.zeros_like(self.W1)                    # how much signal each connection carries
        self.use2 = np.zeros_like(self.W2)

    @property
    def n_params(self):
        return self.W1.size + self.b1.size + self.W2.size + self.b2.size

    @property
    def n_connected(self):
        """Connections still alive: what this module really costs to run."""
        return (int((~self.cut).sum()) + int((~self.cut2).sum()) + self.b1.size + self.b2.size)

    def _forward(self, x):
        h = np.maximum(0, x @ self.W1 + self.b1)
        return h, softmax(h @ self.W2 + self.b2)

    def guess_probs(self, x):
        return self._forward(x)[1]

    def learn(self, x, answer_index, correct, lr, spread=1.0, decay=0.0, margin=1.0):
        """Correct -> make that answer (and its neighbours on the number line)
        more likely. Wrong -> make that answer less likely.

        spread: how much neighbours share the credit, like number neurons in
        real brains that also fire a little for nearby numbers. Without it,
        7 and 8 look unrelated and the brain can't find rules.
        margin: push a wrong answer further away than just "less likely" (1.0 = old behaviour).
        decay: pull the unused weights down a little each time, so what the brain
        does not use slowly goes quiet and can be pruned.
        """
        h, p = self._forward(x)
        if correct:
            near = np.exp(-0.5 * ((np.arange(p.size) - answer_index) / spread) ** 2)
            g = p - near / near.sum()                 # d(cross-entropy)/dz
        else:
            pw = min(p[answer_index], 0.99)
            g = -p.copy()
            g[answer_index] += 1
            g *= (margin * pw / (1 - pw))             # d(-log(1-p))/dz
        gh = (self.W2 @ g) * (h > 0)
        if decay:
            self.W1 *= 1 - lr * decay
            self.W2 *= 1 - lr * decay
        self.W2 -= lr * np.outer(h, g)
        self.b2 -= lr * g
        self.W1 -= lr * np.outer(x, gh)
        self.b1 -= lr * gh
        self.use1 = 0.9 * self.use1 + 0.1 * np.abs(np.outer(x, gh))   # how much signal each one carries
        self.use2 = 0.9 * self.use2 + 0.1 * np.abs(np.outer(h, g))
        if self.cut.any():                             # cut connections stay cut
            self.W1[self.cut] = 0.0
        if self.cut2.any():
            self.W2[self.cut2] = 0.0

    def prune(self, fraction=0.02, by="use"):
        """Sleep-time pruning: cut the connections that carry the least signal.

        by="use"  - the ones the module never really uses (like real synapses that go quiet);
        by="size" - the ones with the smallest weight.
        Only matrix entries are cut, never the biases, so a module can still answer.
        Returns how many went.
        """
        if fraction <= 0:
            return 0
        gone = 0
        for W, mask, use in ((self.W1, self.cut, self.use1), (self.W2, self.cut2, self.use2)):
            alive = ~mask
            n_alive = int(alive.sum())
            n_cut = min(int(n_alive * fraction), n_alive - 1 if n_alive > 1 else 0)
            if n_cut <= 0:
                continue
            score = (use if by == "use" else np.abs(W)).ravel()
            score = np.where(alive.ravel(), score, np.inf)         # flat: one list of every connection
            for idx in np.argpartition(score, n_cut - 1)[:n_cut]:
                mask.flat[idx] = True
                W.flat[idx] = 0.0
            gone += n_cut
        self.cuts += gone
        return gone

    def state(self, prefix):
        return {f"{prefix}{k}": getattr(self, k) for k in ("W1", "b1", "W2", "b2", "cut", "cut2")}

    def load(self, data, prefix):
        for k in ("W1", "b1", "W2", "b2"):
            setattr(self, k, data[f"{prefix}{k}"])
        for k in ("cut", "cut2"):                    # brains saved before pruning had no masks
            setattr(self, k, np.zeros_like(getattr(self, k), dtype=bool) if f"{prefix}{k}" not in data
                    else data[f"{prefix}{k}"])


class Router:
    """Looks at the problem and picks one module to handle it."""

    def __init__(self, n_in, n_modules, rng):
        self.W = rng.normal(0, 0.1, (n_in, n_modules))
        self.b = np.zeros(n_modules)

    @property
    def n_params(self):
        return self.W.size + self.b.size

    def probs(self, x):
        return softmax(x @ self.W + self.b)

    def choose(self, x):
        return int(self.probs(x).argmax())

    def learn(self, x, best_module, lr):
        g = self.probs(x)
        g[best_module] -= 1
        self.W -= lr * np.outer(x, g)
        self.b -= lr * g

    def reinforce(self, x, module, lr, good=True):
        """The route itself can be learned while awake: if the module the router woke answered
        well, send this kind of problem there again; if it kept answering wrong, send it elsewhere.
        Small steps - the router must not become the only thing that decides."""
        g = self.probs(x).copy()
        g[module] -= 1 if good else -1
        self.W -= lr * np.outer(x, g)
        self.b -= lr * g

    def connected(self):
        return int((self.W != 0).sum()) + self.b.size
