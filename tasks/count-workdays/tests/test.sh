#!/bin/bash
# Harbor verifier entry point. Runs in a fresh container after the agent has
# finished; only /app is copied in from the agent's container.
# Writes a single reward (1.0 or 0.0) to /logs/verifier/reward.txt.
set -u
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt

# The tool runs as 'nobody'; it must not read the grader.
chmod -R go-rwx /tests
# Copying /app out of one container and into another can drop execute bits
# (for example via a Windows host). Restore read+execute for everyone; /app
# stays owned by root, so the tool still cannot write there.
chown -R root:root /app
chmod -R a+rX,go-w /app
find /app -type f -exec chmod a+x {} +

python3 /tests/grade.py \
  --app /app \
  --reward-file /logs/verifier/reward.txt \
  --sandbox-user nobody

if [ ! -s /logs/verifier/reward.txt ]; then
  echo 0 > /logs/verifier/reward.txt
fi
