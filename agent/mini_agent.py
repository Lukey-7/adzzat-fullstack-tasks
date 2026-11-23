#!/usr/bin/env python3
"""A minimal free agent: a local Ollama model works on one task in Docker.

    ollama pull qwen2.5-coder:3b
    python agent/mini_agent.py fix-calday-dates --model qwen2.5-coder:3b

The model sees the task's instruction.md and answers each turn with ONE JSON
action, executed inside a container built from the task's own Dockerfile
(no network):

    {"action": "run", "cmd": "<shell command>"}
    {"action": "read", "path": "/app/calday.f"}
    {"action": "write", "path": "...", "content": "<whole file>"}
    {"action": "replace", "path": "...", "old": "<exact text>", "new": "..."}
    {"action": "done"}

After "done" (or the step limit) the task is graded exactly as Harbor's
separate verifier would: only the artifact leaves the agent's container and
tests/test.sh runs in a fresh one. The transcript and the result are written
to runs/<task>-<timestamp>.json. Standard library only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import tomllib
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "tasks")

SYSTEM = """You are a software engineer working in a Linux container.
Reply with exactly ONE JSON object per turn and nothing else. Actions:
  {"action": "run", "cmd": "<bash command>"}       (runs in /app, 60 s limit)
  {"action": "read", "path": "<absolute path>"}
  {"action": "replace", "path": "<absolute path>", "old": "<exact text>", "new": "<text>"}
  {"action": "write", "path": "<absolute path>", "content": "<whole file>"}
  {"action": "done"}                                (when the task is finished)
Prefer "replace" for small edits. Check your work by running it."""


def chat(model, messages, host):
    body = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "format": "json",
        # Ollama's default 4096-token context silently truncates long files.
        "options": {"temperature": 0.2, "num_ctx": 16384},
    }).encode()
    req = urllib.request.Request(host + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read())["message"]["content"]


def docker(*args, input=None, timeout=None):
    # Bytes, not text mode: on Windows, text-mode pipes turn "\n" into "\r\n",
    # which silently gave every file the model wrote CRLF line endings (and
    # broke "#!/bin/bash" shebangs) in the first runs.
    r = subprocess.run(["docker"] + list(args),
                       input=None if input is None else input.encode("utf-8"),
                       capture_output=True, timeout=timeout)
    return types.SimpleNamespace(
        returncode=r.returncode,
        stdout=r.stdout.decode("utf-8", "replace"),
        stderr=r.stderr.decode("utf-8", "replace"))


def act(cid, action):
    kind = action.get("action")
    if kind == "run":
        try:
            r = docker("exec", "-w", "/app", cid, "bash", "-c",
                       str(action.get("cmd", "")), timeout=60)
        except subprocess.TimeoutExpired:
            return "error: command timed out after 60 s"
        out = (r.stdout + r.stderr)[-3000:]
        return "exit status %d\n%s" % (r.returncode, out)
    if kind == "read":
        r = docker("exec", cid, "cat", str(action.get("path", "")))
        return (r.stdout or r.stderr)[:12000]
    if kind == "write":
        r = docker("exec", "-i", cid, "sh", "-c", 'cat > "$1"', "sh",
                   str(action.get("path", "")), input=action.get("content", ""))
        return "written" if r.returncode == 0 else "error: " + r.stderr
    if kind == "replace":
        path = str(action.get("path", ""))
        text = docker("exec", cid, "cat", path).stdout
        old = action.get("old", "")
        n = text.count(old) if old else 0
        if n != 1:
            return "error: 'old' text found %d times, need exactly 1" % n
        new_text = text.replace(old, action.get("new", ""))
        r = docker("exec", "-i", cid, "sh", "-c", 'cat > "$1"', "sh", path,
                   input=new_text)
        return "replaced" if r.returncode == 0 else "error: " + r.stderr
    return "error: unknown action; use run, read, write, replace or done"


def verify(task, tag, cid):
    """Separate verifier: copy the artifact out, grade it in a fresh container."""
    with open(os.path.join(TASKS, task, "task.toml"), "rb") as fh:
        artifact = tomllib.load(fh)["artifacts"][0]
    work = tempfile.mkdtemp(prefix="agent-verify-")
    try:
        docker("cp", "%s:%s" % (cid, artifact), os.path.join(work, "sub"))
        if artifact == "/app":
            place = "rm -r /app && cp -r /sub /app"
        else:
            place = "cp /sub %s" % artifact
        r = docker("run", "--rm", "--network", "none",
                   "-v", "%s:/sub:ro" % os.path.join(work, "sub"),
                   "-v", "%s:/tests_src:ro" % os.path.join(TASKS, task,
                                                           "tests"),
                   tag, "sh", "-c",
                   place + " && cp -r /tests_src /tests && "
                   "bash /tests/test.sh >/tmp/log 2>&1; "
                   "cat /logs/verifier/reward.txt; cat /tmp/log")
        lines = r.stdout.splitlines()
        rest = "\n".join(lines[1:])
        try:
            log = json.loads(rest[rest.index("{"):rest.rindex("}") + 1])
        except ValueError:
            log = {"raw": rest[-800:]}
        return float(lines[0]) if lines else 0.0, log
    finally:
        shutil.rmtree(work, ignore_errors=True)


def parse_action(reply):
    try:
        return json.loads(reply)
    except ValueError:
        m = re.search(r"\{.*\}", reply, re.S)
        try:
            return json.loads(m.group(0)) if m else {}
        except ValueError:
            return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--model", default="qwen2.5-coder:3b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--max-steps", type=int, default=30)
    args = ap.parse_args()

    tag = "adzzat-%s:local" % args.task
    b = docker("build", "-q", "-t", tag,
               os.path.join(TASKS, args.task, "environment"))
    if b.returncode != 0:
        sys.exit(b.stderr)
    cid = docker("run", "-d", "--network", "none", tag, "sleep",
                 "infinity").stdout.strip()
    with open(os.path.join(TASKS, args.task, "instruction.md"),
              encoding="utf-8") as fh:
        instruction = fh.read()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": instruction}]
    steps, started = [], time.time()
    try:
        for step in range(args.max_steps):
            reply = chat(args.model, messages, args.host)
            messages.append({"role": "assistant", "content": reply})
            action = parse_action(reply)
            if action.get("action") == "done":
                steps.append({"step": step, "action": action})
                break
            try:
                obs = act(cid, action)
            except Exception as exc:  # keep the loop alive on harness errors
                obs = "error: %s" % exc
            steps.append({"step": step, "action": action,
                          "observation": obs[:2000]})
            print("step %d: %s -> %s" % (step, json.dumps(action)[:120],
                                         obs[:80].replace("\n", " ")),
                  flush=True)
            messages.append({"role": "user", "content": obs})
        reward, log = verify(args.task, tag, cid)
    finally:
        docker("rm", "-f", cid)

    result = {"task": args.task, "agent": "mini_agent", "model": args.model,
              "steps": len(steps), "minutes": round((time.time() - started)
                                                    / 60, 1),
              "reward": reward, "grader": {k: log.get(k) for k in
                                           ("cases", "passed", "error",
                                            "first_failures")}}
    os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
    path = os.path.join(ROOT, "runs", "%s-%d.json" % (args.task, time.time()))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"result": result, "transcript": steps}, fh, indent=1)
    print(json.dumps(result, indent=2))
    print("transcript:", path)


if __name__ == "__main__":
    main()
