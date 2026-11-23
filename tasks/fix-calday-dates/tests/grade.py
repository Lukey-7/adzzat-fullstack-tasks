#!/usr/bin/env python3
"""Hidden grader for the fix-calday-dates task.

How it closes the cheap ways to a reward:

1. Only the submitted source file is graded. ``calday.f`` is copied into an
   empty directory and compiled here with a FIXED command
   (``gfortran -o calday calday.f``), so build-script or compiler-flag edits
   in the workspace change nothing, and the visible example file is ignored.
2. Fresh inputs every run. Most queries are random dates in 1601..3000, drawn
   with a new seed per grading run, plus fixed edge cases around century
   leap-year boundaries. Hardcoding the visible examples, or adding a constant
   offset that happens to fix this century, cannot pass.
3. Expected answers come from Python's ``datetime`` (proleptic Gregorian
   calendar), computed in this process and never written to disk.
4. Inside Docker the program is compiled and run as ``nobody`` and /tests is
   unreadable to it (see test.sh), so it cannot read this file or write the
   reward.

Reward is binary: 1.0 only if every answer line matches exactly.
"""
import argparse
import datetime as dt
import json
import os
import pwd
import random
import shutil
import subprocess
import sys
import tempfile

YEAR_MIN, YEAR_MAX = 1601, 3000
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY",
        "SUNDAY"]
COMPILE_TIMEOUT = 120
RUN_TIMEOUT = 60


# ---------------------------------------------------------------- reference
def ref_answer(query):
    parts = query.split()
    try:
        op, nums = parts[0], [int(p) for p in parts[1:]]
        if op == "DIFF" and len(nums) == 6:
            a, b = _date(*nums[:3]), _date(*nums[3:])
            return str(b.toordinal() - a.toordinal())
        if op == "ADD" and len(nums) == 4:
            res = dt.date.fromordinal(_date(*nums[:3]).toordinal() + nums[3])
            if not YEAR_MIN <= res.year <= YEAR_MAX:
                return "ERROR"
            return "%04d-%02d-%02d" % (res.year, res.month, res.day)
        if op == "DOW" and len(nums) == 3:
            return DAYS[_date(*nums).weekday()]
    except (ValueError, OverflowError):
        pass
    return "ERROR"


def _date(y, m, d):
    if not YEAR_MIN <= y <= YEAR_MAX:
        raise ValueError("year out of range")
    return dt.date(y, m, d)


# -------------------------------------------------------------------- cases
def _rand_date(rng, lo=YEAR_MIN, hi=YEAR_MAX):
    start = dt.date(lo, 1, 1).toordinal()
    end = dt.date(hi, 12, 31).toordinal()
    return dt.date.fromordinal(rng.randint(start, end))


def _ymd(d):
    return "%d %d %d" % (d.year, d.month, d.day)


FIXED = [
    # visible examples from the instruction
    "DIFF 2024 1 1 2024 3 1", "ADD 2024 2 28 2", "DOW 2024 1 1",
    # the bug report
    "DIFF 1900 2 28 1900 3 1", "DOW 1900 1 1", "DIFF 1601 1 1 3000 12 31",
    # century leap-year rules
    "DIFF 1700 2 28 1700 3 1", "DIFF 2000 2 28 2000 3 1",
    "DIFF 2100 2 28 2100 3 1", "DIFF 2400 2 28 2400 3 1",
    "ADD 1899 12 31 60", "ADD 2100 3 1 -1", "ADD 2000 3 1 -1",
    "DOW 2000 2 29", "DOW 2100 3 1", "DOW 1752 9 14", "DOW 3000 12 31",
    "DIFF 3000 12 31 1601 1 1", "ADD 1601 1 1 0", "ADD 1601 1 1 -1",
    "ADD 3000 12 31 1",
    # invalid input
    "DOW 1900 2 29", "DOW 2100 2 29", "DIFF 2023 2 29 2024 1 1",
    "DOW 2024 13 1", "DOW 2024 4 31", "DOW 2024 1 0", "DOW 1600 12 31",
    "DOW 3001 1 1", "DIFF 2024 1 1", "ADD 2024 1 1", "FOO 2024 1 1",
    "DOW x y z",
]


