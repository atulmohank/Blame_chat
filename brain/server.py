"""BlameChat brain. Run: uvicorn server:app --port 8787  (from the brain/ folder)"""
import asyncio
import random
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import events
import llm
import state
from cometchat import send_text
from ground import MEMBER_FILES, failures, find_culprit, git, imports_of_members, parse_diff, run, trace_tests
from members import FILE_TO_UID
from template import build_lines, chat_fallback, commit_lines, error_lines, fix_lines, green_line
from validator import validate, validate_chat

@asynccontextmanager
async def lifespan(_app):
    asyncio.create_task(refresh_status("startup"))
    yield


app = FastAPI(title="BlameChat brain", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def log(msg, kind="log", refs=None):
    """Print the step, then publish it on /events with the same timestamp and its facts."""
    now = datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] {msg}", flush=True)
    events.emit(now, kind, msg, refs)


class Ask(BaseModel):
    text: str
    guid: str | None = None


@app.get("/session")
def session():
    s = state.load()
    return {"guid": s.get("guid"), "take": s.get("take"), "uid": "atul"}


# One script at a time: an /ask or /commit that arrives mid-script waits its turn.
# Every pytest run and every git bisect in this process happens under this lock.
SCRIPT_LOCK = asyncio.Lock()

# Last pytest result, cached. GET /status only reads it; it never runs pytest.
STATUS = {"state": "unknown", "failed": None, "passed": None, "failing_test": None,
          "head": None, "source": None, "checked_at": None}


def record_status(failed, passed, source, head, failing_test=None):
    STATUS.update(state="failing" if failed else "passing", failed=failed, passed=passed,
                  failing_test=failing_test, head=head, source=source,
                  checked_at=datetime.now().strftime("%H:%M:%S"))
    log(f"status <- {STATUS['state']} ({failed} failed, {passed} passed) [{source} @ {head}]", "status", dict(STATUS))


def bisect_in_progress():
    """A git bisect started outside this process (python ground.py --force-bisect)."""
    return (state.REPO / ".git" / "BISECT_START").exists()


async def refresh_status(source):
    """Run pytest once under the lock and cache the result (startup only)."""
    async with SCRIPT_LOCK:
        if bisect_in_progress():
            log(f"status: skipped {source} check, a git bisect is in progress", "status")
            return
        try:
            head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
            failed, passed, fails = await asyncio.to_thread(failures)
        except Exception as e:
            log(f"status check failed: {e}", "error")
            return
        record_status(failed, passed, source, head, fails[0]["test"] if fails else None)


@app.get("/status")
def status():
    """The cached result. If tinyshop's HEAD moved since that run (reset_take, a commit not yet
    reacted to), the cache no longer describes the code, so report unknown rather than stale."""
    try:
        head = git("rev-parse", "--short", "HEAD")
    except Exception:
        head = None
    if STATUS["head"] and head != STATUS["head"]:
        return {**STATUS, "state": "unknown", "stale": True, "current_head": head}
    return STATUS


