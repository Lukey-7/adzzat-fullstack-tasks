# Fix CALDAY's date arithmetic (Fortran 77)

`/app` contains CALDAY, a small calendar calculator written in fixed-form
Fortran 77 (`/app/calday.f`). The comment block at the top of that file is its
specification: it reads `DIFF`, `ADD` and `DOW` queries from standard input
and writes one answer line per query.

Users report wrong answers:

> `DOW 2024 1 1` prints `WEDNESDAY`, but 1 January 2024 was a Monday.
> `ADD 2024 2 28 2` prints `2024-04-21` instead of `2024-03-01`.
> `DIFF 1900 2 28 1900 3 1` prints `2`, but 1900 was not a leap year, so the
> answer is `1`. Day counts between two dates in the same century look right.

Fix the program so that **every** query is answered correctly for the
(proleptic) Gregorian calendar, exactly as the header comment describes,
including `ERROR` for invalid dates and out-of-range results.

## Rules

- **Only `/app/calday.f` is graded.** The grader copies that one file into a
  clean directory and builds it with exactly `gfortran -o calday calday.f`
  (gfortran 12, default options). Changes to `build.sh`, compiler flags or any
  other file have no effect on your score.
- Keep the program in Fortran and keep the input and output formats unchanged.
- `./run_examples.sh` builds the program and checks five visible examples.
  The hidden grader checks several hundred queries, most of them random dates
  between 1601 and 3000, and passes only if every answer is correct.

## Difficulty: medium

A small fix once found; finding it is the work.
