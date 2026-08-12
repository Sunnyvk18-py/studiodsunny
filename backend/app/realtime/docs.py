"""Extend chat hub with doc collab rooms (Yjs update relay via Redis)."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from fastapi import WebSocket

from app.realtime.hub import hub


class DocCollab:
    """Fan-out Yjs binary updates for a document room."""

    PREFIX = "doc:"

    def room(self, doc_id: str) -> str:
        return f"{self.PREFIX}{doc_id}"

    async def publish_update(self, doc_id: str, update_b64: str, sender_id: str) -> None:
        payload = {
            "type": "yjs",
            "doc_id": doc_id,
            "update": update_b64,
            "sender_id": sender_id,
        }
        channel = self.room(doc_id)
        body = json.dumps(payload)
        if hub.redis:
            try:
                await hub.redis.publish(f"hq:chat:{channel}", body)
                # keep latest snapshot hint for late joiners (optional soft state)
                await hub.redis.set(f"hq:doc:last:{doc_id}", update_b64, ex=3600)
                return
            except Exception:
                pass
        await hub._fanout(channel, payload)

    async def publish_awareness(self, doc_id: str, awareness: dict[str, Any], sender_id: str) -> None:
        payload = {
            "type": "awareness",
            "doc_id": doc_id,
            "awareness": awareness,
            "sender_id": sender_id,
        }
        await hub.publish(self.room(doc_id), payload)

    async def publish_awareness_bin(
        self,
        doc_id: str,
        update_b64: str,
        sender_id: str,
        awareness: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "type": "awareness-bin",
            "doc_id": doc_id,
            "update": update_b64,
            "sender_id": sender_id,
            "awareness": awareness or {},
        }
        await hub.publish(self.room(doc_id), payload)

    async def subscribe(self, ws: WebSocket, doc_id: str) -> None:
        await hub.subscribe(ws, self.room(doc_id))


doc_collab = DocCollab()


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))
