#!/bin/sh
# Build the calday program in /app.
set -e
cd "$(dirname "$0")"
gfortran -o calday calday.f
