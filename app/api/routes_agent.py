# app/api/routes_agent.py

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.runtime import create_run, start_run_background, get_run, run_record_to_dict


router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentRunRequest(BaseModel):
    input: str = Field(..., description="User input/prompt for the agent")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None


class AgentRunResponse(BaseModel):
    run_id: str
    status: str


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest) -> AgentRunResponse:
    rr = await create_run(payload=req.model_dump())
    await start_run_background(rr.run_id)
    return AgentRunResponse(run_id=rr.run_id, status="created")


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str) -> Dict[str, Any]:
    rr = await get_run(run_id)
    if not rr:
        raise HTTPException(status_code=404, detail="run_id not found")
    return run_record_to_dict(rr)
