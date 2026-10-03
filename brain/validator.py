"""Gate for LLM banter: the wording may change, the facts may not."""
import re

from members import FILES

MEMBERS = [m["file"] for m in FILES]

LINE_REF = re.compile(r"\bL\d+\b")
HEX = re.compile(r"\b[0-9a-f]{7,}\b", re.I)
PY_FILE = re.compile(r"[\w./-]+\.py\b")
CLAIM = re.compile(r"\b(commit\w*|changed|edited|newer|pushed)\b", re.I)
NEWER = re.compile(r"\bnewer\b", re.I)


def mentioned_members(text):
    return {f for f in MEMBERS if re.search(r"(?<![\w.])@?" + re.escape(f) + r"\b", text)}


def validate(messages, facts):
    """-> (ok, reason)"""
    if not isinstance(messages, list) or not all(
            isinstance(m, dict) and isinstance(m.get("speaker"), str) and isinstance(m.get("text"), str)
            for m in messages):
        return False, "bad shape: need [{speaker, text}]"
    if not 3 <= len(messages) <= 5:
        return False, f"need 3-5 messages, got {len(messages)}"
    for m in messages:
        if m["speaker"] not in MEMBERS:
            return False, f"speaker {m['speaker']!r} is not a member"

    culprit, line, commit = facts["culprit"], facts.get("line"), facts["commit"]
    fragment = facts.get("code_fragment")
    last = messages[-1]
    if last["speaker"] != culprit:
        return False, f"last speaker is {last['speaker']}, culprit is {culprit}"
    if line and not re.search(rf"\bL{line}\b", last["text"]):
        return False, f"confession lacks L{line}"
    if commit not in last["text"]:
        return False, f"confession lacks commit {commit}"
    if fragment and fragment not in last["text"]:
        return False, f"confession lacks code fragment {fragment!r}"

    changed = set(facts.get("changed_files", []))
    newer_ok = {c["file"] for c in facts.get("changed_not_run", [])
                if c["commit_time"] > facts["commit_time"]}
    imports = facts.get("imports", {})

    for i, m in enumerate(messages):
        who, text = m["speaker"], m["text"]
        tag = f"msg {i + 1} ({who})"
        for f in PY_FILE.findall(text):
            if f.lstrip("@").split("/")[-1] not in MEMBERS:
                return False, f"{tag} names non-member file {f}"
        if m is not last:
            if LINE_REF.search(text):
                return False, f"{tag} has a line number"
            if HEX.search(text):
                return False, f"{tag} has a commit hash"
            if "`" in text:
                return False, f"{tag} has backticked code"
        if NEWER.search(text) and who not in newer_ok:
            return False, f"{tag} claims a newer commit it doesn't have"
        if CLAIM.search(text) and who not in changed:
            return False, f"{tag} talks about changes but isn't in changed_files"
        for f in mentioned_members(text) - {who}:
            if f != culprit and f not in imports.get(who, []):
                return False, f"{tag} mentions {f}, which is neither the culprit nor an import"
    return True, "ok"
