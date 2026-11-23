# AI tools used, and where I corrected them

| Tool | Used for | Free? |
|---|---|---|
| Claude Code (Claude Opus 5.5) | Pair-programming: drafting the Fortran program, graders, harness, page and docs, and running the verification commands | No: my existing subscription. It was not used as a test-taker, and no paid API was called by anything in this repo |
| qwen2.5-coder:3b via Ollama, local CPU | The free agent that attempted both tasks (`agent/mini_agent.py`) | Yes |
| Harbor 0.27 (`oracle`, `nop` agents) | Running and linting the tasks | Yes (open source) |

Every result in this repo comes from free, local tools. Claude helped write
the code; it did not solve or score the tasks.

## Where the AI output was wrong, and what I changed

1. **The agent harness corrupted every file the model wrote.** The first
   harness piped file contents into `docker exec` in text mode. On Windows
   that turns `\n` into `\r\n`, so the model's `#!/bin/bash` became
   `#!/bin/bash\r` and every grader call failed with `FileNotFoundError`. I
   noticed because *every* case failed the same way, which looks like
   plumbing, not a model mistake. I replayed the transcript, found the 37-byte
   file that should have been 35 bytes, and switched the harness to bytes.
   The two void runs are kept in `runs/invalid/` and excluded from the
   results.
2. **The first "constant offset" shortcut tripped over the bug it was meant to
   paper over.** It inserted `- 51` into the long `JDN = ...` line, which
   pushed more of that line past column 72. So the demo was not testing the
   shortcut it claimed to test. I rewrote it as a separate statement,
   `JDN = JDN - 51`.
3. **The first task-1 statement gave the answer away.** Its difficulty note
   said the cause was "a property of the language rather than of the
   algorithm". I cut that from `instruction.md`. The full difficulty note now
   lives in `task.toml` metadata, which the page shows but the agent never
   sees.
4. **A grader case would have been unfair.** While planning the task-2
   invalid cases, the plan included loosely formatted dates such as
   `2024-1-05`. I dropped them before writing the grader. The statement
   says dates are *always* written as `YYYY-MM-DD`, and Python's own `strptime`
   accepts `2024-1-05`. So those cases would have tested a guess about
   unstated behaviour. I kept only impossible dates, out-of-range years,
   non-dates and wrong argument counts.
5. **The task-1 oracle first just copied a pristine file.** That proves
   nothing about the root cause, so I replaced it with the one-line edit (move
   the century term onto a continuation line). Now `solve.sh` documents the
   fix.
6. **The first COBOL grader import failed on Windows.** I generated the
   visible examples by importing the Linux-only grader (`import pwd`) on the
   Windows host. I stubbed `pwd` for that one-off generation, so the examples
   come from the same reference model that grades.
7. **Small things:** a wrong `harbor lint -p` flag (lint takes task
   directories). The shortcut demo also parsed test.sh output as pure JSON and
   crashed. It now extracts the JSON object.
