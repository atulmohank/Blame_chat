import json
from pathlib import Path

BRAIN = Path(__file__).resolve().parent
REPO = BRAIN.parent / "tinyshop"
STATE_FILE = BRAIN / "state.json"


def load():
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save(state):
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
