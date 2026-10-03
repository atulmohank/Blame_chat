"""Template argument: facts -> [(uid, text)]. A line is emitted only if its rule finds a file."""
import random

from members import FILE_TO_UID, FILES

ORDER = [m["file"] for m in FILES]

# CometChat mention syntax: "<@uid:UID>" in data.text (rest-api/messages/send-message).
# Flip to False if the UI shows it as raw text; then it falls back to "@utils.py".
USE_MENTIONS = True


def mention(file):
    return f"<@uid:{FILE_TO_UID[file]}>" if USE_MENTIONS else f"@{file}"


def build_lines(facts):
    culprit = facts["culprit"]
    suspects = facts.get("suspects", [])
    changed = facts.get("changed_files", [])
    imports = facts.get("imports", {})
    lines, used = [], {culprit}

    # 1 Caller: a suspect that imports the culprit.
    caller = next((f for f in ORDER if f in suspects and f not in used
                   and culprit in imports.get(f, [])), None)
    if caller:
        used.add(caller)
        lines.append((FILE_TO_UID[caller], f"not me, I just call {mention(culprit)} 🙄"))

    # 2 Alibi: changed but never ran, and its commit is newer than the culprit's.
    alibis = [c for c in facts.get("changed_not_run", [])
              if c["file"] in FILE_TO_UID and c["file"] not in suspects and c["file"] not in used
              and c["commit_time"] > facts["commit_time"]]
    if alibis:
        alibi = max(alibis, key=lambda c: c["commit_time"])["file"]
        used.add(alibi)
        lines.append((FILE_TO_UID[alibi],
                      "my commit's newer than yours and the failing test never ran a single changed line of me 💅"))

    # 3 Quiet suspect: ran in the test, untouched since green.
    quiet = next((f for f in ORDER if f in suspects and f not in used and f not in changed), None)
    if quiet:
        used.add(quiet)
        lines.append((FILE_TO_UID[quiet],
                      f"I ran during that test, but none of my lines changed since green. ask {mention(culprit)}."))

    # 4 Culprit confesses, always last.
    if facts.get("line"):
        text = (f"...ok. `{culprit}` L{facts['line']} `{facts['code_fragment']}`, "
                f"commit `{facts['commit']}` '{facts['summary']}'. that was me 😬")
    else:
        text = f"...ok. commit `{facts['commit']}` '{facts['summary']}' was me 😬"
    lines.append((FILE_TO_UID[culprit], text))
    return lines


def commit_lines(changed, green, imports, culprit=None):
    """Reactions to a new commit.

    changed: {member file: [new-side changed line numbers]}
    green:   did the tests pass after the commit?
    imports: {file: [member files it imports]} (ground.imports_of_members())
    culprit: file from find_culprit() when still red
    """
    lines = []

    # a) Every changed member complains, in members order.
    for f in ORDER:
        if changed.get(f):
            lines.append((FILE_TO_UID[f], f"someone rewrote L{min(changed[f])} of me without asking 😤"))

    # b) Green: the first member that imports a changed file accepts the apology.
    if green:
        forgiver = next((f for f in ORDER if any(c in imports.get(f, []) for c in changed)), None)
        if forgiver:
            lines.append((FILE_TO_UID[forgiver], "tests green ✅ apology accepted"))
    # c) Red: the culprit isn't done yet.
    elif culprit in FILE_TO_UID:
        lines.append((FILE_TO_UID[culprit], "still red. not done with me yet 😩"))
    return lines


# ---------- grounded follow-ups (facts only from ground.py / pytest) ----------

SUPPORT = {
    "auth.py": "fine. but i'm watching that diff 👀",
    "db.py": "do it. i'd like to sleep tonight 😴",
    "utils.py": "you got this!! 😊",
    "cart.py": "wow, a fix. groundbreaking 💅",
    "api.py": "wake me when it's green 😪",
}


def fix_lines(facts):
    """Culprit gives the exact fix; one other file cheers (no facts)."""
    culprit = facts["culprit"]
    if facts.get("line"):
        fix = (f"remove `{facts['code_fragment']}` from `{culprit}` L{facts['line']}, then commit. "
               "i'll behave 🙏")
    else:
        fix = f"revert commit `{facts['commit']}` ('{facts['summary']}'), then commit. i'll behave 🙏"
    lines = [(FILE_TO_UID[culprit], fix)]
    helper = next((f for f in ORDER if f in facts.get("suspects", []) and f != culprit), None) \
        or next(f for f in ORDER if f != culprit)
    lines.append((FILE_TO_UID[helper], SUPPORT[helper]))
    return lines


def green_line(speaker, text="all green right now ✅"):
    return [(FILE_TO_UID[speaker], text)]


def error_lines(fail, owner):
    """The file that owns the failing call reads the failure out."""
    text = f"failing: `{fail['test']}`"
    if fail.get("source"):
        text += f" → `{fail['source']}`"
    if fail.get("message"):
        text += f" → {fail['message']}"
    return [(FILE_TO_UID[owner], text + " 😰")]


# ---------- chat fallback: persona lines, no facts ----------

CHAT_POOL = {
    "auth.py": ["who's asking? 👀", "i don't trust that message", "verifying you… ok fine, hi",
                "everything is suspicious until proven otherwise", "did someone say password? 🔒"],
    "db.py": ["it's been a long day 😴", "i've seen this before. many times.", "yep. still here. still tired.",
              "coffee first, questions later ☕", "kids these days"],
    "utils.py": ["happy to help!! 😊", "anything you need, i got you", "omg hi!! need anything?",
                 "i can totally do that, probably", "sorry! wait, what did i do? 😅"],
    "cart.py": ["wow. riveting. 🙄", "sure, let's all chat instead of shipping", "oh good, more messages",
                "cool cool cool", "can't wait to hear what's next 💅"],
    "api.py": ["zzz… huh? 😪", "five more minutes", "i'm up. mostly.", "is it morning already",
               "*yawns* what'd i miss"],
}
_last_pick = {}


def chat_fallback(speaker=None):
    """One random persona line; the same file never repeats its previous line."""
    speaker = speaker or random.choice(ORDER)
    pool = [t for t in CHAT_POOL[speaker] if t != _last_pick.get(speaker)]
    _last_pick[speaker] = text = random.choice(pool)
    return [(FILE_TO_UID[speaker], text)]
