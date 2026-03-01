# backend/app/api/routes_events.py

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.agent.events import hub, new_event, event_to_payload, sse_format


router = APIRouter(
    prefix="",
    tags=["Events"],
)


@router.get("/events")
async def events_stream(request: Request, run_id: Optional[str] = None):
    """
    Server-Sent Events endpoint.

    - If run_id is provided: stream only that run's events (+ global, if you publish global)
    - Else: stream all events
    """

    q = await hub.subscribe(run_id=run_id)

    async def generator():
        try:
            # Send an initial "connected" event
            connected = new_event(
                type="status",
                message="SSE connected",
                run_id=run_id,
                data={"scope": "run" if run_id else "global"},
            )
            yield sse_format("status", event_to_payload(connected), connected.id)

            while True:
                # If client disconnects, stop
                if await request.is_disconnected():
                    break

                try:
                    # Wait for next event with timeout; on timeout, send heartbeat
                    evt = await asyncio.wait_for(q.get(), timeout=10.0)
                    yield sse_format(evt.type, event_to_payload(evt), evt.id)
                except asyncio.TimeoutError:
                    hb = new_event(type="heartbeat", message="ping", run_id=run_id)
                    yield sse_format("heartbeat", event_to_payload(hb), hb.id)

        finally:
            await hub.unsubscribe(q, run_id=run_id)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Helpful for Nginx if you later proxy:
            "X-Accel-Buffering": "no",
        },
    )
