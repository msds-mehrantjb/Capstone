from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from datetime import datetime
import re

router = APIRouter(prefix="/api/scope", tags=["scope"])


def _default_scope(year: int) -> dict:
    """
    Creates ISO 27001 Scope Statement template
    with all placeholders preserved.
    """
    return {
        "meta": {
            "year": year,
            "version": "v0",
            "title": "ISO 27001 Scope Statement",
            "template_name": "ISO 27001 Scope Statement Template",
            "created_at": datetime.utcnow().isoformat(),
            "placeholders_retained": True,
        },
        "sections": [
            {
                "id": "1_introduction_purpose",
                "title": "1. Introduction and Purpose",
                "body": "The Information Security Management System (ISMS) of [Organization Name] is established to protect the confidentiality, integrity, and availability of information assets supporting the [Primary Business Function, e.g., Financial Services / Software Development] operations.",
                "bullets": [],
            },
            {
                "id": "2_organizational_boundaries",
                "title": "2. Organizational Boundaries",
                "body": "The ISMS applies to the following departments and business units within [Organization Name]:",
                "bullets": [
                    "[Department A, e.g., Information Technology]",
                    "[Department B, e.g., Human Resources]",
                    "[Specific Project Team, e.g., Managed Services Division]",
                ],
            },
            {
                "id": "3_geographic_physical_boundaries",
                "title": "3. Geographic and Physical Boundaries",
                "body": "The scope includes all information processing facilities located at:",
                "bullets": [
                    "[Main Office Address]: Including the primary server room housing the Windows-based server cluster.",
                    "[Secondary Site/Data Center Address]: Hosting backup domain controllers and disaster recovery systems.",
                    "[Remote Work Policy]: The scope extends to the secure management of corporate-issued Windows workstations used by remote employees via [VPN/Zero Trust solution].",
                ],
            },
            {
                "id": "4_technical_logical_boundaries",
                "title": "4. Technical and Logical Boundaries",
                "body": "This ISMS encompasses the Windows-based enterprise ecosystem, specifically:",
                "bullets": [
                    "Identity Management: All user accounts, groups, and permissions managed via [Active Directory Domain Name / Azure AD tenant].",
                    "Server Infrastructure: All Windows Server instances (including [Web, SQL, File, and Application Servers]) hosted on [Physical Hardware / Hyper-V / VMware].",
                    "Endpoint Management: All enterprise-managed Windows workstations and laptops managed via [Microsoft Endpoint Manager / Intune / Group Policy].",
                    "Network Infrastructure: The local area network (LAN), wireless networks, and firewalls securing the Windows environment.",
                ],
            },
            {
                "id": "5_exclusions_justifications",
                "title": "5. Exclusions and Justifications",
                "body": "The following areas are excluded from the scope of the ISMS:",
                "bullets": [
                    "[Excluded Asset/Location]: Justified because [Reason, e.g., this facility is managed by a third-party landlord and does not store corporate data].",
                    "[Specific Business Unit]: Justified because it operates on a completely air-gapped network with no interaction with the primary enterprise domain.",
                ],
            },
            {
                "id": "6_stakeholders_external_dependencies",
                "title": "6. Stakeholders and External Dependencies",
                "body": "The scope also accounts for the security requirements of:",
                "bullets": [
                    "Customers: Specifically those utilizing the [Specific Service Name].",
                    "Regulators: Compliance with [Local/Industry Law, e.g., GDPR, HIPAA].",
                    "Third-Party Vendors: Specifically [Cloud Provider Name, e.g., Microsoft Azure] for hybrid identity services.",
                ],
            },
        ],
    }


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    d = _project_root() / "data" / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _system_status_path() -> Path:
    return _data_dir() / "SystemStatus.json"


def _read_system_status() -> dict:
    p = _system_status_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"SystemStatus.json not found at: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read SystemStatus.json: {e}")


# ---- NEW: filename validation (prevents ../ traversal) ----
_SCOPE_FILE_RE = re.compile(r"^\d{4}-Scope(?:-[A-Za-z0-9_]+)?-v\d+\.json$")


def _validate_scope_filename(year: int, filename: str) -> str:
    filename = (filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    # must match 2026-Scope-Anything-v3.json or 2026-Scope-v3.json
    if not _SCOPE_FILE_RE.match(filename):
        raise HTTPException(status_code=400, detail=f"Invalid scope filename: {filename}")

    # must belong to this year
    if not filename.startswith(f"{year}-Scope"):
        raise HTTPException(status_code=400, detail=f"Filename year mismatch: {filename}")

    return filename


def _load_or_create(year: int, filename: str) -> dict:
    data_dir = _data_dir()
    p = data_dir / filename

    if not p.exists():
        # create ONLY the v0 template if it's requested/missing
        if filename == f"{year}-Scope-v0.json":
            p.write_text(json.dumps(_default_scope(year), indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            raise HTTPException(status_code=404, detail=f"Scope file not found: {filename}")

    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read scope file {filename}: {e}")

    doc.setdefault("meta", {})
    doc["meta"]["source_file"] = filename
    return doc


@router.get("/context")
def get_scope_context(year: int = 2026):
    """
    Loads the scope doc based on SystemStatus.json sections.scope_context.scope_file_name
    Falls back to {year}-Scope-v0.json if missing.
    """
    sys = _read_system_status()
    scope_ctx = ((sys.get("sections") or {}).get("scope_context") or {})
    filename = scope_ctx.get("scope_file_name") or f"{year}-Scope-v0.json"

    # validate only if not v0 fallback (v0 is always acceptable)
    if filename != f"{year}-Scope-v0.json":
        filename = _validate_scope_filename(year, filename)

    return _load_or_create(year, filename)


# ✅ NEW ENDPOINT used by Dashboard.tsx
@router.get("/file")
def get_scope_by_filename(year: int = 2026, filename: str = ""):
    """
    Loads a scope doc by exact filename (must match naming convention).
    Example:
      /api/scope/file?year=2026&filename=2026-Scope-v2.json
    """
    filename = _validate_scope_filename(year, filename)
    return _load_or_create(year, filename)