#!/bin/bash
# Oracle: restore the formula with the century term on a continuation line,
# inside columns 7-72 where fixed-form Fortran actually reads it.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$DIR/calday.f" /app/calday.f
cd /app && ./run_examples.sh
