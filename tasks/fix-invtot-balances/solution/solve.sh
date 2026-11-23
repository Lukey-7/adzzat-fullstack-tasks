#!/bin/bash
# Oracle. Three defects in the data definitions, none in the control flow:
#  1. WS-CUST-TOTAL is PIC 9(7)V99: no S, so a negative balance is stored as
#     its absolute value, and only 7 integer digits, so balances of 10 million
#     or more silently lose their high-order digits. -> PIC S9(9)V99
#  2. COMPUTE without ROUNDED truncates the taxed amount to the cent.
set -euo pipefail
python3 - <<'PY'
p = "/app/invtot.cbl"
s = open(p).read()
for old, new in [
    ("       01  WS-CUST-TOTAL           PIC 9(7)V99.\n",
     "       01  WS-CUST-TOTAL           PIC S9(9)V99.\n"),
    ("               COMPUTE WS-LINE =\n",
     "               COMPUTE WS-LINE ROUNDED =\n"),
]:
    assert s.count(old) == 1, "unexpected source"
    s = s.replace(old, new)
open(p, "w").write(s)
PY
cd /app && ./run_examples.sh
