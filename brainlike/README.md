# brainlike — a tiny brain-inspired learner

Built from scratch in NumPy. No pre-trained model, runs on a CPU in seconds.

## The idea

| Brain | Here |
|---|---|
| Regions specialise (different sectors for different jobs) | 4 small **modules** |
| Only the needed neurons fire | A **router** wakes **one** module per problem |
| Babies learn by trial and error | It guesses until the teacher says **yes**, and learns from every **no** |
| The hippocampus stores what you learned | **Memory**: a known problem is answered without waking any module |
| Sleep turns memories into skills | **Sleep**: memories are replayed so modules learn the *rules* |
| Number neurons also fire for nearby numbers | **Number line**: when the answer is 7, guessing 6 or 8 counts as nearly right |

The teacher (`task.check`) only says right or wrong. It never reveals the answer.

## Run it

```powershell
.\.venv\Scripts\python.exe -m brainlike.train                  # raise a modular and a dense brain, compare them
.\.venv\Scripts\python.exe -m brainlike.demo 1+1 7*8           # ask the saved brain
.\.venv\Scripts\python.exe -m brainlike.demo 1+1 --fresh       # watch a newborn brain try until it gets 2
.\.venv\Scripts\python.exe -m brainlike.primary S2            # the next year of school: secondary 2
.\.venv\Scripts\python.exe -m brainlike.coding               # the code lesson: tools, recipes, programs, exam
python benchmarks\wiring.py                                 # every wiring compared: accuracy and live connections
python benchmarks\wiring.py --only today --seeds 1          # one wiring, one seed (quicker)
python benchmarks\index_gain.py                             # the cue index: how many memories found, and at what cost
```

`train.py` and `demo.py` use `experiment_state/`. The brain you teach in AgenticOS lives in `brain_state/` (see "Regions and sections" below) and is only touched through `serve.py`.

## The school years, and the code lesson

| Year | Topics it adds |
|---|---|
| P1–P6 | numbers to 10 million; equal groups and sharing; money; units; remainders; percent; the area of a square; greatest common factor, least common multiple; speed |
| S1 | negative numbers; simple equations; proportion (the unitary method); averages; circles |
| **S2** | **ratios; simple interest; volume; problems with three steps** |

Each year has its own story kinds (`SchoolTeller.S2`), its own real-problem pool (`REAL["S2"]`), its own exam sets A and B, and a retake after the feedback round. On the brain in `brain_state/`: P1 98.8%, P2 97.6%, P3 96.6%, P4 94.7%, P5 92.9%, P6 94.2%, **S1 95.0%**, **S2 89.1% (AL2, round 1)** — all AL1 except the new year.

The **code lesson** (`brainlike/coding.py`, the Brain tab's **Code** button, or `teach code` in the chat) is a school lesson in the same shape:

1. **Read the request first** (`brainlike/request.py`). Every question is read for what it *wants* before anything is worked out: the kind of answer (`needed` — how many are needed, `each` — in each / per one, `all` — in all, `money`, `left`, or a plain `count`) and the thing it is about (`cars`, `pens`, `red pens`). A taught recipe declares what it answers (`asks`) and what it does **not** count (`not_about`), so it stays silent on "how many boxes are there?" when its program counts the pens inside the boxes. The reply carries `asked`, and when nothing can answer, the brain says what it wanted instead of guessing.
2. **Teach** — each tool (left over, a power, which is bigger, numbers in order, counting on) and each recipe (a word pattern → the program to write) is shown worked examples. A tool or recipe is kept **only if the brain reproduces every single example** with its own procedure; one wrong example and it is discarded.
3. **Use** — the brain answers tool tasks and runs programs (assignments, `if/then/else`, `for/do`, nested up to four levels) and **checks every step by undoing it**. A program that ends in a negative count of things is thrown away: a count cannot be negative, so that is proof it does not understand the question.
4. **Exam** — 24 fresh questions it was never taught (about a third of them traps: the same words as a taught recipe but a different request), each answer still carrying its check.

**Numbers by meaning, not by position.** A recipe's plan can use `{n1} {n2}` (the sentence's numbers in order) **or named roles** — `{boxes}`, or `{gives away|eats|breaks}` for any word that means "some are taken away". The brain works out which number counts which word, so *"There are 14 boxes with 6 pens in each. Raj takes 14 boxes and gives away 10 pens."* now works: the same number appearing twice no longer confuses it.

