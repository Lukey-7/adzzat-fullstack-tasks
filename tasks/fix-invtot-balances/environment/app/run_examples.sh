#!/bin/sh
# Build invtot, run the example invoices and compare with the expected output.
cd "$(dirname "$0")"
./build.sh || exit 1
./invtot < examples/invoices.txt > /tmp/invtot-out.txt
if diff -u examples/expected.txt /tmp/invtot-out.txt; then
  echo "examples: all match"
else
  echo "examples: MISMATCH (see diff above)"
  exit 1
fi
