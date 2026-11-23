#!/bin/sh
# Build the invtot program in /app.
set -e
cd "$(dirname "$0")"
cobc -x -o invtot invtot.cbl
