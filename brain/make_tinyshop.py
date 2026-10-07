"""Recreate the tinyshop demo repo from scratch (it is a nested git repo, so it isn't committed).
Builds the same 4 commits byte for byte, so the hashes match brain/state.json:
  1bced6f  2026-09-28T10:00:00+05:30  init
  4278cfe  2026-09-29T15:20:00+05:30  refactor: normalize passwords
  6fd0a29  2026-09-30T11:05:00+05:30  feat: 10% festive discount
  673b583  2026-10-01T18:40:00+05:30  chore: tidy reset_password

Usage (from the repo root):  python brain/make_tinyshop.py [target_dir]   (default: ./tinyshop)
Refuses to overwrite an existing target. If your git signs commits by default (commit.gpgsign),
the hashes will differ; then update last_green/init_commit/bug_commit/decoy_head in brain/state.json.
"""
import os
import subprocess
import sys
from pathlib import Path

AUTHOR = ("Atul", "babybroram@gmail.com")

# (message, ISO date, expected short hash, {path: full file content}) - only changed files per commit
COMMITS = [
    ('init', '2026-09-28T10:00:00+05:30', '1bced6f', {
        '.gitattributes': '* text=auto eol=lf\n',
        '.gitignore': '__pycache__/\n.pytest_cache/\n*.pyc\n',
        'README.md': '# tinyshop\n\nA toy shop backend used as the test fixture for BlameChat.\n\nIts git history is deliberately reproducible: a clean `init`, one commit that\nintroduces a login bug, then two unrelated "decoy" commits after it, so the\nnewest commit is *not* the one that broke login.\n\n    python cli.py login alice Secret1\n    python -m pytest -q\n',
        'api.py': '"""HTTP route stubs (not wired up yet)."""\n\n\ndef health():\n    return {"status": "ok"}\n',
        'auth.py': '"""Login, registration and password reset."""\nimport db\nimport utils\n\n\ndef register(username, pw):\n    users = db.load()\n    if username in users:\n        raise ValueError("user exists")\n    users[username] = utils.hash_password(pw)\n    db.save(users)\n\n\ndef login(username, pw):\n    users = db.load()\n    stored = users.get(username)\n    if stored is None:\n        return False\n    return stored == utils.hash_password(pw)\n\n\ndef reset_password(username, new_pw):\n    users = db.load()\n    users[username] = utils.hash_password(new_pw)\n    db.save(users)\n',
        'cart.py': '"""Shopping cart maths."""\n\n\ndef apply_discount(total, pct):\n    return round(total * (1 - pct / 100), 2)\n\n\ndef cart_total(items):\n    return round(sum(price * qty for price, qty in items), 2)\n',
        'cli.py': '"""Usage: python cli.py login <user> <password>"""\nimport sys\n\nimport auth\n\n\ndef main(argv):\n    if len(argv) != 4 or argv[1] != "login":\n        print(__doc__.strip())\n        return 2\n    if auth.login(argv[2], argv[3]):\n        print("✅ welcome")\n        return 0\n    print("❌ invalid password")\n    return 1\n\n\nif __name__ == "__main__":\n    sys.exit(main(sys.argv))\n',
        'data/users.json': '{\n  "alice": "64340506142b0e1babcb02c342d76a854469d5d61edf4bd6cb1c249ac009726e"\n}\n',
        'db.py': '"""Tiny JSON-file user store."""\nimport json\nimport os\n\n\ndef _path():\n    return os.environ.get("TINYSHOP_DB", "data/users.json")\n\n\ndef load():\n    with open(_path(), encoding="utf-8") as f:\n        return json.load(f)\n\n\ndef save(users):\n    with open(_path(), "w", encoding="utf-8") as f:\n        json.dump(users, f, indent=2, sort_keys=True)\n        f.write("\\n")\n',
        'tests/conftest.py': 'import os\nimport shutil\nimport sys\n\nimport pytest\n\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\nsys.path.insert(0, ROOT)\n\n\n@pytest.fixture(autouse=True)\ndef temp_db(tmp_path, monkeypatch):\n    dst = tmp_path / "users.json"\n    shutil.copy(os.path.join(ROOT, "data", "users.json"), dst)\n    monkeypatch.setenv("TINYSHOP_DB", str(dst))\n    yield dst\n',
        'tests/test_auth.py': 'import auth\n\n\ndef test_login_seeded_user():\n    assert auth.login("alice", "Secret1")\n\n\ndef test_register_roundtrip():\n    auth.register("bob", "Hunter2")\n    assert auth.login("bob", "Hunter2")\n',
        'utils.py': '"""Small helpers shared across tinyshop."""\nfrom hashlib import sha256\n\n\ndef hash_password(pw):\n    return sha256(pw.encode()).hexdigest()\n\n\ndef slugify(text):\n    return "-".join(text.lower().split())\n',
    }),
    ('refactor: normalize passwords', '2026-09-29T15:20:00+05:30', '4278cfe', {
        'utils.py': '"""Small helpers shared across tinyshop."""\nfrom hashlib import sha256\n\n\ndef hash_password(pw):\n    return sha256(pw.strip().lower().encode()).hexdigest()\n\n\ndef slugify(text):\n    return "-".join(text.lower().split())\n',
    }),
    ('feat: 10% festive discount', '2026-09-30T11:05:00+05:30', '6fd0a29', {
        'cart.py': '"""Shopping cart maths."""\n\n\ndef apply_discount(total, pct):\n    pct = min(pct + 10, 100)  # festive season\n    return round(total * (1 - pct / 100), 2)\n\n\ndef cart_total(items):\n    return round(sum(price * qty for price, qty in items), 2)\n',
    }),
    ('chore: tidy reset_password', '2026-10-01T18:40:00+05:30', '673b583', {
        'auth.py': '"""Login, registration and password reset."""\nimport db\nimport utils\n\n\ndef register(username, pw):\n    users = db.load()\n    if username in users:\n        raise ValueError("user exists")\n    users[username] = utils.hash_password(pw)\n    db.save(users)\n\n\ndef login(username, pw):\n    users = db.load()\n    stored = users.get(username)\n    if stored is None:\n        return False\n    return stored == utils.hash_password(pw)\n\n\ndef reset_password(username, new_pw):\n    if not new_pw:\n        raise ValueError("empty password")\n    users = db.load()\n    users[username] = utils.hash_password(new_pw)\n    db.save(users)\n',
    }),
]


