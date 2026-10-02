"""Thin CometChat REST v3 client.

Shapes come from CometChat MCP doc pages:
  POST /users                 (rest-api/users/create)
  POST /groups                (rest-api/groups/create, members{participants,...})
  POST /messages + onBehalfOf (rest-api/messages/send-message)
Auth header: `apikey: <REST API key>`. Base: https://{appId}.api-{region}.cometchat.io/v3
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

APP_ID = os.environ["COMETCHAT_APP_ID"]
REGION = os.environ["COMETCHAT_REGION"]
REST_KEY = os.environ["COMETCHAT_REST_API_KEY"]
BASE = f"https://{APP_ID}.api-{REGION}.cometchat.io/v3"


class CometChatError(RuntimeError):
    def __init__(self, status, body):
        self.status, self.body = status, body
        code = (body or {}).get("error", {}).get("code") if isinstance(body, dict) else None
        self.code = code
        super().__init__(f"CometChat {status}: {body}")


def _headers(on_behalf_of=None):
    h = {"apikey": REST_KEY, "accept": "application/json", "content-type": "application/json"}
    if on_behalf_of:
        h["onBehalfOf"] = on_behalf_of
    return h


def _call(method, path, json=None, on_behalf_of=None, params=None):
    r = httpx.request(method, BASE + path, json=json, params=params,
                      headers=_headers(on_behalf_of), timeout=15)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    if r.status_code >= 400:
        raise CometChatError(r.status_code, body)
    return body.get("data", body) if isinstance(body, dict) else body


def create_user(uid, name, avatar=None):
    payload = {"uid": uid, "name": name}
    if avatar:
        payload["avatar"] = avatar
    return _call("POST", "/users", payload)


def update_user(uid, name, avatar=None):
    payload = {"name": name}
    if avatar:
        payload["avatar"] = avatar
    return _call("PUT", f"/users/{uid}", payload)


def list_users(per_page=100):
    return _call("GET", "/users", params={"perPage": per_page})


def create_group(guid, name, owner, participants, description=""):
    return _call("POST", "/groups", {
        "guid": guid,
        "name": name,
        "type": "public",
        "description": description,
        "owner": owner,
        "members": {"participants": participants},
    })


def send_text(sender_uid, guid, text):
    return _call("POST", "/messages", {
        "receiver": guid,
        "receiverType": "group",
        "category": "message",
        "type": "text",
        "data": {"text": text},
    }, on_behalf_of=sender_uid)
