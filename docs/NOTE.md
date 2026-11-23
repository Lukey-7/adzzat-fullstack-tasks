# Note: what I checked, what I changed, what I would do next

## Results (all run on 2026-11-23, local Docker, free tools only)

| | fix-calday-dates (Fortran, medium) | count-workdays (outcome, easy) | fix-invtot-balances (COBOL, medium) |
|---|---|---|---|
| `harbor lint` | clean | clean | clean |
| Harbor `oracle` | **1.0** (776/776 hidden cases) | **1.0** (200/200) | **1.0** (28/28 files) |
| Harbor `nop` | **0.0** (135/776) | **0.0** (tool missing) | **0.0** (2/28) |
| Shortcut that passes the visible check | S2 build flag `-ffixed-line-length-none`: hidden **0.0** (146/776) | S3 hardcoded examples: **0.0** (12/200). S4 shipped holidays baked in: **0.0** (120/200) | S5 fix only the reported symptoms (sign, rounding): hidden **0.0** (4/28) |
| Other shortcut | S1 constant `-51` offset: visible FAIL, hidden **0.0** (203/776) | – | – |
| Real fix as control (same script) | **1.0** | **1.0** | **1.0** |
| qwen2.5-coder:3b, 2 runs each | **0.0, 0.0** | **0.0, 0.0** | **0.0, 0.0** |

Oracle and nop are from the latest Harbor jobs, which covered all three tasks.
Earlier jobs on the first two tasks gave the same rewards. The shortcut
numbers are from the latest run of `shortcuts/run_shortcuts.py`. Its random
inputs change every run, so the pass counts differ slightly from run to run,
but the rewards do not.

The page shows the same numbers per task. They come from
`results/summary.json`, which is built from the Harbor job folders, the
shortcut demo and the agent transcripts in `runs/`.

## The shortcuts, and how the graders stop them

In task 1 the century leap-year term of the formula sits in column 73+, which
fixed-form Fortran ignores. The tempting shortcut is to leave the source alone
and add `-ffixed-line-length-none` to `build.sh`. The visible examples then
pass. The grader stops this in three ways:

- only `calday.f` crosses to the separate verifier container;
- it is compiled there with a fixed `gfortran -o calday calday.f`;
- it is checked on several hundred fresh random dates against Python's
  `datetime`.

So the shortcut scores 0.0. The same random dates also defeat the
constant-offset patch, which is right only for 1900-03-01 to 2100-02-28. In
task 2 the grader writes a new random `holidays.txt` before grading, so a
tool that memorised the shipped list fails. `python shortcuts/run_shortcuts.py`
reproduces all of this.

In task 3 (COBOL) the natural shortcut is to fix only what the bug report
names: add the sign and `ROUNDED`. That passes the visible examples. The
balance field still holds only 7 integer digits, though, so every hidden file
with an account above 9,999,999.99 comes out wrong, and the reward is 0.0.

## What the free agent did (and what that can and cannot show)

- Task 1, run 1: tried a `replace` whose `old` text was not in the file, then
  said "done".
- Task 1, run 2: rewrote the whole file and, while doing so, joined the `LEAP`
  continuation into one long line. That pushed the line past column 72, so
  the file no longer compiled. The model hit the very trap the task is about,
  which suggests the task tests the intended knowledge.
- Task 2, both runs: wrote a plausible bash script at `/app/workdays.sh`, but
  never created `/app/bin/workdays`, the path the statement names, so every
  call failed. I re-read the statement for ambiguity: the path appears in the
  first code block and in every example, so I did not change it.

- Task 3, both runs: the model read the file and went straight for the
  right statement. It tried to add `+ 0.005` before the truncating `COMPUTE`,
  a hand-rolled half-up rounding that would work for these positive amounts.
  But its `replace` quoted the statement on one line, while in the file it
  spans two. Every attempt failed to match, and it repeated the same action
  until the 30-step limit. Even if the edit had landed, it would still have
  missed the sign and the field width. This is a harness and model
  limitation, not a task flaw: a line-tolerant edit tool would have helped.

Six runs of a 3B model on a CPU show only that the tasks are not trivial for
a very weak model and that the graders score its output without crashing.
They say nothing about how a strong model would fare, how hard the tasks are
for humans, or whether 0.0 is stable: at temperature 0.2 the runs differ.
The oracles show the tasks are solvable. I wrote them, so they do not show the
statements are unambiguous to a fresh reader.

## What I changed along the way

- **Added a third task (COBOL) on request.** The brief's stretch suggested a
  third task "of the other kind". This one is language-driven, so the set is
  two language-driven tasks (Fortran, COBOL) and one outcome-driven task.
- **Hinted at the hidden COBOL defect in the statement.** The bug report
  names the sign and rounding symptoms, and also says "our largest accounts
  also look wrong". The header comment documents the balance range. Without
  that hint, the width defect would be a hidden requirement, not a bug to
  find.

- **Fixed my agent harness.** Text-mode pipes on Windows added `\r` to every
  file the model wrote. The first two runs are void, kept in `runs/invalid/`.
- **Made the task-1 statement fairer.** I removed a hint that gave away the
  cause, and added the 1900 example so a constant offset visibly fails.
- **Kept task-2 invalid cases to clear-cut ones.** These are impossible dates,
  out-of-range years, non-dates and wrong argument counts, not format variants
  the statement does not define. I also stated the 5-second limit and the
  span size, because a day-by-day `date -d` loop in bash would time out.
- **Restored execute permission for task 2.** test.sh makes everything under
  `/app` executable again, since execute bits do not survive a trip through a
  Windows host's filesystem.
- **Made the task-1 oracle the real one-line fix**, not a file copy.

## What I would do next

1. Have someone who did not write the tasks attempt them, and run a stronger
   free model (e.g. a 14B+ coder model on a GPU) several times per task to get
   a pass rate with a confidence interval rather than anecdotes.
2. Add a held-out variant of each task (another long line, other
   holiday rules) to check for memorisation.
3. Report partial scores in the grader log by query type (DIFF / ADD / DOW,
   invalid input) so failures are easier to diagnose. The reward would stay
   binary.
4. On the page: show transcripts, and run the grader from the page against an
   uploaded submission in a sandbox.