Result on the real brain: **13/13 recipes and 5/5 tools kept** (up from 6 recipes), 6/6 tasks and 24/24 program steps checked by undoing, and on the exam **58% before the lesson → 88% after (AL2)**, with 7 of the questions it could not do before now taught by the lesson. `benchmarks/recipes_regression.py` is the guard: 200 real world questions through the chat before and after teaching the new recipes — **0 better, 0 worse, 200 unchanged**.

`benchmarks/teach_coding.py` is only the measurement around that lesson (the S1 "each one holds N" family before and after, and the rewards), so the taught material has a single home.

**What it is not:** code is still a small plan language (`plan: total = 9*7; left = total-2; left/5`), not a general interpreter. The request reader knows six kinds of question and the nouns in them; **when the question asks for something no recipe was taught to answer, the brain says so instead of guessing** — and the three exam questions it still gets wrong ("how many people are in one car?", "how many jars are there?", "how many pens cost 15 dollars?") are answered by the *reading* engine, not by a recipe. That is the next thing to fix, and it is a reading problem, not an arithmetic one.

## Results so far (as of 2026-10-01)

Task: single-digit `+ - *` (300 problems). 240 are learned over 10 "days", and 60 are **never shown**. Those 60 test whether it learned rules or only facts. Numbers are averaged over 3 seeds.

| | Right on first try, unseen problems | Weights used per new problem |
|---|---|---|
| Dense (one module, 11.5k weights) | 57% | 11,476 (100%) |
| **Modular (router + 4 × small module)** | **54%** | **2,947 (26%)** |

- **Similar quality with about a quarter of the compute.** That's the main result.
- **Modules sometimes specialise on their own:** in some runs about 75% of multiplication goes to a single module, and nobody told it what `*` means. In other runs the split stays mixed, so this is not reliable yet.
- **What mattered most was how numbers are perceived, not the architecture.** Seeing digits as quantities ("3" = three units) and using number-line credit raised unseen accuracy from **15% to about 60%**.
- **Weak spots:** multiplication (about 20–30% unseen). Results vary between runs (43–63%) because the routing is still unstable. Inside a module, learning still uses ordinary gradient descent.

## The wiring: better connections and a smaller brain (measured 2026-10-05)

`benchmarks/wiring.py` raises every wiring exactly like `train.py` does and changes only the connections, 3 seeds each. "connected" is the work per new problem: how many synapses are actually alive after pruning.

| Wiring | Unseen right, 1st try | + / − / × | Connections awake | Weights total |
|---|---|---|---|---|
| today (router + 4 modules) | 53% ±11 | 70 / 66 / 18% | 2,947 | 11,500 |
| **sections (one per operation)** | **72% ±5** | 93 / 97 / 15% | 2,851 | 8,553 |
| sections, smaller (16/16/16) | 70% ±2 | 94 / 94 / 9% | **1,931** | 5,793 |
| sections, ×-heavy (12/12/60) | 70% ±4 | 93 / 97 / 8% | 1,471 | 9,933 |
| sections, ×-heavy + pruning | 71% ±5 | 92 / 94 / 15% | **1,229** | 9,933 |
| router + pruning 2%/night | 48% ±2 | 64 / 61 / 14% | 2,455 | 11,500 |
| router, router learns while awake | 54% ±10 | 66 / 66 / 21% | 2,947 | 11,500 |
| pruning 10%/night | 21% ±6 | 19 / 31 / 11% | 1,171 | 11,500 |
| pruning + weight decay | 21% ±5 | 24 / 24 / 15% | 2,455 | 11,500 |

What this says, plainly:

- **The connections that helped most were cut apart, not tuned.** Hard sections (the operator decides) beat the learned router by **+19 points** of unseen accuracy *and* need slightly fewer connections — a learned router mixes the operations and pays for it. This is the "routing is unstable" weakness, measured.
- **Pruning is real efficiency at a real cost.** Cutting the 2% of connections that carry the least signal each night (`Module.prune`, `by="use"` — what a synapse actually carries, not how big it is) removes **17–40% of the awake connections for 1–4 points of accuracy**. Cutting 10% a night destroys the brain (72% → 21%): most connections still look alike early on.
- **Weight decay is harmful here** (72% → 21%): the weights it shrinks are the ones carrying the signal.
- **Giving the hard operation more neurons did not help multiplication** (8–15% whether × had 16 or 60 hidden units). Multiplication is not short of neurons; it is a **perception** problem — the same conclusion as "how numbers are perceived mattered most", and still open.
- **Learning the route while awake** (reward-modulated, `Router.reinforce`) is within noise of not doing it: the router's problem is not when it learns.

