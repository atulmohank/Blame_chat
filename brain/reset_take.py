"""Fresh take: reset tinyshop to the decoy-2 HEAD, bump the take, new empty group.

Usage: python reset_take.py            (then reload the browser)
       python reset_take.py --no-git   (only make a new group)
"""
import subprocess
import sys
import time

import state
from cometchat import create_group
from members import FILES, HUMAN


def git(*args):
    return subprocess.run(["git", *args], cwd=state.REPO, check=True,
                          capture_output=True, text=True).stdout.strip()


def main():
    s = state.load()
    if "--no-git" not in sys.argv:
        git("reset", "--hard", s["decoy_head"])
        git("clean", "-fdq", "-e", "data/users.json")
        print("tinyshop reset to", git("log", "-1", "--format=%h %s"))
    s["last_green"] = s.get("init_commit", s["last_green"])
    s["take"] = int(s.get("take", 0)) + 1
    guid = f"repo-tinyshop-t{s['take']}"
    create_group(
        guid=guid,
        name="tinyshop 🧑‍💻",
        owner=HUMAN["uid"],
        participants=[m["uid"] for m in FILES],
        description="every member is a file in the repo",
    )
    s["guid"] = guid
    s["group_created_at"] = int(time.time())
    state.save(s)
    print(f"take {s['take']}: group {guid} created with {len(FILES)} files + {HUMAN['uid']}")
    print("now restart nothing - just reload http://localhost:5173")


if __name__ == "__main__":
    main()
