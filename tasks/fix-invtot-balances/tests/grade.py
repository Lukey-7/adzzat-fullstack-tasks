#!/usr/bin/env python3
"""Hidden grader for the fix-invtot-balances task (COBOL).

How it closes the cheap ways to a reward:

1. Only the submitted source file is graded. ``invtot.cbl`` is copied into an
   empty directory and compiled here with a FIXED command
   (``cobc -x -o invtot invtot.cbl``), so build-script or compiler-flag edits
   change nothing, and the visible example files are ignored.
2. Fresh inputs every run: several invoice files with random customers,
   quantities and prices, drawn with a new seed per run, including customers
   whose refunds exceed their charges, balances above 10 million, amounts
   whose tax lands exactly on half a cent, and rejected lines. Fixing only the
   reported symptoms, or hardcoding the visible examples, cannot pass.
3. Expected output comes from an independent Python model using ``Decimal``
   with ROUND_HALF_UP, computed in this process and never written to disk.
4. Inside Docker the program is compiled and run as ``nobody`` and /tests is
   unreadable to it (see test.sh).

Reward is binary: 1.0 only if every output file matches exactly.
"""
import argparse
import json
import os
import pwd
import random
import shutil
import string
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal

COMPILE_TIMEOUT = 180
RUN_TIMEOUT = 30
CENT = Decimal("0.01")
TAX = Decimal("1.075")
MAX_BAL = Decimal("999999999.99")


# ---------------------------------------------------------------- reference
def _amount(qty, price):
    return (Decimal(int(qty)) * Decimal(int(price)) / 100 * TAX).quantize(
        CENT, rounding=ROUND_HALF_UP)


def _accepted(line):
    rec = line.ljust(17)
    t, q, p = rec[6], rec[7:10], rec[10:17]
    return t in "CR" and len(t) == 1 and q.isdigit() and p.isdigit() \
        and q.isascii() and p.isascii()


def _fmt(value, digits):
    sign = "-" if value < 0 else "+"
    whole, frac = divmod(abs(value) * 100, 100)
    return "%s%0*d.%02d" % (sign, digits, int(whole), int(frac))


def reference(lines):
    out, rejected, grand = [], 0, Decimal(0)
    cur, bal = None, None
    for line in lines:
        if not _accepted(line):
            rejected += 1
            continue
        rec = line.ljust(17)
        cust = rec[:6]
        if cur is None or cust != cur:
            if cur is not None:
                out.append("%s %s" % (cur, _fmt(bal, 9)))
            cur, bal = cust, Decimal(0)
        amt = _amount(rec[7:10], rec[10:17])
        if rec[6] == "C":
            bal += amt
            grand += amt
        else:
            bal -= amt
            grand -= amt
    if cur is not None:
        out.append("%s %s" % (cur, _fmt(bal, 9)))
    out.append("TOTAL  %s" % _fmt(grand, 11))
    out.append("REJECTED %05d" % rejected)
    return out


# -------------------------------------------------------------------- cases
def _rec(cust, typ, qty, price):
    return "%s%s%03d%07d" % (cust, typ, qty, price)


def _half_cent_price(rng):
    """A price (cents) for qty 1 whose taxed amount ends in exactly half a
    cent: price * 1.075 has a third decimal of 5 when price % 40 == 20."""
    return rng.randint(0, 249999) * 40 + 20


def _customer(rng, cid, kind):
    recs = []
    if kind == "big":  # balance above 10 million (but within the limit)
        for _ in range(rng.randint(2, 6)):
            recs.append(_rec(cid, "C", rng.randint(500, 999),
                             rng.randint(3000000, 9999999)))
    elif kind == "negative":  # refunds exceed charges
        recs.append(_rec(cid, "C", rng.randint(1, 20),
                         rng.randint(100, 50000)))
        for _ in range(rng.randint(1, 3)):
            recs.append(_rec(cid, "R", rng.randint(10, 300),
                             rng.randint(10000, 900000)))
    elif kind == "halfcent":
        for _ in range(rng.randint(1, 4)):
            recs.append(_rec(cid, rng.choice("CR"), 1, _half_cent_price(rng)))
    else:  # mixed
        for _ in range(rng.randint(1, 8)):
            recs.append(_rec(cid, rng.choice("CCCR"), rng.randint(0, 999),
                             rng.randint(0, 9999999)))
    return recs


