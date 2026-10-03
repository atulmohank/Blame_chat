"""Template argument: facts -> [(uid, text)]. A line is emitted only if its rule finds a file."""
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
