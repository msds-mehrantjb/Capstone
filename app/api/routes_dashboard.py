from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary")
def dashboard_summary(env: str = "Production"):
    """
    Reads test dashboard JSON from:
      Capstone-main/data/raw/Dashboard.json

    NOTE:
    This file is OUTSIDE the app/ folder, so we resolve project root as:
      .../Capstone-main (two levels above app/api/)
    """
    project_root = Path(__file__).resolve().parents[2]  # -> Capstone-main/
    json_path = project_root / "data" / "raw" / "Dashboard.json"

    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Dashboard.json not found at: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    # Make env selector reflect in UI even if JSON is static
    payload["environment"] = env
    return payload
