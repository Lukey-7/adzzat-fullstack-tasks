#!/bin/bash
# Harbor verifier entry point. Runs in a fresh container after the agent has
# finished; only /app/calday.f is copied in from the agent's container.
# Writes a single reward (1.0 or 0.0) to /logs/verifier/reward.txt.
set -u
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt

# The submission is compiled and run as 'nobody'; it must not read the grader.
chmod -R go-rwx /tests

python3 /tests/grade.py \
  --source /app/calday.f \
  --reward-file /logs/verifier/reward.txt \
  --sandbox-user nobody

# A crashed grader must never leave the reward missing.
if [ ! -s /logs/verifier/reward.txt ]; then
  echo 0 > /logs/verifier/reward.txt
fi
