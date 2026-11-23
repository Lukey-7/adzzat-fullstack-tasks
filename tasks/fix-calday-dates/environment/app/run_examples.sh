#!/bin/sh
# Build calday, run the example queries and compare with the expected answers.
cd "$(dirname "$0")"
./build.sh || exit 1
./calday < examples/queries.txt > /tmp/calday-out.txt
if diff -u examples/expected.txt /tmp/calday-out.txt; then
  echo "examples: all match"
else
  echo "examples: MISMATCH (see diff above)"
  exit 1
fi
