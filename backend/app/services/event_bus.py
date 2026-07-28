import asyncio
import logging
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class EventBus:
    """Simple pub/sub event bus to bridge Kafka consumer → WebSocket clients."""

    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.add(websocket)
        logger.info("WebSocket client connected. Total subscribers: %d", len(self._subscribers))

    async def unsubscribe(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.discard(websocket)
        logger.info("WebSocket client disconnected. Total subscribers: %d", len(self._subscribers))

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers)

        disconnected: list[WebSocket] = []
        for ws in subscribers:
            try:
                await ws.send_json(event)
            except Exception:
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._subscribers.discard(ws)
            logger.info("Removed %d disconnected subscribers.", len(disconnected))

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


event_bus = EventBus()