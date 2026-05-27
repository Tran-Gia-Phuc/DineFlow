"""
streaming/sse_manager.py
Quản lý SSE queues theo session_id.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


class SSEManager:

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}

    # --- Queue lifecycle ---

    def create_queue(self, session_id: str, maxsize: int = 100) -> asyncio.Queue:
        if session_id in self._queues:
            logger.warning("SSEManager: queue %s đã tồn tại, tạo lại", session_id)
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._queues[session_id] = q
        logger.info("SSEManager: created queue for %s (total=%d)", session_id, len(self._queues))
        return q

    def get_queue(self, session_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(session_id)

    def remove_queue(self, session_id: str) -> None:
        if session_id in self._queues:
            del self._queues[session_id]
            logger.info("SSEManager: removed queue for %s (total=%d)", session_id, len(self._queues))

    # --- Emit ---

    def emit_sync(self, session_id: str, event: dict) -> bool:
        """Gọi từ LangChain callback (sync thread) — dùng put_nowait."""
        q = self._queues.get(session_id)
        if q is None:
            return False
        try:
            q.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("SSEManager.emit_sync: queue full for %s", session_id)
            return False

    async def emit(self, session_id: str, event: dict) -> bool:
        """Gọi từ async context (worker)."""
        q = self._queues.get(session_id)
        if q is None:
            return False
        try:
            await q.put(event)
            return True
        except asyncio.QueueFull:
            logger.warning("SSEManager.emit: queue full for %s", session_id)
            return False

    # --- Stream ---

    async def stream(self, session_id: str) -> AsyncGenerator[dict, None]:
        """Yield từng event cho EventSourceResponse. Tự dọn queue sau done/error."""

        # Chờ queue được tạo (POST /chat/async có thể đến sau GET /chat/stream)
        WAIT_TIMEOUT = 30  # chờ tối đa 30 giây
        waited = 0
        while session_id not in self._queues:
            await asyncio.sleep(0.2)
            waited += 0.2
            if waited >= WAIT_TIMEOUT:
                yield {"type": "error", "message": "Session không tồn tại hoặc timeout"}
                return

        q = self._queues[session_id]

        TIMEOUT = 300  # 5 phút
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    logger.warning("SSEManager.stream: timeout for %s", session_id)
                    yield {"type": "error", "message": "Timeout"}
                    break

                yield event

                if event.get("type") in ("done", "error"):
                    break
        finally:
            self.remove_queue(session_id)

# Singleton — import ở khắp nơi
sse_manager = SSEManager()