def git(target, *args, env=None):
    return subprocess.run(["git", "-C", str(target), *args], check=True,
                          capture_output=True, text=True, env=env).stdout.strip()


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "tinyshop")
    if target.exists() and any(target.iterdir()):
        sys.exit(f"{target} already exists and is not empty; delete it first.")
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(target)], check=True)
    git(target, "config", "core.autocrlf", "false")
    git(target, "config", "user.name", AUTHOR[0])
    git(target, "config", "user.email", AUTHOR[1])
    ok = True
    for msg, date, expected, files in COMMITS:
        for path, content in files.items():
            f = target / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(content.encode("utf-8"))  # exact bytes, LF endings
        git(target, "add", "-A")
        env = dict(os.environ,
                   GIT_AUTHOR_NAME=AUTHOR[0], GIT_AUTHOR_EMAIL=AUTHOR[1], GIT_AUTHOR_DATE=date,
                   GIT_COMMITTER_NAME=AUTHOR[0], GIT_COMMITTER_EMAIL=AUTHOR[1], GIT_COMMITTER_DATE=date)
        git(target, "commit", "-q", "--no-verify", "-m", msg, env=env)
        got = git(target, "rev-parse", "--short=7", "HEAD")
        match = got == expected
        ok &= match
        print(f"{got}  {msg}" + ("" if match else f"   (expected {expected})"))
    print("hashes match brain/state.json" if ok else
          "WARNING: hashes differ; update the commit ids in brain/state.json")


if __name__ == "__main__":
    main()
