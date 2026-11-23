#!/usr/bin/env python3
"""Show that the graders stop the obvious shortcuts.

For each attempt this script builds the task's Docker image, applies the
attempt to a copy of the task's /app, then in Docker:

  1. runs the VISIBLE check an agent can see (run_examples.sh, or the
     examples from the statement), which is what a naive grader would use;
  2. simulates Harbor's separate verifier: a fresh container from the same
     image receives only the task's artifact (calday.f, or /app), plus a
     fresh /tests, and runs tests/test.sh, which writes the reward.

Usage:  python shortcuts/run_shortcuts.py          (needs Docker)
Writes shortcuts/results.json.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "tasks")
HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------- attempts
def t1_constant_offset(app):
    """Subtract the 51-day error seen in 2024 instead of fixing the cause."""
    p = os.path.join(app, "calday.f")
    src = open(p).read()
    old = "(Y + 4900 + A)/100)/4\n"
    assert src.count(old) == 1
    src = src.replace(old, old + "      JDN = JDN - 51\n", 1)
    open(p, "w", newline="\n").write(src)


def t1_build_flag(app):
    """Make the build read long lines instead of fixing the source."""
    p = os.path.join(app, "build.sh")
    src = open(p).read().replace("gfortran -o calday calday.f",
                                 "gfortran -ffixed-line-length-none "
                                 "-o calday calday.f")
    open(p, "w", newline="\n").write(src)


def t1_real_fix(app):
    """The upstream calday source, with the formula inside column 72."""
    shutil.copyfile(os.path.join(ROOT, "calday", "calday.f"),
                    os.path.join(app, "calday.f"))


HARDCODED = """#!/bin/sh
# Answers the visible examples from the statement, nothing else.
case "$1 $2" in
  "2024-12-23 2024-12-30") echo 3 ;;
  "2024-12-30 2024-12-23") echo -3 ;;
  "2025-01-01 2025-01-01") echo 0 ;;
  *) exit 2 ;;
