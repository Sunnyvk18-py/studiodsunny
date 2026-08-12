"""In-process + Redis pub/sub fan-out for chat / presence."""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.config import settings

PRESENCE_TTL = 45


class RealtimeHub:
    def __init__(self) -> None:
        self.local: dict[str, set[WebSocket]] = defaultdict(set)
        self.meta: dict[WebSocket, dict[str, Any]] = {}
        self.presence_mem: dict[str, dict[str, float]] = defaultdict(dict)
        self.redis = None
        self._listener: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url)
            await asyncio.wait_for(client.ping(), timeout=0.4)
            self.redis = client
            self._listener = asyncio.create_task(self._listen())
        except Exception:
            self.redis = None

    async def stop(self) -> None:
        if self._listener:
            self._listener.cancel()
        if self.redis:
            await self.redis.aclose()

    async def connect(self, ws: WebSocket, user: dict[str, Any]) -> None:
        await ws.accept()
        self.meta[ws] = {"user": user, "channels": set()}

    def disconnect(self, ws: WebSocket) -> list[str]:
        info = self.meta.pop(ws, None)
        channels = list((info or {}).get("channels") or [])
        for ch in channels:
            self.local[ch].discard(ws)
        return channels

    async def subscribe(self, ws: WebSocket, channel: str) -> None:
        self.local[channel].add(ws)
        if ws in self.meta:
            self.meta[ws]["channels"].add(channel)
        await self.heartbeat(channel, self.meta[ws]["user"]["id"])

    async def heartbeat(self, channel: str, user_id: str) -> None:
        now = time.time()
        if self.redis:
            key = f"hq:presence:{channel}"
            try:
                await self.redis.zadd(key, {user_id: now})
                await self.redis.zremrangebyscore(key, 0, now - PRESENCE_TTL)
                await self.redis.expire(key, 120)
                return
            except Exception:
                pass
        room = self.presence_mem[channel]
        room[user_id] = now
        for uid, ts in list(room.items()):
            if ts < now - PRESENCE_TTL:
                room.pop(uid, None)

    async def presence(self, channel: str) -> list[str]:
        now = time.time()
        if self.redis:
            try:
                await self.redis.zremrangebyscore(f"hq:presence:{channel}", 0, now - PRESENCE_TTL)
                members = await self.redis.zrange(f"hq:presence:{channel}", 0, -1)
                return [m.decode() if isinstance(m, bytes) else str(m) for m in members]
            except Exception:
                pass
        room = self.presence_mem[channel]
        return [uid for uid, ts in room.items() if ts >= now - PRESENCE_TTL]

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload)
        if self.redis:
            try:
                await self.redis.publish(f"hq:chat:{channel}", body)
                return
            except Exception:
                pass
        await self._fanout(channel, payload)

    async def _fanout(self, channel: str, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.local.get(channel, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _listen(self) -> None:
        assert self.redis is not None
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("hq:chat:*")
        try:
            async for message in pubsub.listen():
                if message.get("type") not in {"message", "pmessage"}:
                    continue
                channel_name = message.get("channel") or b""
                if isinstance(channel_name, bytes):
                    channel_name = channel_name.decode()
                slug = str(channel_name).split("hq:chat:")[-1]
                try:
                    payload = json.loads(message["data"])
                except Exception:
                    continue
                await self._fanout(slug, payload)
        except asyncio.CancelledError:
            await pubsub.aclose()


hub = RealtimeHub()
