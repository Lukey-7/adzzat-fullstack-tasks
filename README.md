# Two verified tasks and a small page that shows them

Take-home for the Full-Stack Software Engineer role at Adzzat Labs.

- **Two Terminal-Bench-style tasks** in Harbor format, built on one small
  codebase ([`calday/`](calday/), a Fortran 77 date calculator, MIT, written
  for this exercise):
  - [`fix-calday-dates`](tasks/fix-calday-dates/): **language-driven**,
    medium. Fix wrong date arithmetic in the Fortran program. The root cause
    is a fixed-form Fortran rule, not the algorithm.
  - [`count-workdays`](tasks/count-workdays/): **outcome-driven**, easy. Only
    the goal is stated: a `workdays START END` CLI that counts working days
    against a holiday file. The code is never described, and grading is purely
    behavioural.
- **Hidden graders** run in Harbor's separate verifier container, on fresh
  random inputs every run. A [shortcut demo](shortcuts/run_shortcuts.py)
  shows four shortcuts that the graders block.
- **A minimal full-stack page** ([`page/`](page/)): FastAPI serves
  `GET /api/tasks` and `GET /api/tasks/{id}`, reading the task folders
  directly. A single static HTML/JS page shows a list and a detail view:
  statement, difficulty, environment, and the verified results.

Results, what I checked and what I would do next: [docs/NOTE.md](docs/NOTE.md).
AI tools and where I corrected them: [docs/AI_TOOLS.md](docs/AI_TOOLS.md).

## Layout

```
calday/                 the small codebase (correct upstream version)
tasks/<id>/
  instruction.md        statement shown to the agent
  task.toml             Harbor config: difficulty + difficulty_note, kind,
                        graded artifacts, separate verifier
  environment/          Dockerfile + /app contents the agent starts from
  solution/solve.sh     oracle
  tests/test.sh         verifier entry point -> /logs/verifier/reward.txt
  tests/grade.py        hidden grader
shortcuts/              shortcut demo + its results.json
agent/mini_agent.py     free local agent (Ollama) that runs in the task container
tools/collect_results.py  merges Harbor jobs, shortcut and agent results
results/summary.json    what the page shows as "results"
runs/                   agent transcripts (runs/invalid: void runs, see NOTE)
page/                   FastAPI backend, static frontend, API tests, Dockerfile
```

## Setup

Requirements: Docker, Python 3.12+ and [uv](https://docs.astral.sh/uv/).
The tasks also need [Harbor](https://github.com/laude-institute/harbor)
(`uv tool install harbor`). The agent runs need [Ollama](https://ollama.com)
with `ollama pull qwen2.5-coder:3b`. Everything is free and runs locally.

## Run

**The page** (http://localhost:8000):

```
cd page
uv run uvicorn app:app --port 8000
```

or in Docker, from the repo root: `docker compose up --build`.

**The tasks in Harbor:**

```
harbor lint tasks/fix-calday-dates tasks/count-workdays
harbor run -p tasks -a oracle     # expect 1.0 on both
harbor run -p tasks -a nop        # expect 0.0 on both
```

**Shortcut demo** (needs Docker): `python shortcuts/run_shortcuts.py`

**Free local agent:** start `ollama serve`, then
`python agent/mini_agent.py fix-calday-dates --model qwen2.5-coder:3b`.

**Refresh the results the page shows:** `python tools/collect_results.py`
(reads `jobs/`, `shortcuts/results.json` and `runs/*.json`).

## Test

```
cd page
uv run pytest -q          # API tests: list, detail, 404 and path-traversal ids, index
```

The task graders are tested by the Harbor oracle and nop runs and by the
shortcut demo. Each shortcut demo includes a real fix as a control, which
must score 1.0.

## Design choices, briefly

- **One codebase, two kinds of task.** Task 1 is about the *language*: the
  bug only makes sense once you know that fixed-form Fortran ignores columns
  73 and beyond. Task 2 is about the *outcome*: any language in the container
  is fine.
- **Only the artifact crosses to the verifier.** That is `calday.f` for
  task 1 and `/app` for task 2, so build-flag edits or planted files elsewhere
  do nothing. The grader compiles with a fixed command and runs the
  submission as `nobody`. `/tests` is unreadable to it.
- **Differential grading on random inputs.** Expected answers come from
  Python's `datetime`, computed in memory per run. Task 2 also swaps in a
  fresh, randomly generated `holidays.txt`.
- **The page reads the task folders directly**, so it cannot drift from what
  Harbor runs. The statement's HTML is rendered from this repo's own
  Markdown. Every other field is escaped in the browser.
