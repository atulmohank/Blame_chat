"""Grounded culprit finder: failing test x lines it ran x lines changed since green.

Usage: python ground.py                 (prints evidence log + facts JSON)
       python ground.py --force-bisect  (skip the trace intersection, use git bisect)
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import state
from members import FILES

BRAIN = str(state.BRAIN)
REPO = str(state.REPO)
MEMBER_FILES = [m["file"] for m in FILES]
PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def _env():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=BRAIN)
    env.pop("TRACE_OUT", None)
    return env


def run(args, timeout=20, env=None, check=True):
    r = subprocess.run(args, cwd=REPO, env=env or _env(), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{args[:3]} exited {r.returncode}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def git(*args):
    return run(["git", *args]).rstrip("\n")


# ---------- evidence gathering ----------

def trace_tests():
    """Run pytest with the trace plugin. Returns {nodeid: {"outcome", "lines": {(file, n)}}}."""
    fd, out = tempfile.mkstemp(suffix=".json", prefix="blamechat-trace-")
    os.close(fd)
    try:
        env = dict(_env(), TRACE_OUT=out)
        run(PYTEST + ["--tb=short", "-p", "trace_plugin"], env=env, check=False)
        with open(out, encoding="utf-8") as f:
            raw = json.load(f)
    finally:
        os.remove(out)
    if not raw:
        raise RuntimeError("trace plugin wrote no results")
    return {nid: {"outcome": r.get("outcome"), "lines": {tuple(x) for x in r.get("lines", [])}}
            for nid, r in raw.items()}


def plain_failing_tests():
    """Floor without the plugin: parse FAILED ids from pytest -rf."""
    out = run(PYTEST + ["-rf", "--tb=no"], check=False)
    return re.findall(r"^FAILED (\S+)", out, re.M), out


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_diff(diff):
    """{file: [(old_start, old_count, new_start, new_count), ...]}"""
    hunks, cur = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            cur = None if line == "+++ /dev/null" else line[6:]
            if cur:
                hunks.setdefault(cur, [])
        elif cur and (m := HUNK.match(line)):
            a, b, c, d = m.groups()
            hunks[cur].append((int(a), int(b or 1), int(c), int(d or 1)))
    return hunks


def changed_lines(hunks):
    return {f: {n for _, _, c, d in hs for n in range(c, c + d)} for f, hs in hunks.items()}


def last_commit(green, path):
    h, ct, s = git("log", "-1", "--format=%h|%ct|%s", f"{green}..HEAD", "--", path).split("|", 2)
    return {"commit": h, "commit_time": int(ct), "summary": s}


def blame(path, n):
    out = git("blame", "-L", f"{n},{n}", "--porcelain", "HEAD", "--", path).splitlines()
    info = {"commit": out[0].split()[0][:7]}
    for line in out[1:]:
        if line.startswith("\t"):
            info["code"] = line[1:]
        elif line.startswith("committer-time "):
            info["commit_time"] = int(line.split()[1])
        elif line.startswith("summary "):
            info["summary"] = line[len("summary "):]
    return info


def fragment(green, path, n, new_line, hunks):
    """Text inserted into line n vs. its last_green version, e.g. '.strip().lower()'."""
    try:
        old_src = git("show", f"{green}:{path}").splitlines()
    except RuntimeError:
        return new_line.strip()
    old = None
    for a, b, c, d in hunks.get(path, []):
        if c <= n < c + d and b:
            old_hunk = old_src[a - 1:a - 1 + b]
            k = n - c
            old = old_hunk[k] if k < len(old_hunk) else \
                (difflib.get_close_matches(new_line, old_hunk, 1, 0) or [None])[0]
    if not old:
        return new_line.strip()
    sm = difflib.SequenceMatcher(None, old, new_line, autojunk=False)
    added = "".join(new_line[j1:j2] for op, _, _, j1, j2 in sm.get_opcodes() if op in ("insert", "replace"))
    return added.strip() or new_line.strip()


IMPORT = re.compile(r"^(?:import|from)\s+(\w+)", re.M)


def imports_of_members():
    mods = {f[:-3]: f for f in MEMBER_FILES}
    result = {}
    for f in MEMBER_FILES:
        try:
            src = git("show", f"HEAD:{f}")
        except RuntimeError:
            continue
        result[f] = sorted({mods[m] for m in IMPORT.findall(src) if m in mods and mods[m] != f})
    return result


def bisect(green, failing_id):
    """git bisect run on one failing test. Always resets."""
    py = sys.executable.replace("\\", "/")
    try:
        git("bisect", "start", "HEAD", green)
        out = run(["git", "bisect", "run", py, "-m", "pytest", "-q", "-p", "no:cacheprovider", failing_id],
                  timeout=120)
    finally:
        run(["git", "bisect", "reset"], check=False)
    m = re.search(r"^([0-9a-f]{7,40}) is the first '?bad'? commit", out, re.M)
    if not m:
        raise RuntimeError("bisect found no first bad commit:\n" + out[-1500:])
    return m.group(1)[:7]


# ---------- the finder ----------

def find_culprit(force_bisect=False, evidence=None):
    ev = evidence if evidence is not None else []
    green = state.load()["last_green"]  # the ONLY state key read here

    traces, trace_error = None, None
    try:
        traces = trace_tests()
        failing = [nid for nid, r in traces.items() if r["outcome"] == "failed"]
        passed = sum(1 for r in traces.values() if r["outcome"] == "passed")
        ev.append(f"pytest: {len(failing)} failed, {passed} passed")
    except Exception as e:  # tracing broke: fall back to plain pytest
        trace_error = str(e)
        failing, _ = plain_failing_tests()
        ev.append(f"pytest: {len(failing)} failed (trace error: {trace_error})")
    if not failing:
        raise RuntimeError("no failing test - nothing to blame")

    executed = set().union(*(traces[f]["lines"] for f in failing)) if traces else set()
    hunks = parse_diff(run(["git", "diff", "-U0", green, "HEAD", "--", ".", ":!tests", ":!data"]))
    changed = changed_lines(hunks)
    commits = {f: last_commit(green, f) for f in changed}
    ev.append("changed since green: " + ", ".join(sorted(changed)))

    hits = sorted((f, n) for f, n in executed if n in changed.get(f, ()))
    suspects = [f for f in MEMBER_FILES if any(x[0] == f for x in executed)]

    facts = {"method": "trace", "failing_test": failing[0], "suspects": suspects, "accomplices": []}

    if hits and not force_bisect:
        ev.append("ran in failing test: " + ", ".join(f"{f} L{n}" for f, n in hits))
        blamed = [dict(blame(f, n), file=f, line=n) for f, n in hits]
        blamed.sort(key=lambda b: (b["commit_time"], b["file"], b["line"]))
        top = blamed[0]
        facts.update(culprit=top["file"], line=top["line"], code=top["code"],
                     code_fragment=fragment(green, top["file"], top["line"], top["code"], hunks),
                     commit=top["commit"], commit_time=top["commit_time"], summary=top["summary"])
        facts["accomplices"] = [{"file": b["file"], "line": b["line"], "commit": b["commit"]}
                                for b in blamed[1:] if (b["file"], b["line"]) != (top["file"], top["line"])]
        culprit_files = {b["file"] for b in blamed}
    else:
        reason = "forced" if force_bisect else ("trace error" if trace_error else "no changed line ran")
        ev.append(f"bisect ({reason}): {failing[0]}")
        h = bisect(green, failing[0])
        info = dict(zip(("commit", "commit_time", "summary"),
                        git("log", "-1", "--format=%h|%ct|%s", h).split("|", 2)))
        info["commit_time"] = int(info["commit_time"])
        shown = parse_diff(run(["git", "show", "-U0", "--format=", h, "--", ".", ":!tests"]))
        added = [(f, n) for f, ns in changed_lines(shown).items() for n in sorted(ns)]
        facts.update(method="bisect", code=None, code_fragment=None, line=None, **info)
        if len(added) == 1:
            f, n = added[0]
            code = git("show", f"{h}:{f}").splitlines()[n - 1]
            facts.update(culprit=f, line=n, code=code, code_fragment=fragment(green, f, n, code, hunks))
        else:
            facts["culprit"] = next(iter(shown), None)
        culprit_files = {facts["culprit"]}
        ev.append(f"bisect first bad commit: {h}")

    facts["changed_files"] = sorted(changed)
    facts["changed_not_run"] = [dict(commits[f], file=f) for f in sorted(changed) if f not in culprit_files]
    facts["bystanders"] = [f for f in MEMBER_FILES if f not in suspects and f != facts["culprit"]]
    facts["imports"] = imports_of_members()
    ev.append(f"blame {facts['commit']} '{facts['summary']}'")
    return facts


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    log = []
    try:
        result = find_culprit(force_bisect="--force-bisect" in sys.argv, evidence=log)
    finally:
        print("\n".join(log))
    print(json.dumps(result, indent=2, ensure_ascii=False))
