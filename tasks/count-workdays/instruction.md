# Count working days

Payroll needs a command-line tool that counts working days between two dates.

Make this command work:

```
/app/bin/workdays START END
```

It must print the number of **working days** `d` with `START <= d < END`
(the start date counts, the end date does not), as a plain integer followed by
a newline, and exit with status 0.

- A working day is a Monday to Friday that is not a holiday.
- Holidays are listed in `/app/holidays.txt`: one `YYYY-MM-DD` date per line;
  blank lines and lines starting with `#` are ignored. The list may be
  unsorted, may contain duplicates, and may contain dates that fall on a
  weekend (those change nothing). **The file is replaced every year, so the
  tool must read it each time it runs.**
- `START` and `END` are always written as `YYYY-MM-DD`. Supported years are
  1601 to 3000 (Gregorian calendar).
- If `END` is earlier than `START`, print the count for `END <= d < START`
  as a negative number. If they are equal, print `0`.
- If the arguments are not exactly two valid dates in the supported range
  (for example `2023-02-29`, `2024-13-01`, `1600-12-31` or `tomorrow`),
  print nothing on standard output and exit with status 2.

With the `holidays.txt` that is in `/app` now:

```
$ /app/bin/workdays 2024-12-23 2024-12-30
3
$ /app/bin/workdays 2024-12-30 2024-12-23
-3
$ /app/bin/workdays 2025-01-01 2025-01-01
0
$ /app/bin/workdays 2023-02-29 2023-03-01      # exit status 2, no output
```

## Rules

- Use whatever is installed in this container: Fortran (`gfortran`; the team's
  existing date calculator is in `/app/calday`, with its specification at the
  top of `calday.f`), Python 3 or POSIX shell. There is no network access.
- Everything the tool needs must live under `/app`; only `/app` is kept for
  grading. The tool is run as an unprivileged user, so it must not write to
  `/app` (it may use `/tmp`).
- The grader runs the tool on several hundred hidden date pairs, spanning
  anything from a day to a few centuries, with a different `holidays.txt`.
  Each call must finish within 5 seconds.

## Difficulty: easy

The goal is precise; the work is getting every edge right.
