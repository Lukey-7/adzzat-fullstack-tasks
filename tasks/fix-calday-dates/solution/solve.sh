#!/bin/bash
# Oracle. Root cause: in fixed-form Fortran only columns 7-72 of a line are
# read, and gfortran silently drops the rest (it warns only with -Wall). The
# century leap-year term of the Julian Day Number formula starts in column 73,
# so it was never compiled. Fix: move that term onto a continuation line.
set -euo pipefail
python3 - <<'PY'
p = "/app/calday.f"
s = open(p).read()
old = " / 12 - 3*((Y + 4900 + A)/100)/4\n"
new = " / 12\n     &    - 3*((Y + 4900 + A)/100)/4\n"
assert s.count(old) == 1, "unexpected source"
open(p, "w").write(s.replace(old, new))
PY
cd /app && ./run_examples.sh
