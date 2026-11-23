#!/bin/bash
# Oracle: install a small Python implementation as /app/bin/workdays.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$DIR/workdays" /app/bin/workdays
chmod 755 /app/bin/workdays
/app/bin/workdays 2024-12-23 2024-12-30
