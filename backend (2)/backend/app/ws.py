"""
WebSocket push.

The stream processor writes straight into the databases; it does not notify the
API. Rather than ask Person B to change their code (which would couple our two
services together), the API runs ONE background loop that re-reads the cheap
Redis counters every couple of seconds and pushes to every connected client
only when a number has actually changed.

One loop, N clients - so 50 open dashboards cost the same as one.
"""

import asyncio
import logging
from typing import Set

from fastapi import WebSocket

from . import config, services

log = logging.getLogger("shopsphere.ws")


class LiveHub:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._last: dict | None = None
        self._task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        # Send the current numbers immediately so the dashboard is never blank
        # while waiting for the next change.
        snapshot = await asyncio.to_thread(services.live_snapshot)
        self._last = snapshot
        await websocket.send_json({"event": "snapshot", **snapshot})

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._clients.discard(websocket)

    async def _broadcast(self, payload: dict):
        async with self._lock:
            clients = list(self._clients)
        dead = []
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    async def _loop(self):
        while True:
            try:
                await asyncio.sleep(config.WS_POLL_SECONDS)
                async with self._lock:
                    if not self._clients:
                        continue
                # Blocking Redis reads go to a thread so they never stall the
                # event loop and starve the HTTP endpoints.
                snapshot = await asyncio.to_thread(services.live_snapshot)
                prev = self._last or {}
                changed = any(
                    snapshot.get(k) != prev.get(k)
                    for k in ("revenue_today", "orders_today", "active_users")
                )
                if not changed:
                    continue
                event = (
                    "new_order"
                    if snapshot.get("orders_today", 0) > prev.get("orders_today", 0)
                    else "tick"
                )
                self._last = snapshot
                await self._broadcast({"event": event, **snapshot})
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("live loop error: %s", e)

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


hub = LiveHub()