def make_cases(seed):
    rng = random.Random(seed)
    cases = list(FIXED)
    for _ in range(300):
        cases.append("DIFF %s %s" % (_ymd(_rand_date(rng)),
                                     _ymd(_rand_date(rng))))
    for c in range(1700, 3000, 100):  # pairs straddling each century's Feb
        a = _rand_date(rng, c - 1, c)
        b = _rand_date(rng, c, c + 1)
        cases.append("DIFF %s %s" % (_ymd(a), _ymd(b)))
    for _ in range(200):
        cases.append("ADD %s %d" % (_ymd(_rand_date(rng)),
                                    rng.randint(-200000, 200000)))
    for _ in range(200):
        cases.append("DOW %s" % _ymd(_rand_date(rng)))
    for _ in range(30):  # random invalid days
        y, m = rng.randint(YEAR_MIN, YEAR_MAX), rng.randint(1, 12)
        cases.append("DOW %d %d %d" % (y, m, rng.choice([0, 32, 30, 29])))
    rng.shuffle(cases)
    return cases


# ------------------------------------------------------------------- runner
def _demote(user):
    if not user or os.geteuid() != 0:
        return {}, None
    pw = pwd.getpwnam(user)
    return {"user": pw.pw_uid, "group": pw.pw_gid, "extra_groups": []}, pw


def grade(source, sandbox_user=None, seed=None):
    if not os.path.isfile(source) or os.path.islink(source):
        return {"reward": 0.0, "error": "missing or symlinked %s" % source}
    room = tempfile.mkdtemp(prefix="grade-room-")
    try:
        shutil.copyfile(source, os.path.join(room, "calday.f"))
        kwargs, pw = _demote(sandbox_user)
        if pw:
            os.chown(room, pw.pw_uid, pw.pw_gid)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": room}
        try:
            comp = subprocess.run(["gfortran", "-o", "calday", "calday.f"],
                                  cwd=room, env=env, capture_output=True,
                                  text=True, timeout=COMPILE_TIMEOUT, **kwargs)
        except subprocess.TimeoutExpired:
            return {"reward": 0.0, "error": "compile timeout"}
        if comp.returncode != 0:
            return {"reward": 0.0,
                    "error": "compile failed: " + comp.stderr[-1500:]}

        if seed is None:
            seed = int.from_bytes(os.urandom(8), "big")
        cases = make_cases(seed)
        expected = [ref_answer(q) for q in cases]
        try:
            run = subprocess.run([os.path.join(room, "calday")], cwd=room,
                                 env=env, input="\n".join(cases) + "\n",
                                 capture_output=True, text=True,
                                 timeout=RUN_TIMEOUT, **kwargs)
            got = [l.strip() for l in run.stdout.splitlines()]
        except subprocess.TimeoutExpired:
            return {"reward": 0.0, "error": "run timeout"}
        except UnicodeDecodeError:
            return {"reward": 0.0, "error": "non-text output"}

        wrong = []
        for i, (q, want) in enumerate(zip(cases, expected)):
            have = got[i] if i < len(got) else "<missing>"
            if have != want:
                wrong.append({"query": q, "expected": want, "got": have})
        if len(got) != len(cases):
            wrong.append({"query": "<line count>", "expected": len(cases),
                          "got": len(got)})
        passed = len(cases) - sum(1 for w in wrong if w["query"] !=
                                  "<line count>")
        return {"reward": 1.0 if not wrong else 0.0, "seed": seed,
                "cases": len(cases), "passed": passed,
                "first_failures": wrong[:8]}
    finally:
        shutil.rmtree(room, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/app/calday.f")
    ap.add_argument("--reward-file")
    ap.add_argument("--sandbox-user")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()
    result = grade(args.source, args.sandbox_user, args.seed)
    print(json.dumps(result, indent=2))
    if args.reward_file:
        os.makedirs(os.path.dirname(args.reward_file), exist_ok=True)
        with open(args.reward_file, "w") as fh:
            fh.write("%.1f\n" % result["reward"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