@app.get("/events")
async def event_stream():
    """SSE: a "hello" with the take and tinyshop HEAD, this take's history, "replayed", then live steps."""
    q, history = events.subscribe()
    try:
        head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
    except Exception:
        head = None
    hello = {"take": events.TAKE, "head": head, "last_green": state.load().get("last_green")}

    async def stream():
        try:
            yield events.sse(None, hello, "hello")
            for seq, event in history:
                yield events.sse(seq, event)
            yield events.sse(None, {"count": len(history)}, "replayed")
            while True:
                seq, event = await q.get()
                yield events.sse(seq, event)
        finally:
            events.unsubscribe(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


UID_TO_FILE = {uid: f for f, uid in FILE_TO_UID.items()}
HISTORY = defaultdict(lambda: deque(maxlen=8))   # guid -> last 8 {"who", "text"} (atul + files)
FACTS = {}                                        # guid -> (HEAD, facts) for grounded follow-ups


def remember(guid, who, text):
    text = re.sub(r"<@uid:(\w+)>", lambda m: "@" + UID_TO_FILE.get(m.group(1), m.group(1)), text)
    HISTORY[guid].append({"who": who, "text": text})


async def post_script(guid, lines):
    """lines = [(uid, text) or (uid, text, metadata), ...], posted with human-ish gaps."""
    for i, (uid, text, *meta) in enumerate(lines):
        if i:
            await asyncio.sleep(random.uniform(1.2, 2.5))
        sent = await asyncio.to_thread(send_text, uid, guid, text, meta[0] if meta else None)
        remember(guid, UID_TO_FILE.get(uid, uid), text)
        log(f"posted {uid}: {text}", "posted", {
            "id": (sent or {}).get("id") if isinstance(sent, dict) else None,  # CometChat message id
            "uid": uid, "file": UID_TO_FILE.get(uid), "guid": guid, "confession": bool(meta)})


BLAME = re.compile(
    r"\b(broke|break|breaks|broken|blame|bugs?|buggy|fail|fails|failed|failing|guilty|culprit"
    r"|fault|responsible|trouble\s*maker|who\s+did|did\s+this|what\s+happened|not\s+working"
    r"|doesn['’]?t\s+work)\b",
    re.I,
)


def is_blame(text):
    return bool(BLAME.search(text))


ERROR_PHRASE = re.compile(r"\b(what\s+failed|which\s+test|traceback)\b", re.I)
FIX = re.compile(r"\b(fix|solve|solution|repair|how\s+do\s+i|what\s+now|undo)\b", re.I)
ERROR = re.compile(r"\b(error|what['’]?s\s+wrong|why)\b", re.I)
NAMED = re.compile(r"@?\b(" + "|".join(re.escape(f[:-3]) for f in MEMBER_FILES) + r")(?:\.py)?\b", re.I)


def intent(text):
    """blame | fix | error | chat. Error phrases first ("what failed" also says "failed")."""
    if ERROR_PHRASE.search(text):
        return "error"
    if FIX.search(text):
        return "fix"
    if is_blame(text):
        return "blame"
    if ERROR.search(text):
        return "error"
    return "chat"


async def grounded_facts(guid, evidence=None):
    """Facts for this take, recomputed only when HEAD moved."""
    head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
    cached = FACTS.get(guid)
    if evidence is None and cached and cached[0] == head:
        return cached[1]
    facts = await asyncio.to_thread(find_culprit, evidence=evidence)
    FACTS[guid] = (head, facts)
    return facts


PYTEST_EVIDENCE = re.compile(r"^pytest: (\d+) failed(?:, (\d+) passed)?")
EVIDENCE = {"trace": ["pytest trace", "git diff", "git blame"], "bisect": ["pytest", "git bisect"]}


def confession_metadata(facts):
    """The computed facts behind the confession, for the UI's receipt card (never parsed from prose)."""
    return {"blamechat": {
        "kind": "confession",
        "file": facts["culprit"],
        "line": facts.get("line"),
        "fragment": facts.get("code_fragment"),
        "commit": facts["commit"],
        "summary": facts.get("summary"),
        "failing_test": facts.get("failing_test"),
        "method": facts["method"],
        "evidence": EVIDENCE.get(facts["method"], []),
    }}


def attach_confession(lines, facts):
    """The culprit speaks last (template and LLM rules); its line carries the facts."""
    if lines and lines[-1][0] == FILE_TO_UID.get(facts.get("culprit")):
        uid, text = lines[-1][:2]
        lines = [*lines[:-1], (uid, text, confession_metadata(facts))]
    return lines


def commit_position(commit):
    """Where a commit sits in last_green..HEAD, oldest first: {"index", "of", "is_head"} from git."""
    green = state.load()["last_green"]
    revs = git("rev-list", "--reverse", f"{green}..HEAD").split()
    index = next((i for i, rev in enumerate(revs, 1) if rev.startswith(commit)), None)
    if not index:
        return {}
    return {"index": index, "of": len(revs), "is_head": index == len(revs)}


def evidence_event(line, facts, extra=None):
    """(kind, refs) for one ground.py evidence line; refs are the facts that line summarises."""
    extra = extra or {}
    if m := PYTEST_EVIDENCE.match(line):
        return "pytest", {"failed": int(m[1]), "passed": int(m[2]) if m[2] is not None else None,
                          "failing_test": facts.get("failing_test")}
    if line.startswith("changed since green"):
        return "changed", {"files": facts.get("changed_files", []), "last_green": extra.get("last_green")}
    if line.startswith("ran in failing test"):
        hits = [{"file": facts["culprit"], "line": facts.get("line"), "commit": facts["commit"]}] if facts.get("culprit") else []
        return "ran", {"hits": hits + facts.get("accomplices", []), "failing_test": facts.get("failing_test")}
    if line.startswith("bisect first bad commit"):
        return "bisect", {"commit": facts.get("commit")}
    if line.startswith("bisect"):
        return "bisect", {"failing_test": facts.get("failing_test")}
    if line.startswith("blame "):
        return "blame", {"file": facts.get("culprit"), "line": facts.get("line"), "commit": facts.get("commit"),
                         "summary": facts.get("summary"), "fragment": facts.get("code_fragment"),
                         "method": facts.get("method"), **extra.get("position", {})}
    return "log", {}


def room_from_facts(facts):
    """Each member's part in the current failure, straight from find_culprit's facts."""
    changed_not_run = {c["file"]: c for c in facts.get("changed_not_run", [])}
    accomplices = {a["file"]: a for a in facts.get("accomplices", [])}
    members = []
    for f in MEMBER_FILES:
        if f == facts.get("culprit"):
            m = {"status": "culprit", "line": facts.get("line"), "commit": facts.get("commit")}
        elif f in changed_not_run:
            m = {"status": "changed-not-run", "commit": changed_not_run[f]["commit"]}
        elif f in accomplices:
            m = {"status": "ran", "line": accomplices[f]["line"], "commit": accomplices[f]["commit"]}
        elif f in facts.get("suspects", []):
            m = {"status": "ran"}
        elif f in facts.get("bystanders", []):
            m = {"status": "bystander"}
        else:
            m = {"status": "unknown"}
        members.append({"file": f, **m})
    return members


ROOM_TEXT = {"culprit": "culprit", "changed-not-run": "changed, never ran", "ran": "ran in test",
             "bystander": "bystander", "green": "green", "unknown": "unknown"}


def publish_room(members, source):
    """Emit a "room" event only when some member's status changed (no terminal line)."""
    last = next((e for _, e in reversed(events.HISTORY) if e["kind"] == "room"), None)
    if last and last["refs"]["members"] == members:
        return
    text = "room: " + ", ".join(f"{m['file']} {ROOM_TEXT[m['status']]}" for m in members)
    events.emit(datetime.now(), "room", text, {"members": members, "source": source})


async def ground_and_post(guid):
    async with SCRIPT_LOCK:
        log("grounding…", "grounding")
        evidence = []
        try:
            head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
            facts = await grounded_facts(guid, evidence)
        except Exception as e:
            for line in evidence:
                log(line, *evidence_event(line, {}))
            log(f"grounding failed: {e}", "error")
            return
        extra = {"last_green": state.load().get("last_green")}
        try:
            extra["position"] = await asyncio.to_thread(commit_position, facts["commit"])
        except Exception:
            pass  # only decorates the blame step
        for line in evidence:
            log(line, *evidence_event(line, facts, extra))
        publish_room(room_from_facts(facts), "ask")
        counts = next((m for m in map(PYTEST_EVIDENCE.match, evidence) if m), None)
        if counts:  # pytest ran this time (cached facts skip it and leave the status alone)
            passed = int(counts[2]) if counts[2] is not None else None
            record_status(int(counts[1]), passed, "ask", head, facts.get("failing_test"))
        lines = build_lines(facts)
        if llm.mode() != "template":
            lines = await banter_lines(facts) or lines
        lines = attach_confession(lines, facts)
        log("asking the files…", "asking", {"speakers": [UID_TO_FILE.get(l[0], l[0]) for l in lines],
                                            "method": facts.get("method")})
        await post_script(guid, lines)


async def banter_lines(facts):
    """LLM wording for the same facts: validate, retry once, else None (-> template)."""
    which = llm.mode()
    log(f"llm: {which} …", "llm", {"mode": which})
    hint = None
    for attempt in (1, 2):
        t0 = time.perf_counter()
        try:
            messages = await asyncio.to_thread(llm.banter, facts, hint)
        except Exception as e:
            log(f"llm: attempt {attempt} error: {e}", "llm", {"attempt": attempt, "ok": False})
            break
        ok, reason = validate(messages, facts)
        if ok:
            log(f"llm: attempt {attempt} valid ({time.perf_counter() - t0:.1f}s, {len(messages)} messages)",
                "llm", {"attempt": attempt, "ok": True, "messages": len(messages)})
            return llm.to_lines(messages)
        log(f"llm: attempt {attempt} invalid: {reason}", "llm", {"attempt": attempt, "ok": False})
        hint = reason
    log("→ template fallback", "llm", {"fallback": "template"})
    return None


async def fix_and_post(guid):
    """Grounded: the culprit spells out the fix computed by ground.py."""
    async with SCRIPT_LOCK:
        try:
            head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
            failed, passed, fails = await asyncio.to_thread(failures)
            log(f"pytest: {failed} failed, {passed} passed", "pytest", {
                "failed": failed, "passed": passed, "failing_test": fails[0]["test"] if fails else None, "head": head})
            record_status(failed, passed, "ask", head, fails[0]["test"] if fails else None)
            cached = FACTS.get(guid)
            if not failed:
                speaker = cached[1]["culprit"] if cached else "db.py"
                lines = green_line(speaker, "tests are already green ✅ nothing to fix")
            else:
                facts = await grounded_facts(guid)
                log(f"fix: {facts['culprit']} L{facts['line']} remove {facts['code_fragment']!r}", "fix", {
                    "file": facts["culprit"], "line": facts.get("line"), "fragment": facts.get("code_fragment"),
                    "commit": facts.get("commit")})
                publish_room(room_from_facts(facts), "ask")
                lines = fix_lines(facts)
        except Exception as e:
            log(f"fix failed: {e}", "error")
            return
        await post_script(guid, lines)


def call_owner(source, facts=None):
    """Member whose function the failing assertion calls (auth.login -> auth.py)."""
    for mod in re.findall(r"\b(\w+)\.\w+\(", source or ""):
        if f"{mod}.py" in MEMBER_FILES:
            return f"{mod}.py"
    return ((facts or {}).get("suspects") or ["auth.py"])[0]


async def error_and_post(guid):
    """Grounded: re-run pytest, read out the failing test and its assertion."""
    async with SCRIPT_LOCK:
        try:
            head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
            failed, passed, fails = await asyncio.to_thread(failures)
        except Exception as e:
            log(f"error check failed: {e}", "error")
            return
        log(f"pytest: {failed} failed, {passed} passed", "pytest", {
            "failed": failed, "passed": passed, "failing_test": fails[0]["test"] if fails else None, "head": head})
        record_status(failed, passed, "ask", head, fails[0]["test"] if fails else None)
        if not failed or not fails:
            await post_script(guid, green_line("auth.py"))
            return
        cached = FACTS.get(guid)
        owner = call_owner(fails[0]["source"], cached[1] if cached else None)
        log(f"failing: {fails[0]['test']} at {fails[0]['where']} (owner {owner})", "failing", {
            "test": fails[0]["test"], "where": fails[0]["where"], "owner": owner})
        await post_script(guid, error_lines(fails[0], owner))


async def chat_and_post(guid, history, text):
    """Free chat: personality only. LLM -> strict chat validator -> retry once -> persona pool."""
    async with SCRIPT_LOCK:
        m = NAMED.search(text)
        addressed = f"{m.group(1).lower()}.py" if m else None
        lines = None
        if llm.mode() != "template":
            log(f"llm: {llm.mode()} chat …" + (f" (addressed {addressed})" if addressed else ""), "llm",
                {"mode": llm.mode(), "addressed": addressed})
            hint = None
            for attempt in (1, 2):
                t0 = time.perf_counter()
                try:
                    messages = await asyncio.to_thread(llm.chat, history, text, addressed, hint)
                except Exception as e:
                    log(f"llm: attempt {attempt} error: {e}", "llm", {"attempt": attempt, "ok": False})
                    break
                ok, reason = validate_chat(messages, first=addressed)
                if ok:
                    log(f"llm: attempt {attempt} valid ({time.perf_counter() - t0:.1f}s, {len(messages)} messages)",
                        "llm", {"attempt": attempt, "ok": True, "messages": len(messages)})
                    lines = llm.to_lines(messages)
                    break
                log(f"llm: attempt {attempt} invalid: {reason}", "llm", {"attempt": attempt, "ok": False})
                hint = reason
            if lines is None:
                log("→ template fallback", "llm", {"fallback": "template"})
        await post_script(guid, lines or chat_fallback(addressed))


@app.post("/ask")
async def ask(body: Ask):
    guid = body.guid or state.load().get("guid")
    kind = intent(body.text)
    log(f"atul asked: {body.text!r} (group {guid}) → {kind}", "asked", {"text": body.text, "intent": kind, "guid": guid})
    history = list(HISTORY[guid])
    remember(guid, "atul", body.text)
    if kind == "blame":
        asyncio.create_task(ground_and_post(guid))
        return {"ok": True, "grounding": True}
    if kind == "fix":
        asyncio.create_task(fix_and_post(guid))
    elif kind == "error":
        asyncio.create_task(error_and_post(guid))
    else:
        asyncio.create_task(chat_and_post(guid, history, body.text))
    return {"ok": True, "intent": kind}


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
            log(f"commit detected {commit} '{subject}'", "commit", {"commit": commit, "subject": subject})
            changed = await asyncio.to_thread(member_changes, commit)
            if not changed:
                log("commit touched no members, staying quiet", "commit", {"commit": commit, "changed": {}})
                return
            failed, passed = await asyncio.to_thread(test_counts)
            log(f"pytest: {failed} failed, {passed} passed", "pytest",
                {"failed": failed, "passed": passed, "head": commit, "changed": changed})
            record_status(failed, passed, "commit", commit)
            green, culprit = failed == 0, None
            if green:
                s = state.load()
                s["last_green"] = commit
                state.save(s)
                log(f"last_green → {commit}", "last_green", {"commit": commit})
                publish_room([{"file": f, "status": "green", "commit": commit} for f in MEMBER_FILES], "commit")
            else:
                facts = await asyncio.to_thread(find_culprit)
                culprit = facts["culprit"]
                log(f"still red: {culprit} L{facts['line']} ({facts['commit']})", "still_red",
                    {"file": culprit, "line": facts.get("line"), "commit": facts.get("commit")})
                publish_room(room_from_facts(facts), "commit")
            imports = await asyncio.to_thread(imports_of_members)
            guid = state.load().get("guid")
            await post_script(guid, commit_lines(changed, green, imports, culprit))
        except Exception as e:
            log(f"commit reaction failed: {e}", "error")


@app.post("/commit")
async def commit():
    # Pin the hash now, so a queued reaction still talks about the right commit.
    head = await asyncio.to_thread(git, "rev-parse", "--short", "HEAD")
    asyncio.create_task(react_to_commit(head))
    return {"ok": True, "commit": head}
