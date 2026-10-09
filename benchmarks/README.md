# Benchmarks (problems the brain's teacher did not write)

| File | What | Source |
|---|---|---|
| `svamp_train.csv` | 3,138 problems from MAWPS + ASDiv-A, with equations: the standard **training** set | https://github.com/arkilpatel/SVAMP (`data/mawps-asdiv-a_svamp/train.csv`) |
| `svamp_dev.csv` | **SVAMP**, 1,000 primary-school word problems built to catch shortcut reasoning: the **test** set | same repository (`dev.csv`) |
| `asdiv.xml` + `asdiv.py` | ASDiv problems labelled by grade (1-6); grades 1-2 are the outside exams of the world school, split into even (dev) and odd (test) problems | https://github.com/chaochun/nlu-asdiv-dataset |
| `gsm8k_test.jsonl` | **GSM8K** test set, 1,319 harder multi-step grade-school problems | https://github.com/openai/grade-school-math |

## Run
```powershell
.\.venv\Scripts\python.exe benchmarks\run_reader.py                       # train the brain's reader, test on SVAMP and GSM8K, save it into brain_state/language/
.\.venv\Scripts\python.exe benchmarks\run_llm.py qwen3:8b nothink 300 100  # a plain language model on the same problems
.\.venv\Scripts\python.exe benchmarks\run_llm.py qwen3:0.6b think 60 30
.\.venv\Scripts\python.exe benchmarks\run_llm_per_problem.py qwen3:8b nothink 300   # every answer saved in results/, for subset comparisons
.\.venv\Scripts\python.exe benchmarks\run_kindergarten.py                     # kindergarten stages 1-6 on the simulated world
.\.venv\Scripts\python.exe benchmarks\run_svamp_kindergarten.py test show     # SVAMP read by acting stories out (dev = 300-599)
.\.venv\Scripts\python.exe benchmarks\run_school.py                            # kindergarten + world school P1, P2, then ASDiv grades 1-2 (dev/test halves) vs the models
.\.venv\Scripts\python.exe benchmarks\run_llm_per_problem.py qwen3:8b nothink asdiv2   # a model on one ASDiv grade
.\.venv\Scripts\python.exe benchmarks\train_reasoner.py --no-save             # the step-by-step reasoner on worked solutions, test on SVAMP and GSM8K (--epochs N to change 6)
.\.venv\Scripts\python.exe benchmarks\bench_reasoner.py profile|parity|train  # cProfile the trainer | prove it matches the original loop | run train_reasoner.py
```
Samples: the first N SVAMP problems, and N GSM8K problems after shuffling with seed 0. The brain and the models get the same ones.
