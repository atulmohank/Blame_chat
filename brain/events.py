"""Live step stream for the web UI (GET /events, Server-Sent Events).

Every line the brain prints to its log is also an event here, stamped with the same HH:MM:SS.
Shape: {ts, take, kind, text, refs}; refs hold the computed facts behind the line (from ground.py,
pytest and git), never hand-written values. The current take's events are kept in memory so a
page reload replays them; a new take (reset_take.py bumps state.json) starts an empty history.
Push only: subscribers are queues fed by emit(), nothing here runs on a timer.
"""
import asyncio
import itertools
import json

import state

HISTORY = []          # [(seq, event)] for the current take
SUBSCRIBERS = set()   # asyncio.Queue per open /events stream
TAKE = None
_seq = itertools.count(1)


def current_take():
    try:
        return state.load().get("take")
    except Exception:
        return TAKE


def sync_take():
    """Drop the history when reset_take.py has started a new take since the last event."""
    global TAKE
    take = current_take()
    if take != TAKE:
        TAKE = take
        HISTORY.clear()
    return TAKE


def emit(when, kind, text, refs=None):
    """when: the same datetime the log line was stamped with."""
    event = {"ts": when.strftime("%H:%M:%S"), "take": sync_take(), "kind": kind, "text": text,
             "refs": refs or {}}
    item = (next(_seq), event)
    HISTORY.append(item)
    for q in SUBSCRIBERS:
        q.put_nowait(item)
    return event


def subscribe():
    """A queue for live events plus a snapshot of the history to replay first (taken atomically)."""
    sync_take()
    q = asyncio.Queue()
    SUBSCRIBERS.add(q)
    return q, list(HISTORY)


def unsubscribe(q):
    SUBSCRIBERS.discard(q)


def sse(seq, event, name=None):
    head = (f"event: {name}\n" if name else "") + (f"id: {seq}\n" if seq is not None else "")
    return f"{head}data: {json.dumps(event, ensure_ascii=False)}\n\n"
