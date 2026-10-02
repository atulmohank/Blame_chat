"""BlameChat brain. Run: uvicorn server:app --port 8787  (from the brain/ folder)"""
import asyncio
import random
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import state
from cometchat import send_text

app = FastAPI(title="BlameChat brain")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


class Ask(BaseModel):
    text: str
    guid: str | None = None


@app.get("/session")
def session():
    s = state.load()
    return {"guid": s.get("guid"), "take": s.get("take"), "uid": "atul"}


async def post_script(guid, lines):
    """lines = [(uid, text), ...], posted with human-ish gaps."""
    for i, (uid, text) in enumerate(lines):
        if i:
            await asyncio.sleep(random.uniform(1.2, 2.5))
        await asyncio.to_thread(send_text, uid, guid, text)
        log(f"posted {uid}: {text}")


@app.post("/ask")
async def ask(body: Ask):
    guid = body.guid or state.load().get("guid")
    log(f"atul asked: {body.text!r} (group {guid})")
    # Day 2 stub: prove the round trip. Day 3 replaces this with the grounded culprit finder.
    lines = [("db_py", "hi 👋 db.py here. tired, but present.")]
    asyncio.create_task(post_script(guid, lines))
    return {"ok": True, "queued": len(lines)}