esac
"""

BAKED = r'''#!/usr/bin/env python3
# Correct counting, but the holidays shipped with the task are baked in.
import datetime as dt, re, sys
HOLIDAYS = {dt.date.fromisoformat(s) for s in """%s""".split()}
def parse(t):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t): raise ValueError
    d = dt.date.fromisoformat(t)
    if not 1601 <= d.year <= 3000: raise ValueError
    return d
try:
    a, b = (parse(x) for x in sys.argv[1:])
except ValueError:
    sys.exit(2)
s = 1
if b < a: a, b, s = b, a, -1
n = sum(1 for o in range(a.toordinal(), b.toordinal())
        if dt.date.fromordinal(o).weekday() < 5
        and dt.date.fromordinal(o) not in HOLIDAYS)
print(s * n)
'''


def t2_hardcode(app):
    _write_tool(app, HARDCODED)


def t2_baked_holidays(app):
    shipped = [l.strip() for l in open(os.path.join(app, "holidays.txt"))
               if l.strip() and not l.startswith("#")]
    _write_tool(app, BAKED % " ".join(shipped))


def t2_real_fix(app):
    shutil.copyfile(os.path.join(TASKS, "count-workdays", "solution",
                                 "workdays"),
                    os.path.join(app, "bin", "workdays"))


def _write_tool(app, text):
    with open(os.path.join(app, "bin", "workdays"), "w", newline="\n") as fh:
        fh.write(text)


VISIBLE_T1 = "cd /app && sh run_examples.sh >/dev/null 2>&1 && echo PASS || echo FAIL"
VISIBLE_T2 = ("chmod +x /app/bin/workdays; w=/app/bin/workdays; "
              "[ \"$($w 2024-12-23 2024-12-30)\" = 3 ] && "
              "[ \"$($w 2024-12-30 2024-12-23)\" = -3 ] && "
              "[ \"$($w 2025-01-01 2025-01-01)\" = 0 ] && "
              "{ $w 2023-02-29 2023-03-01; [ $? = 2 ]; } && echo PASS || echo FAIL")

def t3_symptoms_only(app):
    """Add the sign and ROUNDED, keep the 7-digit balance field."""
    p = os.path.join(app, "invtot.cbl")
    src = open(p).read()
    for old, new in [("PIC 9(7)V99.", "PIC S9(7)V99."),
                     ("COMPUTE WS-LINE =", "COMPUTE WS-LINE ROUNDED =")]:
        assert src.count(old) == 1
        src = src.replace(old, new)
    open(p, "w", newline="\n").write(src)


def t3_real_fix(app):
    shutil.copyfile(os.path.join(ROOT, "invtot", "invtot.cbl"),
                    os.path.join(app, "invtot.cbl"))


VISIBLE_T3 = "cd /app && sh run_examples.sh >/dev/null 2>&1 && echo PASS || echo FAIL"

ATTEMPTS = [
    ("fix-calday-dates", "S1 constant offset: subtract the 51 days seen in 2024",
     t1_constant_offset, VISIBLE_T1, "/app/calday.f"),
    ("fix-calday-dates", "S2 build flag: -ffixed-line-length-none in build.sh",
     t1_build_flag, VISIBLE_T1, "/app/calday.f"),
    ("fix-calday-dates", "control: the real fix (oracle source)",
     t1_real_fix, VISIBLE_T1, "/app/calday.f"),
    ("count-workdays", "S3 hardcode the visible examples",
     t2_hardcode, VISIBLE_T2, "/app"),
    ("count-workdays", "S4 bake the shipped holidays into the tool",
     t2_baked_holidays, VISIBLE_T2, "/app"),
    ("count-workdays", "control: the real tool (oracle)",
     t2_real_fix, VISIBLE_T2, "/app"),
    ("fix-invtot-balances", "S5 fix only the reported symptoms (sign, rounding)",
     t3_symptoms_only, VISIBLE_T3, "/app/invtot.cbl"),
    ("fix-invtot-balances", "control: the real fix (upstream invtot.cbl)",
     t3_real_fix, VISIBLE_T3, "/app/invtot.cbl"),
]


# ----------------------------------------------------------------- docker
def docker(*args, **kw):
    return subprocess.run(["docker"] + list(args), capture_output=True,
                          text=True, **kw)


def build(task):
    tag = "adzzat-%s:local" % task
    r = docker("build", "-q", "-t", tag,
               os.path.join(TASKS, task, "environment"))
    if r.returncode != 0:
        sys.exit("docker build failed for %s:\n%s" % (task, r.stderr))
    return tag


def run_attempt(task, tag, apply, visible_cmd, artifact):
    work = tempfile.mkdtemp(prefix="shortcut-")
    try:
        app = os.path.join(work, "app")
        shutil.copytree(os.path.join(TASKS, task, "environment", "app"), app)
        apply(app)
        # 1. visible check, as the agent would see it
        vis = docker("run", "--rm", "-v", "%s:/src:ro" % app, tag, "sh", "-c",
                     "rm -r /app && cp -r /src /app && " + visible_cmd)
        visible = vis.stdout.strip().splitlines()[-1] if vis.stdout else "ERR"
        # 2. separate verifier: fresh container, only the artifact + /tests
        if artifact == "/app":
            place = "rm -r /app && cp -r /sub /app"
        else:
            place = "cp /sub/%s %s" % (os.path.basename(artifact), artifact)
        ver = docker("run", "--rm", "-v", "%s:/sub:ro" % app,
                     "-v", "%s:/tests_src:ro" % os.path.join(TASKS, task,
                                                             "tests"),
                     tag, "sh", "-c",
                     place + " && cp -r /tests_src /tests && "
                     "bash /tests/test.sh >/tmp/log 2>&1; "
                     "cat /logs/verifier/reward.txt; cat /tmp/log")
        lines = ver.stdout.splitlines()
        reward = float(lines[0]) if lines else 0.0
        rest = "\n".join(lines[1:])
        try:
            log = json.loads(rest[rest.index("{"):rest.rindex("}") + 1])
        except ValueError:
            log = {"raw": rest[-800:]}
        return visible, reward, log
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    tags = {}
    results = []
    for task, name, apply, visible_cmd, artifact in ATTEMPTS:
        if task not in tags:
            tags[task] = build(task)
        visible, reward, log = run_attempt(task, tags[task], apply,
                                           visible_cmd, artifact)
        results.append({"task": task, "attempt": name,
                        "visible_check": visible, "hidden_reward": reward,
                        "passed": log.get("passed"),
                        "cases": log.get("cases"),
                        "example_failure": (log.get("first_failures")
                                            or [None])[0]})
        print("%-17s %-55s visible=%-4s hidden=%.1f (%s/%s)"
              % (task, name, visible, reward, log.get("passed"),
                 log.get("cases")))
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