## The cue index: finding a memory without reading the shelf (measured 2026-10-05)

`index.py` is the hippocampus-style index: for every memory it keeps the cue words that identify it ("capital", "portugal") and which memories each word points at. A question is looked up by the words it shares, not by its exact wording, and the same words are used to *match* (all identifying words must be present, no more than 3 extra, so a near miss cannot drift onto a neighbour). `benchmarks/index_gain.py` re-asks every fact the taught brain stores, in wordings a person would actually use ("what is the capital of Portugal?", "capital of portugal please", words the other way round):

| | Found | Entries opened per lookup | Time |
|---|---|---|---|
| exact wording (the old way) | **34/98 (35%)** | the whole shelf: 334 | — |
| **cue index** | **98/98 (100%)** | **median 1, worst 3** | 0.2 ms / 98 questions |

- **The gain is recall, not only speed:** 64 of the 98 questions the brain could not find at all before, it now finds (and those misses used to wake the reading engine, which answers from a different store).
- **Two things keep the index honest and small.** Common words ("number", "answer") are dropped as *index* cues when they point at more than 32 memories — opening hundreds of places costs more than reading the shelf — but they still count for matching. And the index only ever **adds** a way of finding something: an exact-key search still runs first, so a stale or missing index can cost a lookup but can never lose a fact.
- Entries are stored by number, not by repeating their text under every cue word: **1.4 KB for the told facts** (87 bytes each). Story titles are whole sentences and nothing looks them up by cue words yet, so episodes are not indexed (`episodes=False`).
- The index rebuilds itself when the facts change (`Knowledge.changed` is watched — no caller has to remember), is saved to `brain_state/index/index.json`, and `mind.recall_fact()` / `mind.where_is()` are what `serve.py` uses for "ask" and "teach".

## Regions and sections (as of 2026-10-01)

The brain you teach (`brain_state/`) is split into regions that never mix their knowledge:

| Region | Holds | Folder |
|---|---|---|
| **arithmetic** | single-digit facts in 3 **sections** (addition, subtraction, multiplication), bigger problems, rules, written methods | `brain_state/arithmetic/` |
| **knowledge** | facts about the world, exactly as taught | `brain_state/knowledge/` |
| **language** | phrases and phrase patterns learned from the teacher; a local model (`qwen3:8b`, Ollama) suggests meanings for new phrasings, always confirmed by the teacher, and never calculates | `brain_state/language/` |

The operator symbol decides the section, so only the addition section ever learns addition (`Brain(sections=True)`).

Same size, same schedule, average of 3 seeds, unseen single-digit facts:

| Brain | Unseen right | + | − | × |
|---|---|---|---|---|
| dense (1 module) | 57–60% | 76–83% | 72–75% | 17–19% |
| learned router (4 modules) | 54–59% | 69–72% | 72–75% | 15–24% |
| **sections (1 per operation)** | **73–74%** | **100%** | **93–94%** | 19–22% |
| sections + rule `a*b = a*(b-1)+a` | **95–98%** | 100% | 88–96% | **100%** |

Multiplication is hard to *guess*, and more sleep doesn't fix it. A rule that **explains** it (`a*b = a*(b-1)+a`) lets the brain work out facts it was never taught, from addition, which it has mastered: solving by understanding. Rules whose right side uses the same operation are used this way (`compose.explains`). Other rules are one-step shortcuts.

## Prefrontal, monitor and strategy (as of 2026-10-01)

