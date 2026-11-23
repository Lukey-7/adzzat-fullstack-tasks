#!/usr/bin/env python3
"""Gather every verified result into results/summary.json for the page.

Sources:
  jobs/<job>/<trial>/            Harbor runs (oracle, nop); latest per agent
  shortcuts/results.json         the shortcut demo (shortcuts/run_shortcuts.py)
  runs/<task>-<ts>.json          local free-model runs (agent/mini_agent.py)

    python tools/collect_results.py
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _grader_log(trial):
    path = os.path.join(trial, "verifier", "test-stdout.txt")
    try:
        text = open(path, encoding="utf-8").read()
        return json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (OSError, ValueError):
        return {}


def harbor_runs():
    latest = {}
    for res in sorted(glob.glob(os.path.join(ROOT, "jobs", "*", "*",
                                             "result.json"))):
        trial = os.path.dirname(res)
        job = os.path.basename(os.path.dirname(trial))
        with open(res, encoding="utf-8") as fh:
            data = json.load(fh)
        try:
            reward = float(open(os.path.join(trial, "verifier",
                                             "reward.txt")).read())
        except (OSError, ValueError):
            reward = None
        log = _grader_log(trial)
        agent = data["config"]["agent"]["name"]
        latest[(data["task_name"], agent)] = {
            "agent": agent, "reward": reward, "job": job,
            "cases": log.get("cases"), "passed": log.get("passed")}
    out = {}
    for (task, _), row in sorted(latest.items()):
        out.setdefault(task, []).append(row)
    return out


def main():
    summary = {}
    for task, rows in harbor_runs().items():
        summary.setdefault(task, {})["harbor"] = rows
    path = os.path.join(ROOT, "shortcuts", "results.json")
    if os.path.exists(path):
        for row in json.load(open(path, encoding="utf-8")):
            summary.setdefault(row["task"], {}).setdefault(
                "shortcuts", []).append(
                {k: row[k] for k in ("attempt", "visible_check",
                                     "hidden_reward", "passed", "cases")})
    for path in sorted(glob.glob(os.path.join(ROOT, "runs", "*.json"))):
        res = json.load(open(path, encoding="utf-8"))["result"]
        summary.setdefault(res["task"], {}).setdefault(
            "agent_runs", []).append(
            {"agent": res["agent"], "model": res["model"],
             "reward": res["reward"], "steps": res["steps"],
             "minutes": res["minutes"],
             "passed": res["grader"].get("passed"),
             "cases": res["grader"].get("cases"),
             "transcript": os.path.relpath(path, ROOT).replace(os.sep, "/")})
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "summary.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
