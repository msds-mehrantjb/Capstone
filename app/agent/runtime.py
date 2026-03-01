# app/agent/runtime.py

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from app.agent.events import hub, new_event
from app.agent.graph import agent_graph



@dataclass
class RunRecord:
    run_id: str
    created_ts: float
    started_ts: Optional[float] = None
    finished_ts: Optional[float] = None
    status: str = "created"  # created | running | succeeded | failed
    input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


_runs: Dict[str, RunRecord] = {}
_runs_lock = asyncio.Lock()


async def create_run(payload: Dict[str, Any]) -> RunRecord:
    run_id = str(uuid.uuid4())
    rr = RunRecord(run_id=run_id, created_ts=time.time(), input=payload)
    async with _runs_lock:
        _runs[run_id] = rr
    return rr


async def get_run(run_id: str) -> Optional[RunRecord]:
    async with _runs_lock:
        return _runs.get(run_id)


async def _update_run(run_id: str, **updates) -> None:
    async with _runs_lock:
        rr = _runs.get(run_id)
        if not rr:
            return
        for k, v in updates.items():
            setattr(rr, k, v)


async def start_run_background(run_id: str) -> None:
    asyncio.create_task(_run_pipeline(run_id))


async def _run_pipeline(run_id: str) -> None:
    await _update_run(run_id, status="running", started_ts=time.time())

    await hub.publish(
        new_event(type="status", message="Run started", run_id=run_id, data={"status": "running"})
    )

    try:
        # PLAN
        await hub.publish(
            new_event(type="node_start", message="Planning started", run_id=run_id, data={"node": "plan"})
        )
        await asyncio.sleep(0.75)
        await hub.publish(
            new_event(type="node_end", message="Planning complete", run_id=run_id, data={"node": "plan"})
        )

        # EXECUTE
        await hub.publish(
            new_event(type="node_start", message="Execution started", run_id=run_id, data={"node": "execute"})
        )
        await asyncio.sleep(0.75)
        await hub.publish(
            new_event(type="node_end", message="Execution complete", run_id=run_id, data={"node": "execute"})
        )

        # SUMMARIZE
        await hub.publish(
            new_event(type="node_start", message="Summarization started", run_id=run_id, data={"node": "summarize"})
        )
        await asyncio.sleep(0.75)
        await hub.publish(
            new_event(type="node_end", message="Summarization complete", run_id=run_id, data={"node": "summarize"})
        )

        await _update_run(run_id, status="succeeded", finished_ts=time.time())

        await hub.publish(
            new_event(type="status", message="Run succeeded", run_id=run_id, data={"status": "succeeded"})
        )

    except Exception as e:
        await _update_run(run_id, status="failed", finished_ts=time.time(), error=str(e))

        await hub.publish(
            new_event(type="error", message="Run failed", run_id=run_id, data={"error": str(e)})
        )
    initial_state = {
    "run_id": run_id,
    "input": rr.input["input"],
    "plan": {},
    "evidence": {},
    "report": {},
    }

    result = await agent_graph.ainvoke(initial_state)


def run_record_to_dict(rr: RunRecord) -> Dict[str, Any]:
    return asdict(rr)