| Region | Brain part | What it does |
|---|---|---|
| **prefrontal** | prefrontal cortex | Turns problems with several steps into a **plan** (`plan: apples = 3*4; left = apples-2; left/5`), runs it step by step through the arithmetic region, and keeps results in **working memory** (7 slots, `last` = previous answer) so follow-ups like "now add 5 to that" work. The language region writes plans from sentences. |
| **monitor** | anterior cingulate + parietal number sense | **Number sense** perceives every number within ±20% and carries the fuzz through the calculation. An answer outside that range is certainly wrong (7*8 can't be 15), so impossible guesses are thrown out before the teacher sees them, and the section learns from that. It also reports **confidence** (the weakest step) and **doubts** (memories that contradict rules or number sense). |
| **strategy** | basal ganglia | For a fact it doesn't know: guess (cheap, maybe wrong) or work it out with a rule (more steps, reliable)? The teacher's ✓/✗ is the reward. A right answer is worth 1 and every step costs 0.02, with 10% exploring. With `a*b = a*(b-1)+a` taught, it switched to working facts out after one wrong guess and got 9/9 right. |

**Checking by undoing** (in the monitor): 2+6 = 8 is checked with 8-6 = 2, 9-4 = 5 with 5+4 = 9, 56/8 = 7 with 7*8 = 56, and a*b by taking b away a times. It only uses facts the brain knows, never the fact being checked or its flipped twin, so one section checks another. It raised self-checked unseen facts from 77% to 83% (subtraction 21/23 to 23/23).

Number sense alone lifted unseen single-digit facts from 69% to 78% with no teacher (multiplication 1/16 to 6/16).

## Next experiments

1. Stabilise routing so specialisation is clean and repeatable.
2. Give the teacher richer feedback ("too big" / "too small") so tries drop from about 13 to about 7.
3. Replace the gradient descent inside modules with a local, backprop-free rule.
4. Add a module that uses tools (for example repeated addition for `*`), like a child counting on fingers.
5. Keep inactive modules on disk so memory is saved too, not only compute.

## Files

- `task.py`: the problems, how they are perceived, and the teacher
- `parts.py`: `Module` (a specialist) and `Router`, with sleep-time **pruning** (the connections that carry the least signal are cut and stay cut) and a router that can learn from awake outcomes
- `brain.py`: trial and error, memory, sleep, save/load
- `train.py`: the modular vs dense experiment
- `demo.py`: ask it questions
- `compose.py`: big problems (`10*10`, `1+1+1`, `12*(3+4)`, `7/2`, `-2.5*4`, any size) worked out from single-digit facts with written methods: column addition with carry, column subtraction with borrow, long multiplication, long division. Answers are exact (`1/3` stays `1/3`). When the answer is wrong, the teacher checks the steps it guessed, so fixing one big problem also teaches the facts underneath.
- `rules.py`: rules with letters (`n/n = 1`, `a*1 = a`) used as one-step shortcuts. Rules are taught, or **noticed**: the brain looks for a pattern in the facts it knows, checks there is no counterexample, and asks the teacher before trusting it (induction).
- `regions.py`: the brain as regions (arithmetic, knowledge, language) with separate storage, and the one-time move from the old single-region layout (old files kept in `brain_state/_before_regions/`)
- `index.py`: the cue index — cue word → the memories that word can be found in, so a question worded differently still finds its fact; built from stored state only, conservative on matching, exact search kept as fallback
- `language.py`: the language region (learned phrases, number patterns, local helper model)
- `planner.py`: the prefrontal region (plans, working memory)
- `monitor.py`: number sense, confidence, doubts
- `strategy.py`: the strategy chooser (basal ganglia) — it lives in the coordination region
- `coordination.py`: the coordination region — the tools (the group, percent, common-factor, least-multiple and unitary procedures moved here from the reading engine), where each tool may be used (cue words: the hand list plus what the tool was taught with), the rewards for work done with a tool, and the strategy chooser
- `english.py` + `english_chat.py`: the English region (word forms by "words and rules", word relations with reasoning, tense and agreement in sentences) and how English questions are recognised
- `equations.py`: missing numbers (8 + ? = 11) by inverse rules, and comparing (<, =, >)
- `curriculum_p3.py`: P3 lessons and exams (one file per level from P3 on)
- `curriculum.py` + `school.py`: the Singapore + Estonia school: `python -m brainlike.school P1` (add `--dry-run` to teach a copy)
- `serve.py`: JSON commands on stdin/stdout, used by the **Brain** tab in AgenticOS, where you are the teacher
- `world.py` + `stories.py`: the simulated world (scenes for the senses, facts, before/after events, and stories whose every sentence comes with the scene after it)
- `kindergarten.py`: the kindergarten region (words from scenes, facts with is-a inheritance, verb effects, lessons, exam, chat)
- `primary.py`: the world-based school (P1–P6, S1, S2): Singapore and secondary topics as stories with scenes, exam on new stories, feedback and retake, and an outside exam on ASDiv or GSM8K: `python -m brainlike.primary S2` (add `--dry-run`)
- `coding.py`: the code lesson — taught tools and taught recipes (a word pattern → the program to write, kept only if every worked example is reproduced), programs run and checked by undoing, then an exam: `python -m brainlike.coding`
- `storyreader.py`: reading a story by acting it out, with learned sentence frames, learned pronouns, a mental model with unknowns, and learning from a teacher's answer

