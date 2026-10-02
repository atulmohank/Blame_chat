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
    python reset_take.py               # resets tinyshop + makes a fresh empty group

Terminal 1 (brain):  `cd brain`  then  `python -m uvicorn server:app --port 8787`
Terminal 2 (web):    `cd web`    then  `npm run dev`  -> open http://localhost:5173
Terminal 3 (cli):    `cd tinyshop` then `python cli.py login alice Secret1`

## Layout

- `tinyshop/`  demo repo (own git history: init -> bug -> 2 decoys)
- `brain/`     FastAPI: `/session` (current group), `/ask` (your message -> files reply via CometChat REST)
- `web/`       Vite + React + CometChat React UI Kit v7, logged in as `atul`
