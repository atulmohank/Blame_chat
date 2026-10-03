"""Unit tests for the brain's /commit path and the cached /status. Run: python -m pytest test_server.py

No CometChat, git or pytest subprocess runs here: those calls are replaced with fakes.
TestClient is used without `with`, so the startup status check (a real pytest run) does not fire.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture(autouse=True)
def fresh_status(monkeypatch):
    monkeypatch.setattr(server, "STATUS", {**server.STATUS, "state": "unknown", "failed": None, "passed": None})
    monkeypatch.setattr(server.random, "uniform", lambda a, b: 0)


def test_commit_endpoint_pins_head_and_returns_immediately(monkeypatch):
    seen = []

    async def fake_react(commit):
        seen.append(commit)

    monkeypatch.setattr(server, "git", lambda *args: "abc1234")
    monkeypatch.setattr(server, "react_to_commit", fake_react)
    res = TestClient(server.app).post("/commit")
    assert res.json() == {"ok": True, "commit": "abc1234"}
    assert seen == ["abc1234"]


def _fake_commit_world(monkeypatch, failed, passed):
    sent, saved, locked_during_pytest = [], [], []

    def fake_counts():
        locked_during_pytest.append(server.SCRIPT_LOCK.locked())
        return failed, passed

    monkeypatch.setattr(server, "git", lambda *args: "fix hash")
    monkeypatch.setattr(server, "member_changes", lambda commit: {"utils.py": [6]})
    monkeypatch.setattr(server, "test_counts", fake_counts)
    monkeypatch.setattr(server, "imports_of_members", lambda: {"auth.py": ["utils.py"]})
    monkeypatch.setattr(server, "find_culprit", lambda: {"culprit": "utils.py", "line": 6, "commit": "abc1234"})
    monkeypatch.setattr(server, "send_text", lambda uid, guid, text, metadata=None: sent.append((uid, text, metadata)))
    monkeypatch.setattr(server.state, "load", lambda: {"guid": "repo-tinyshop-test", "last_green": "1bced6f"})
    monkeypatch.setattr(server.state, "save", lambda s: saved.append(s))
    return sent, saved, locked_during_pytest


def test_green_commit_caches_passing_status(monkeypatch):
    sent, saved, locked = _fake_commit_world(monkeypatch, failed=0, passed=5)
    asyncio.run(server.react_to_commit("abc1234"))

    assert locked == [True], "pytest must only run while SCRIPT_LOCK is held"
    assert server.STATUS["state"] == "passing"
    assert (server.STATUS["failed"], server.STATUS["passed"]) == (0, 5)
    assert (server.STATUS["source"], server.STATUS["head"]) == ("commit", "abc1234")
    assert saved and saved[-1]["last_green"] == "abc1234"
    assert ("utils_py", "someone rewrote L6 of me without asking 😤", None) in sent
    assert ("auth_py", "tests green ✅ apology accepted", None) in sent


def test_red_commit_caches_failing_status(monkeypatch):
    sent, saved, locked = _fake_commit_world(monkeypatch, failed=1, passed=4)
    asyncio.run(server.react_to_commit("abc1234"))

    assert locked == [True]
    assert server.STATUS["state"] == "failing"
    assert not saved, "last_green must not move on a red commit"
    assert sent[-1][:2] == ("utils_py", "still red. not done with me yet 😩")


def test_status_endpoint_only_reads_the_cache(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("GET /status must not run pytest")

    monkeypatch.setattr(server, "failures", boom)
    monkeypatch.setattr(server, "trace_tests", boom)
    monkeypatch.setattr(server, "test_counts", boom)
    monkeypatch.setattr(server, "git", lambda *args: "673b583")
    server.record_status(1, 4, "ask", "673b583", "tests/test_auth.py::test_login")
    body = TestClient(server.app).get("/status").json()
    assert body["state"] == "failing"
    assert body["failing_test"] == "tests/test_auth.py::test_login"


def test_status_is_unknown_once_head_moves(monkeypatch):
    server.record_status(0, 5, "commit", "fe12abc")
    monkeypatch.setattr(server, "git", lambda *args: "673b583")  # reset_take moved HEAD
    body = TestClient(server.app).get("/status").json()
    assert body["state"] == "unknown" and body["stale"] is True


def test_confession_carries_computed_facts_as_metadata():
    facts = {"culprit": "utils.py", "line": 6, "code_fragment": ".strip().lower()", "commit": "4278cfe",
             "summary": "refactor: normalize passwords", "failing_test": "tests/test_auth.py::test_login",
             "method": "trace"}
    lines = server.attach_confession([("auth_py", "not me"), ("utils_py", "...ok. that was me")], facts)
    assert lines[0] == ("auth_py", "not me")
    uid, _, meta = lines[-1]
    assert uid == "utils_py"
    assert meta["blamechat"]["kind"] == "confession"
    assert (meta["blamechat"]["file"], meta["blamechat"]["line"], meta["blamechat"]["commit"]) == ("utils.py", 6, "4278cfe")
    assert meta["blamechat"]["evidence"] == ["pytest trace", "git diff", "git blame"]


def test_no_metadata_when_culprit_does_not_speak_last():
    facts = {"culprit": "utils.py", "commit": "4278cfe", "method": "bisect"}
    lines = [("utils_py", "hmm"), ("auth_py", "not me")]
    assert server.attach_confession(lines, facts) == lines
