from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any, Dict, Literal
from datetime import datetime
import json
import os
import tempfile

router = APIRouter(prefix="/api/system", tags=["system"])

StepStatus = Literal["Blocked", "Not Started", "In Progress", "Completed"]

def project_root() -> Path:
    # .../Capstone-main/app/api/routes_system_status.py -> parents[2] = Capstone-main
    return Path(__file__).resolve().parents[2]

RAW_DIR = project_root() / "data" / "raw"
SYSTEM_STATUS_PATH = RAW_DIR / "SystemStatus.json"

DEFAULT_SECTIONS: Dict[str, Dict[str, StepStatus]] = {
    "scope_context": {"status": "Not Started", "scope_file_name": "2026-Scope-Draft-v0.json"},
    "assets_cia": {"status": "Blocked"},
    "threats_vulns": {"status": "Blocked"},
    "controls_posture": {"status": "Blocked"},
    "risk_analysis": {"status": "Blocked"},
    "risk_evaluation": {"status": "Blocked"},
    "risk_treatment": {"status": "Blocked"},
    "soa": {"status": "Blocked"},
    "action_plan": {"status": "Blocked"},
    "monitoring": {"status": "Blocked"},
    "reports": {"status": "Blocked"},
}


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _default_status() -> Dict[str, Any]:
    return {
        "meta": {"name": "SystemStatus", "version": "1.0"},
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "sections": DEFAULT_SECTIONS,
    }


def _load_status() -> Dict[str, Any]:
    if not SYSTEM_STATUS_PATH.exists():
        data = _default_status()
        _atomic_write_json(SYSTEM_STATUS_PATH, data)
        return data

    try:
        return json.loads(SYSTEM_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read SystemStatus.json: {e}")


def _normalize_status(data: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"Blocked", "Not Started", "In Progress", "Completed"}

    if not isinstance(data.get("meta"), dict):
        data["meta"] = {"name": "SystemStatus", "version": "1.0"}

    sections = data.get("sections")
    if not isinstance(sections, dict):
        sections = {}

    # ensure all expected keys exist
    for k, v in DEFAULT_SECTIONS.items():
        if k not in sections or not isinstance(sections.get(k), dict):
            sections[k] = dict(v)  # keep defaults (including scope_file_name)
        else:
            # merge in defaults without overwriting existing extra fields
            for dk, dv in v.items():
                sections[k].setdefault(dk, dv)

    # normalize all statuses to allowed set (preserve extra fields)
    for k, v in list(sections.items()):
        if not isinstance(v, dict):
            sections[k] = {"status": "Blocked"}
            continue
        st = v.get("status")
        v["status"] = st if st in allowed else "Blocked"
        sections[k] = v

    data["sections"] = sections
    if "updated_at" not in data:
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return data


@router.get("/status")
def get_status() -> Dict[str, Any]:
    """
    Return current SystemStatus.json (creates a default one if missing).
    """
    return _normalize_status(_load_status())


@router.post("/reset-audit")
def reset_audit() -> Dict[str, Any]:
    data = _normalize_status(_load_status())
    sections = data["sections"]

    for k in list(sections.keys()):
        sections[k]["status"] = "Blocked"

    sections["scope_context"]["status"] = "Not Started"
    sections["scope_context"]["scope_file_name"] = "2026-Scope-Draft-v0.json"

    data["sections"] = sections
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _atomic_write_json(SYSTEM_STATUS_PATH, data)
    return data