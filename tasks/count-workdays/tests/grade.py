#!/usr/bin/env python3
"""Hidden grader for the count-workdays task. Purely behavioural.

The grader never looks at how the tool is written; it only runs
``/app/bin/workdays START END`` and checks stdout and the exit status.

How it closes the cheap ways to a reward:

1. A fresh holiday list. Before grading, ``/app/holidays.txt`` is replaced by
   a randomly generated one (unsorted, with duplicates, weekend dates,
   comments and blank lines). A tool that bakes in the shipped holidays, or
   caches them anywhere, gets wrong answers.
2. Fresh date pairs every run, drawn with a new seed: short and long spans,
   reversed and equal pairs, pairs that start or end on a holiday or a
   weekend. Hardcoding the visible examples cannot pass.
3. Expected answers come from a brute-force day-by-day count with Python's
   ``datetime``, an implementation independent of the oracle's closed form.
4. Inside Docker the tool runs as ``nobody`` with /tests unreadable (see
   test.sh), so it cannot read this file or write the reward. Only /app was
   carried over from the agent's container, and test.sh itself is fresh.

Reward is binary: 1.0 only if every call gives the right output and status.
"""
import argparse
import datetime as dt
import json
import os
import pwd
import random
import subprocess
import sys

YEAR_MIN, YEAR_MAX = 1601, 3000
CALL_TIMEOUT = 5
LO = dt.date(YEAR_MIN, 1, 1).toordinal()
HI = dt.date(YEAR_MAX, 12, 31).toordinal()


def make_holidays(rng):
    """A random holiday list: (file text, set of dates)."""
    dates = []
    # dense around a few random decades, so short spans often hit holidays
    for _ in range(4):
        base = rng.randint(LO, HI - 3700)
        for _ in range(120):
            dates.append(dt.date.fromordinal(base + rng.randint(0, 3650)))
    # sparse across the whole range
    for _ in range(150):
        dates.append(dt.date.fromordinal(rng.randint(LO, HI)))
    dates += rng.sample(dates, 40)  # duplicates
    rng.shuffle(dates)
    lines = ["# hidden holiday list, seed-generated", ""]
    for i, d in enumerate(dates):
        lines.append(d.isoformat())
        if i % 97 == 0:
            lines.append("")
        if i % 131 == 0:
            lines.append("# comment line")
    return "\n".join(lines) + "\n", set(dates), sorted(set(dates))


def expected(a, b, holidays):
    sign = 1
    if b < a:
        a, b, sign = b, a, -1
    n = 0
    for o in range(a.toordinal(), b.toordinal()):
        d = dt.date.fromordinal(o)
        if d.weekday() < 5 and d not in holidays:
            n += 1
    return str(sign * n)


def make_cases(rng, hol_sorted):
    def rdate(lo=LO, hi=HI):
        return dt.date.fromordinal(rng.randint(lo, hi))

    cases = [("2024-12-23", "2024-12-30"), ("2024-12-30", "2024-12-23"),
             ("2025-01-01", "2025-01-01"), ("1601-01-01", "3000-12-31"),
             ("3000-12-31", "1601-01-01")]
    for span in [1, 2, 3, 5, 6, 7, 8, 13, 14, 30, 365, 3650, 36500, 200000]:
        for _ in range(6):
            a = rdate(LO, HI - span)
            b = dt.date.fromordinal(a.toordinal() + rng.randint(0, span))
            pair = (a.isoformat(), b.isoformat())
            cases.append(pair if rng.random() < 0.7 else pair[::-1])
    for _ in range(60):  # start or end exactly on a holiday
        h = rng.choice(hol_sorted)
        other = dt.date.fromordinal(min(HI, max(LO, h.toordinal()
                                                + rng.randint(-40, 40))))
        pair = (h.isoformat(), other.isoformat())
        cases.append(pair if rng.random() < 0.5 else pair[::-1])
    for _ in range(40):
        a = rdate()
        cases.append((a.isoformat(), a.isoformat()) if rng.random() < 0.2
                     else (a.isoformat(), rdate().isoformat()))
    invalid = [("2023-02-29", "2023-03-01"), ("2024-01-01", "1900-02-29"),
               ("2024-13-01", "2024-01-01"), ("2024-04-31", "2024-05-01"),
               ("2024-01-00", "2024-01-05"), ("1600-12-31", "1601-01-02"),
               ("2024-01-01", "3001-01-01"), ("tomorrow", "2024-01-01"),
               ("2024-01-01",), ("2024-01-01", "2024-01-02", "2024-01-03"),
               ()]
    return cases, invalid


def _demote(user):
    if not user or os.geteuid() != 0:
        return {}
    pw = pwd.getpwnam(user)
    return {"user": pw.pw_uid, "group": pw.pw_gid, "extra_groups": []}


def run_tool(tool, args, kwargs):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp",
           "LANG": "C.UTF-8"}
    try:
        p = subprocess.run([tool] + list(args), cwd="/tmp", env=env,
                           capture_output=True, text=True,
                           timeout=CALL_TIMEOUT, **kwargs)
    except subprocess.TimeoutExpired:
        return "<timeout>", None
    except (OSError, UnicodeDecodeError) as exc:
        return "<%s>" % type(exc).__name__, None
    return p.stdout.strip(), p.returncode


def grade(app, sandbox_user=None, seed=None):
    tool = os.path.join(app, "bin", "workdays")
    if not os.path.isfile(tool):
        return {"reward": 0.0, "error": "missing %s" % tool}
    if seed is None:
        seed = int.from_bytes(os.urandom(8), "big")
    rng = random.Random(seed)
    text, holidays, hol_sorted = make_holidays(rng)
    with open(os.path.join(app, "holidays.txt"), "w") as fh:
        fh.write(text)
    kwargs = _demote(sandbox_user)

    cases, invalid = make_cases(rng, hol_sorted)
    wrong = []
    for a, b in cases:
        want = expected(dt.date.fromisoformat(a), dt.date.fromisoformat(b),
                        holidays)
        out, code = run_tool(tool, (a, b), kwargs)
        if out != want or code != 0:
            wrong.append({"args": [a, b], "expected": want, "got": out,
                          "status": code})
    for args in invalid:
        out, code = run_tool(tool, args, kwargs)
        if out != "" or code != 2:
            wrong.append({"args": list(args), "expected": "no output, exit 2",
                          "got": out, "status": code})
    total = len(cases) + len(invalid)
    return {"reward": 1.0 if not wrong else 0.0, "seed": seed,
            "cases": total, "passed": total - len(wrong),
            "first_failures": wrong[:8]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="/app")
    ap.add_argument("--reward-file")
    ap.add_argument("--sandbox-user")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()
    result = grade(args.app, args.sandbox_user, args.seed)
    print(json.dumps(result, indent=2))
    if args.reward_file:
        os.makedirs(os.path.dirname(args.reward_file), exist_ok=True)
        with open(args.reward_file, "w") as fh:
            fh.write("%.1f\n" % result["reward"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
