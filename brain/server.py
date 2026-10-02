"""BlameChat brain. Run: uvicorn server:app --port 8787  (from the brain/ folder)"""
import asyncio
import random
import re
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import state
from cometchat import send_text
from ground import find_culprit
from template import build_lines

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


BLAME = re.compile(r"\b(broke|break|broken|blame|bug|fail|guilty|culprit)\b", re.I)


async def ground_and_post(guid):
    log("grounding…")
    evidence = []
    try:
        facts = await asyncio.to_thread(find_culprit, evidence=evidence)
    except Exception as e:
        for line in evidence:
            log(line)
        log(f"grounding failed: {e}")
        return
    for line in evidence:
        log(line)
    log("asking the files…")
    await post_script(guid, build_lines(facts))


@app.post("/ask")
async def ask(body: Ask):
    guid = body.guid or state.load().get("guid")
    log(f"atul asked: {body.text!r} (group {guid})")
    if BLAME.search(body.text):
        asyncio.create_task(ground_and_post(guid))
        return {"ok": True, "grounding": True}
    # Not a blame question: keep the Day 2 hello.
    lines = [("db_py", "hi 👋 db.py here. tired, but present.")]
    asyncio.create_task(post_script(guid, lines))
    return {"ok": True, "queued": len(lines)}
