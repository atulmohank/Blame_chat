"""pytest plugin: which repo lines did each test execute? Load with -p trace_plugin."""
import json
import os
import sys

import pytest

REPO = os.path.realpath(os.getcwd())
TESTS = os.path.join(REPO, "tests") + os.sep
_results = {}


def _rel(filename):
    path = os.path.realpath(filename)
    if not path.startswith(REPO + os.sep) or path.startswith(TESTS):
        return None
    return os.path.relpath(path, REPO).replace(os.sep, "/")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    lines = set()

    def tracer(frame, event, arg):
        rel = _rel(frame.f_code.co_filename)
        if rel is None:
            return None
        if event == "line":
            lines.add((rel, frame.f_lineno))
        return tracer

    sys.settrace(tracer)
    try:
        yield
    finally:
        sys.settrace(None)
        _results.setdefault(item.nodeid, {})["lines"] = sorted(lines)


def pytest_runtest_logreport(report):
    if report.when == "call":
        _results.setdefault(report.nodeid, {"lines": []})["outcome"] = report.outcome


def pytest_sessionfinish(session):
    out = os.environ.get("TRACE_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(_results, f)
