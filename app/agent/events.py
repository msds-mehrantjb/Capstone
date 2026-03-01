# backend/app/agent/events.py

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Set


@dataclass
class AgentEvent:
    """
    Standard event envelope for SSE.
    """
    id: str
    ts: float
    type: str
    message: str
    run_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class EventHub:
    """
    In-memory event hub supporting global and per-run subscriptions.
    """

    def __init__(self) -> None:
        self._global_subs: Set[asyncio.Queue] = set()
        self._run_subs: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: Optional[str] = None, max_queue: int = 200) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=max_queue)

        async with self._lock:
            if run_id is None:
                self._global_subs.add(q)
            else:
                if run_id not in self._run_subs:
                    self._run_subs[run_id] = set()
                self._run_subs[run_id].add(q)

        return q

    async def unsubscribe(self, q: asyncio.Queue, run_id: Optional[str] = None) -> None:
        async with self._lock:
            if run_id is None:
                self._global_subs.discard(q)
            else:
                if run_id in self._run_subs:
                    self._run_subs[run_id].discard(q)
                    if not self._run_subs[run_id]:
                        del self._run_subs[run_id]

    async def publish(self, event: AgentEvent) -> None:
        async with self._lock:
            targets = list(self._global_subs)

            if event.run_id and event.run_id in self._run_subs:
                targets.extend(list(self._run_subs[event.run_id]))

        for q in targets:
            try:
                q.put_nowait(event)

            except asyncio.QueueFull:
                # Drop event for slow subscriber
                pass


# Global singleton
hub = EventHub()


def new_event(
    *,
    type: str,
    message: str,
    run_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> AgentEvent:

    return AgentEvent(
        id=str(uuid.uuid4()),
        ts=time.time(),
        type=type,
        message=message,
        run_id=run_id,
        data=data,
    )


def event_to_payload(event: AgentEvent) -> Dict[str, Any]:
    return asdict(event)


def sse_format(event_name: str, payload: Dict[str, Any], event_id: Optional[str] = None) -> str:

    lines = []

    if event_id:
        lines.append(f"id: {event_id}")

    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(payload)}")
    lines.append("")

    return "\n".join(lines)
