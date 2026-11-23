# Fix INVTOT's customer balances (COBOL)

`/app` contains INVTOT, a small COBOL program (`/app/invtot.cbl`, GnuCOBOL)
that turns a file of invoice records into a balance per customer. The comment
block at the top of that file is its specification: record layout, amounts,
rounding, output format and which lines are rejected.

The finance team reports wrong balances:

> Customer `BETA02` was charged 107.50 and refunded 161.25, so its balance
> should be `-000000053.75`, but INVTOT prints `+000000053.75`. Several
> balances are a cent or two low: `ACME01` should be `+000000034.92`, not
> `+000000034.90`. Our largest accounts also look wrong.

Fix the program so that its output is correct for **every** input the
specification allows, not only these customers.

## Rules

- **Only `/app/invtot.cbl` is graded.** The grader copies that one file into
  a clean directory and builds it with exactly `cobc -x -o invtot invtot.cbl`
  (GnuCOBOL 3.1, default options). Changes to `build.sh`, compiler flags or
  any other file have no effect on your score.
- Keep the program in COBOL and keep the input and output formats unchanged.
- `./run_examples.sh` builds the program and runs the example invoices
  (`examples/invoices.txt` against `examples/expected.txt`). The hidden
  grader runs a few dozen invoice files of random customers, amounts and
  rejected lines, anywhere within the documented limits, and passes only if
  every output line is correct.

## Difficulty: medium

Each fix is small; knowing what to look for in COBOL data definitions is the
work.
