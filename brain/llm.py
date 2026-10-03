"""Optional banter layer: rewrites the template argument in the files' voices.

LLM_MODE = template | mock | groq | gemini   (brain/.env, default template)
ground.py owns the facts; the LLM only picks words. validator.py checks the result.
"""
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

from members import FILE_TO_UID, FILES

load_dotenv(Path(__file__).with_name(".env"))

TIMEOUT = 8
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(RuntimeError):
    pass


def mode():
    return os.environ.get("LLM_MODE", "template").strip().lower() or "template"


# ---------- prompt ----------

SYSTEM = """You write a short group chat where source files of a repo argue about who broke the build.
Reply with JSON only: {"messages":[{"speaker":"<file>.py","text":"..."}]}

Hard rules:
- 3 to 5 messages. Each under 160 characters. Casual group-chat tone, at most 1 emoji per message.
- Speakers must be files from the member list. Never invent other files.
- Facts are fixed. Never change the culprit, line, code or commit.
- Only the CULPRIT may write a line number (like L6), code, backticks or a commit hash. It speaks LAST and
  confesses with exactly "L<line>", the code_fragment and the short commit hash.
- The words commit, changed, edited, newer, pushed are ONLY for files whose role allows talking about their changes.
  Everyone else must avoid those words entirely.
- Mention other files as "@name.py", and only mention the culprit or a file you import.
- Each speaker may only make the claims its role allows. No other factual claims."""


def roles(facts):
    culprit = facts["culprit"]
    changed = set(facts.get("changed_files", []))
    newer = {c["file"] for c in facts.get("changed_not_run", []) if c["commit_time"] > facts["commit_time"]}
    imports = facts.get("imports", {})
    out = {}
    for m in FILES:
        f, claims = m["file"], []
        if f == culprit:
            claims.append(f'CULPRIT. speaks last. must include "L{facts["line"]}", "{facts["code_fragment"]}" '
                          f'and "{facts["commit"]}" ("{facts["summary"]}") and admit it'
                          if facts.get("line") else
                          f'CULPRIT. speaks last. must include commit "{facts["commit"]}" ("{facts["summary"]}")')
        else:
            if f in facts.get("suspects", []) and culprit in imports.get(f, []):
                claims.append(f"may say it only calls @{culprit}")
            if f in newer:
                claims.append("may say its commit is newer than the culprit's and the failing test never ran its changes")
            if f in facts.get("suspects", []) and f not in changed:
                claims.append("may say it ran in the test but its lines are untouched since green "
                              "(do NOT use the words commit/changed/edited/newer/pushed)")
            if not claims:
                claims.append("bystander: may only tease, no factual claims "
                              "(do NOT use the words commit/changed/edited/newer/pushed)")
        out[f] = {"persona": m["persona"], "role": "; ".join(claims)}
    return out


def user_prompt(facts, hint=None):
    keep = ("culprit", "line", "code", "code_fragment", "commit", "summary", "failing_test",
            "suspects", "changed_files", "bystanders", "imports")
    payload = {"facts": {k: facts.get(k) for k in keep}, "members": roles(facts)}
    text = "Write the chat as JSON. Input:\n" + json.dumps(payload, indent=1, ensure_ascii=False)
    if hint:
        text += f"\n\nYour previous answer was rejected: {hint}. Fix that."
    return text


# ---------- providers ----------

def _parse(content):
    try:
        data = json.loads(content)
    except (TypeError, ValueError) as e:
        raise LLMError(f"not JSON: {e}")
    msgs = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(msgs, list):
        raise LLMError("JSON has no messages list")
    return msgs


def _groq(facts, hint):
    model = os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user_prompt(facts, hint)}],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        "max_completion_tokens": 1500,
    }
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    r = httpx.post(GROQ_URL, json=body, timeout=TIMEOUT,
                   headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
    if r.status_code >= 400:
        raise LLMError(f"groq {r.status_code}: {r.text[:200]}")
    return _parse(r.json()["choices"][0]["message"]["content"])


def _gemini(facts, hint):
    model = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt(facts, hint)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }
    r = httpx.post(GEMINI_URL.format(model=model), json=body, timeout=TIMEOUT,
                   headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    if r.status_code >= 400:
        raise LLMError(f"gemini {r.status_code}: {r.text[:200]}")
    try:
        content = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"gemini: no text in response ({e})")
    return _parse(content)


# Canned outputs for the fixture (utils.py L6 .strip().lower() 4278cfe). No network.
CONFESS = {"speaker": "utils.py",
           "text": "...ok fine. L6 `.strip().lower()` in 4278cfe was me. I was just trying to help 😬"}
MOCKS = {
    "good": [
        {"speaker": "auth.py", "text": "don't look at me. I only call @utils.py and I check everything twice 🙄"},
        {"speaker": "cart.py", "text": "my commit is newer and the failing test never ran a single line of it 💅"},
        {"speaker": "db.py", "text": "I ran in that test. my lines are untouched since green. ask @utils.py"},
        CONFESS,
    ],
    "wrong_line": [
        {"speaker": "auth.py", "text": "I only call @utils.py 🙄"},
        {"speaker": "db.py", "text": "untouched since green, just tired"},
        {"speaker": "utils.py", "text": "ok it was me, L7 `.strip().lower()` in 4278cfe 😬"},
    ],
    "hash_leak": [
        {"speaker": "auth.py", "text": "pretty sure 4278cfe did it, I only call @utils.py"},
        {"speaker": "db.py", "text": "untouched since green"},
        CONFESS,
    ],
    "fake_newer": [
        {"speaker": "auth.py", "text": "I only call @utils.py 🙄"},
        {"speaker": "db.py", "text": "my stuff is newer than yours, wasn't me"},
        CONFESS,
    ],
    "non_member": [
        {"speaker": "auth.py", "text": "I only call @utils.py 🙄"},
        {"speaker": "cart.py", "text": "maybe payments.py did it, who knows 💅"},
        CONFESS,
    ],
    "wrong_last": [
        {"speaker": "auth.py", "text": "I only call @utils.py 🙄"},
        CONFESS,
        {"speaker": "api.py", "text": "zzz… whoever it was, keep it down"},
    ],
}
_mock_calls = 0


def _mock(facts, hint):
    """LLM_MOCK picks the case; a comma list ("fake_newer,good") is played one per call."""
    global _mock_calls
    cases = [c.strip() for c in os.environ.get("LLM_MOCK", "good").split(",")]
    case = cases[min(_mock_calls, len(cases) - 1)]
    _mock_calls += 1
    return json.loads(json.dumps(MOCKS[case]))


PROVIDERS = {"groq": _groq, "gemini": _gemini, "mock": _mock}


def banter(facts, hint=None, which=None):
    """One LLM call -> [{"speaker", "text"}]. Raises LLMError / httpx errors."""
    which = which or mode()
    if which not in PROVIDERS:
        raise LLMError(f"unknown LLM_MODE {which!r}")
    return PROVIDERS[which](facts, hint)


def to_lines(messages):
    """[{"speaker": "auth.py", ...}] -> [(uid, text)] with @file.py turned into CometChat mentions."""
    def mention(m):
        return f"<@uid:{FILE_TO_UID[m.group(1)]}>" if m.group(1) in FILE_TO_UID else m.group(0)
    return [(FILE_TO_UID[m["speaker"]], re.sub(r"@([\w-]+\.py)\b", mention, m["text"]))
            for m in messages]
