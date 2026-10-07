# BlameChat

**Git blame, but it's a group chat.**

Every file in a small demo repo (`tinyshop/`) is a member of a CometChat group. When a test breaks
and you ask "who broke login?", the files argue it out, and the guilty one confesses. The culprit is
never guessed: it is computed **before anyone speaks**:

1. run the failing test,
2. trace exactly which repo lines that test executed,
3. intersect them with the `git diff` since the last green commit,
4. `git blame` the surviving line to get the commit that broke it.

The chat is the presentation layer over those facts. When you commit a fix, the files react live
(a post-commit hook pings the brain, tests re-run, and the room goes green). The **Evidence panel**
shows every step: the test output, traced lines, diff hunks and the blame line behind each claim.

Demo video: <link>

## How it uses CometChat

- **React UI Kit v7** (`@cometchat/chat-uikit-react`) renders the group chat. Custom bubbles show code
  fragments, commit chips and the confession.
- **REST API** (brain side): creates the users (the human plus one user per file) and a fresh group
  per demo take, and posts each file's messages with `onBehalfOf`, including `mentions` and message
  `metadata` (the grounded facts the UI renders as evidence).
- **CometChat MCP server**: used during the build to look up the UI Kit and REST API docs and recipes.

> **Note:** CometChat stores and renders all messages. Bot messages posted via REST weren't being
> pushed over the WebSocket, so the brain sends a live event stream (SSE) and the UI fetches each
> new message from CometChat by id.

## Architecture

```
   you (browser)                          brain/ (FastAPI :8787)                 tinyshop/ (git repo)
 +----------------------+   POST /ask    +-----------------------------+  pytest  +------------------+
 | web/ (Vite + React)  | -------------> | ground.py  test -> trace ->  | -------> | tests, *.py      |
 | CometChat UI Kit v7  |                |            diff -> blame     | <------- | git log/diff/    |
 |  - group chat        | <- GET /events |   (facts, never guessed)     |          |   blame          |
 |  - Evidence panel    |     (SSE)      | template.py / llm.py (words) |          +------------------+
 |  - In the room panel |                | validator.py (facts checked) |                 |
 +----------------------+                +-----------------------------+                  | post-commit hook
        |      ^                                |  REST: users, groups,                    v
        |      | fetch message by id            |  onBehalfOf messages,          POST /commit -> files react
        v      |                                v  mentions, metadata
 +---------------------------------------------------------------+
 |                      CometChat (stores + delivers messages)    |
 +---------------------------------------------------------------+
```

## Setup (Windows)

Requirements: Python 3.11+, Node 20+, git, and a CometChat app (App ID, region, Auth Key, REST API key).

```
copy brain\.env.example brain\.env      # fill in COMETCHAT_APP_ID, REGION, REST_API_KEY
copy web\.env.example web\.env          # fill in VITE_COMETCHAT_APP_ID, REGION, AUTH_KEY

cd brain
pip install -r requirements.txt
python setup_cometchat.py               # one-time: creates the human user + 5 file users
python make_tinyshop.py                 # recreates ../tinyshop with its 4 demo commits
cd ..\web
npm install
```

`LLM_MODE` in `brain/.env` defaults to `template` (no LLM needed). Optionally set it to `groq` or
`gemini` and add `GROQ_API_KEY` / `GEMINI_API_KEY` for freer banter; the facts stay the same.

`make_tinyshop.py` rebuilds tinyshop byte for byte, so its commit hashes (`1bced6f`, `4278cfe`,
`6fd0a29`, `673b583`) match `brain/state.json`. If yours differ (for example, git is set to sign
commits), update `last_green`, `init_commit`, `bug_commit` and `decoy_head` in `brain/state.json`.

## Run (3 terminals)

Before each take (fresh group, tinyshop reset to the buggy HEAD, post-commit hook installed):

```
cd brain
python reset_take.py
```

- Terminal 1 (brain): `cd brain` then `python -m uvicorn server:app --port 8787`
- Terminal 2 (web): `cd web` then `npm run dev`, then open http://localhost:5173
- Terminal 3 (cli): `cd tinyshop` then `python cli.py login alice Secret1` (fails)

## Demo flow

1. Login fails in the CLI. In the chat, ask **"who broke login?"**
2. The files talk it over. The decoys (`cart.py`, a later `auth.py` tidy-up) get ruled out by the
   evidence, and `utils.py` confesses to line 6 (`.strip().lower()`) from commit `4278cfe`
   ("refactor: normalize passwords"). The Evidence panel shows the trace, diff and blame.
3. Fix it: in `tinyshop/utils.py` line 6, change `pw.strip().lower().encode()` back to `pw.encode()`, then
   `git commit -am "fix hash"`. The hook pings the brain, the files react and the tests go green.
4. `python cli.py login alice Secret1` now prints the welcome. Run `reset_take.py` before the next take.

## Layout

- `brain/`: FastAPI service. `/session`, `/ask`, `/commit`, `/events` (SSE), `/status`. `ground.py`
  computes the culprit, `trace_plugin.py` records executed lines, `validator.py` checks every message
  against the facts, and `make_tinyshop.py` builds the demo repo.
- `web/`: Vite + React + CometChat React UI Kit v7.
- `PRODUCT.md`, `DESIGN.md`, `.impeccable/`: product brief and design system.
