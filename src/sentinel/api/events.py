"""Server-Sent Events (SSE) broadcaster conforming to PRD Section 11.3 & 12."""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Set


class EventBroadcaster:
    """Pub-sub broadcast hub for real-time risk intelligence and stress testing events."""

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to all connected SSE clients."""
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(q)

        for q in dead_queues:
            self._subscribers.discard(q)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]) -> None:
        """Synchronous helper for broadcasting from sync code."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            pass

    async def stream_events(self) -> AsyncGenerator[str, None]:
        """Yield formatted SSE text messages with heartbeat."""
        q = self.subscribe()
        try:
            # Send initial connected greeting
            init_data = json.dumps({"connected": True, "time": datetime.utcnow().isoformat()})
            yield f"event: connect\ndata: {init_data}\n\n"

            while True:
                try:
                    # Wait up to 15s for new message, then send ping keepalive
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    event_type = msg["event"]
                    data_str = json.dumps(msg["data"])
                    yield f"event: {event_type}\ndata: {data_str}\n\n"
                except asyncio.TimeoutError:
                    ping_data = json.dumps({"ping": True, "time": datetime.utcnow().isoformat()})
                    yield f"event: ping\ndata: {ping_data}\n\n"
        finally:
            self.unsubscribe(q)


# Singleton event broadcaster instance for backend runtime
broadcaster = EventBroadcaster()
