# BlameChat

Git blame, but it's a group chat. Every member of the CometChat group is a file in `tinyshop/`.

## Run it (Windows, 3 terminals)

One-time:

    cd brain
    pip install -r requirements.txt
    python setup_cometchat.py          # creates atul + 5 file users
    cd ..\web
    npm install

Each recording take:

    cd brain
    python reset_take.py               # resets tinyshop, installs the post-commit hook, fresh empty group

Terminal 1 (brain):  `cd brain`  then  `python -m uvicorn server:app --port 8787`
Terminal 2 (web):    `cd web`    then  `npm run dev`  -> open http://localhost:5173
Terminal 3 (cli):    `cd tinyshop` then `python cli.py login alice Secret1`

Then, in the chat: ask "who broke login?" -> the files argue, utils.py confesses (L6 `.strip().lower()`).
Fix it: in `tinyshop/utils.py` L6 change `pw.strip().lower().encode()` back to `pw.encode()`, save, then

    cd tinyshop
    git commit -am "fix hash"          # post-commit hook pings the brain, returns instantly

utils.py complains about the rewrite, auth.py says tests are green, and
`python cli.py login alice Secret1` prints "✅ welcome". Run `reset_take.py` before the next take.

## Layout

- `tinyshop/`  demo repo (own git history: init -> bug -> 2 decoys)
- `brain/`     FastAPI: `/session` (current group), `/ask` (your message -> files reply via CometChat REST), `/commit` (post-commit hook -> files react)
- `web/`       Vite + React + CometChat React UI Kit v7, logged in as `atul`
