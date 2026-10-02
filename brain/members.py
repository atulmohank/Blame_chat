"""Who is in the BlameChat group. UIDs can't contain dots, so auth.py -> auth_py."""

HUMAN = {"uid": "atul", "name": "Atul"}

# Order matters: the template's role rules pick "first by member order".
FILES = [
    {"uid": "auth_py",  "name": "auth.py",  "file": "auth.py",  "persona": "paranoid gatekeeper"},
    {"uid": "db_py",    "name": "db.py",    "file": "db.py",    "persona": "tired senior"},
    {"uid": "utils_py", "name": "utils.py", "file": "utils.py", "persona": "people-pleaser who breaks things"},
    {"uid": "cart_py",  "name": "cart.py",  "file": "cart.py",  "persona": "sarcastic bystander"},
    {"uid": "api_py",   "name": "api.py",   "file": "api.py",   "persona": "sleepy bystander"},
]

FILE_TO_UID = {m["file"]: m["uid"] for m in FILES}


def avatar(uid: str) -> str:
    # Free, no-signup avatar images. First thing to cut if they cause trouble.
    return f"https://api.dicebear.com/9.x/bottts-neutral/png?seed={uid}&size=128"
