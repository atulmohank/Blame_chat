"""One-time: create the human user + 5 file users. Safe to re-run."""
from cometchat import CometChatError, create_user, update_user
from members import FILES, HUMAN, avatar


def ensure(uid, name):
    try:
        create_user(uid, name, avatar(uid))
        print(f"created  {uid:9} ({name})")
    except CometChatError as e:
        if e.code == "ERR_UID_ALREADY_EXISTS" or "exist" in str(e.body).lower():
            update_user(uid, name, avatar(uid))
            print(f"exists   {uid:9} ({name}) -> updated name/avatar")
        else:
            raise


if __name__ == "__main__":
    ensure(HUMAN["uid"], HUMAN["name"])
    for m in FILES:
        ensure(m["uid"], m["name"])
    print("done: 6 users ready")