BAD = ["", "A00001", "A00001C12", "A00001X0010000100", "A00001c0010000100",
       "A00001C01A0000100", "A00001C001000010 ", "A00001R0010000-10",
       "A00001C0010000", "A00001 0010000100"]


def make_file(rng):
    ids = set()
    while len(ids) < rng.randint(3, 12):
        ids.add("".join(rng.choice(string.ascii_uppercase + string.digits)
                        for _ in range(6)))
    lines = []
    for cid in ids:
        kind = rng.choice(["big", "negative", "halfcent", "mixed", "mixed"])
        recs = _customer(rng, cid, kind)
        if rng.random() < 0.3:  # a rejected line inside the group
            recs.insert(rng.randint(0, len(recs)), rng.choice(BAD))
        lines += recs
    if rng.random() < 0.5:
        lines.insert(0, rng.choice(BAD))
    return lines


def _keep_in_range(lines):
    """Drop customers whose balance would leave the documented range."""
    groups, order = {}, []
    for line in lines:
        key = line.ljust(17)[:6] if _accepted(line) else None
        if key is not None and key not in groups:
            order.append(key)
        groups.setdefault(key, []).append(line)
    for key in order:
        bal = Decimal(0)
        for line in groups[key]:
            if _accepted(line):
                rec = line.ljust(17)
                a = _amount(rec[7:10], rec[10:17])
                bal += a if rec[6] == "C" else -a
        if abs(bal) > MAX_BAL:
            lines = [l for l in lines if not (_accepted(l)
                                              and l.ljust(17)[:6] == key)]
    return lines


def make_cases(seed):
    rng = random.Random(seed)
    files = [
        # the visible examples
        ["ACME01C0020000999", "ACME01C0010001250", "BETA02C0010010000",
         "BETA02R0030005000", "GAMA03C0010000020"],
        # empty input, only rejects
        [], ["", "XXXXXXZ0010000100"],
    ]
    for _ in range(25):
        files.append(_keep_in_range(make_file(rng)))
    return files


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
        shutil.copyfile(source, os.path.join(room, "invtot.cbl"))
        kwargs, pw = _demote(sandbox_user)
        if pw:
            os.chown(room, pw.pw_uid, pw.pw_gid)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": room,
               "TMPDIR": room}
        try:
            comp = subprocess.run(["cobc", "-x", "-o", "invtot",
                                   "invtot.cbl"], cwd=room, env=env,
                                  capture_output=True, text=True,
                                  timeout=COMPILE_TIMEOUT, **kwargs)
        except subprocess.TimeoutExpired:
            return {"reward": 0.0, "error": "compile timeout"}
        if comp.returncode != 0:
            return {"reward": 0.0,
                    "error": "compile failed: " + comp.stderr[-1500:]}

        if seed is None:
            seed = int.from_bytes(os.urandom(8), "big")
        files = make_cases(seed)
        wrong, lines_checked = [], 0
        for i, lines in enumerate(files):
            want = reference(lines)
            lines_checked += len(want)
            try:
                run = subprocess.run(
                    [os.path.join(room, "invtot")], cwd=room, env=env,
                    input="".join(l + "\n" for l in lines),
                    capture_output=True, text=True, timeout=RUN_TIMEOUT,
                    **kwargs)
                got = [l.rstrip() for l in run.stdout.splitlines()]
            except subprocess.TimeoutExpired:
                got = ["<timeout>"]
            except UnicodeDecodeError:
                got = ["<non-text output>"]
            if got != want:
                first = next((j for j in range(max(len(got), len(want)))
                              if j >= len(got) or j >= len(want)
                              or got[j] != want[j]), 0)
                wrong.append({"file": i, "line": first,
                              "expected": want[first] if first < len(want)
                              else "<end>",
                              "got": got[first] if first < len(got)
                              else "<end>"})
        return {"reward": 1.0 if not wrong else 0.0, "seed": seed,
                "cases": len(files), "passed": len(files) - len(wrong),
                "output_lines": lines_checked, "first_failures": wrong[:8]}
    finally:
        shutil.rmtree(room, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/app/invtot.cbl")
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
