"""BlameChat brain. Run: uvicorn server:app --port 8787  (from the brain/ folder)"""
import asyncio
import random
import re
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import state
from cometchat import send_text
from ground import MEMBER_FILES, find_culprit, git, imports_of_members, parse_diff, run, trace_tests
from template import build_lines, commit_lines

app = FastAPI(title="BlameChat brain")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


class Ask(BaseModel):
    text: str
    guid: str | None = None


@app.get("/session")
def session():
    s = state.load()
    return {"guid": s.get("guid"), "take": s.get("take"), "uid": "atul"}


# One script at a time: an /ask or /commit that arrives mid-script waits its turn.
SCRIPT_LOCK = asyncio.Lock()


async def post_script(guid, lines):
    """lines = [(uid, text), ...], posted with human-ish gaps."""
    for i, (uid, text) in enumerate(lines):
        if i:
            await asyncio.sleep(random.uniform(1.2, 2.5))
        await asyncio.to_thread(send_text, uid, guid, text)
        log(f"posted {uid}: {text}")


BLAME = re.compile(
    r"\b(broke|break|breaks|broken|blame|bugs?|buggy|fail|fails|failed|failing|guilty|culprit"
    r"|fault|responsible|trouble\s*maker|who\s+did|did\s+this|what\s+happened|not\s+working"
    r"|doesn['’]?t\s+work)\b",
    re.I,
)


def is_blame(text):
    return bool(BLAME.search(text))


async def ground_and_post(guid):
    async with SCRIPT_LOCK:
        log("grounding…")
        evidence = []
        try:
            facts = await asyncio.to_thread(find_culprit, evidence=evidence)
        except Exception as e:
            for line in evidence:
                log(line)
            log(f"grounding failed: {e}")
            return
        for line in evidence:
            log(line)
        log("asking the files…")
        await post_script(guid, build_lines(facts))


async def locked_script(guid, lines):
    async with SCRIPT_LOCK:
        await post_script(guid, lines)


@app.post("/ask")
async def ask(body: Ask):
    guid = body.guid or state.load().get("guid")
    log(f"atul asked: {body.text!r} (group {guid})")
    if is_blame(body.text):
        asyncio.create_task(ground_and_post(guid))
        return {"ok": True, "grounding": True}
    # Not a blame question: db.py hints at what to ask.
    lines = [("db_py", "db.py here 😴 if something's broken, ask us who broke it.")]
    asyncio.create_task(locked_script(guid, lines))
    return {"ok": True, "queued": len(lines)}


def member_changes(commit):
    """{member file: [new-side changed line numbers]} for one commit."""
    hunks = parse_diff(run(["git", "diff-tree", "-U0", "--no-commit-id", "-r", commit]))
    changed = {}
    for f, hs in hunks.items():
        if f in MEMBER_FILES:
            added = {n for _, _, c, d in hs for n in range(c, c + d)}
            changed[f] = sorted(added or {c for _, _, c, _ in hs})  # pure deletions: where they were
    return changed


def test_counts():
    """Same pytest run as ground.py: (failed, passed)."""
    outcomes = [r["outcome"] for r in trace_tests().values()]
    return outcomes.count("failed"), outcomes.count("passed")


async def react_to_commit(commit):
    async with SCRIPT_LOCK:
        try:
            subject = await asyncio.to_thread(git, "log", "-1", "--format=%s", commit)
            log(f"commit detected {commit} '{subject}'")
            changed = await asyncio.to_thread(member_changes, commit)
            if not changed:
                log("commit touched no members, staying quiet")
                return
            failed, passed = await asyncio.to_thread(test_counts)
            log(f"pytest: {failed} failed, {passed} passed")
            green, culprit = failed == 0, None
            if green:
                s = state.load()
                s["last_green"] = commit
                state.save(s)
                log(f"last_green → {commit}")
            else:
                facts = await asyncio.to_thread(find_culprit)
                culprit = facts["culprit"]
                log(f"still red: {culprit} L{facts['line']} ({facts['commit']})")
            imports = await asyncio.to_thread(imports_of_members)
            guid = state.load().get("guid")
            await post_script(guid, commit_lines(changed, green, imports, culprit))
        except Exception as e:
            log(f"commit reaction failed: {e}")


@app.post("/commit")
async def commit():
    # Pin the hash now, so a queued reaction still talks about the right commit.
    head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
    asyncio.create_task(react_to_commit(head))
    return {"ok": True, "commit": head}
