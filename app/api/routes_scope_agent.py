from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, Optional, List, Literal, Tuple
from datetime import datetime
import json
import re
import copy

router = APIRouter(prefix="/api/scope", tags=["scope-agent"])

# -------------------------
# Models
# -------------------------

Command = Literal[
    "help",
    "commands",
    "fill",
    "exit",
    "autofill",
    "load",
    "submit",
    "reset",
    "cancel",
]

class LoadOption(BaseModel):
    id: str
    label: str

class AgentRequest(BaseModel):
    year: int = 2026
    command: Command
    draft: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None  # used for button clicks / fill selections

class AgentResponse(BaseModel):
    message: str
    draft: Dict[str, Any]
    next_question: Optional[str] = None
    saved_version: Optional[str] = None
    load_options: Optional[List[LoadOption]] = None  # buttons

# -------------------------
# Paths / IO
# -------------------------

PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")

def project_root() -> Path:
    # .../Capstone-main/app/api/routes_scope_agent.py -> parents[2] = Capstone-main
    return Path(__file__).resolve().parents[2]

def get_data_dir() -> Path:
    p = project_root() / "data" / "raw"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_system_status_path() -> Path:
    return project_root() / "data" / "raw" / "SystemStatus.json"

def update_system_scope_pointer(year: int, filename: str, status: str = "In Progress") -> None:
    p = get_system_status_path()
    if not p.exists():
        return  # or create default; but your system route already creates it
    obj = read_json(p)
    obj.setdefault("sections", {})
    obj["sections"].setdefault("scope_context", {})
    obj["sections"]["scope_context"]["status"] = status
    obj["sections"]["scope_context"]["scope_file_name"] = filename
    write_json(p, obj)

def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -------------------------
# Template (v0)
# -------------------------

def default_scope_template(year: int) -> Dict[str, Any]:
    return {
        "meta": {
            "year": year,
            "version": "v0",
            "title": "ISO 27001 Scope Statement Template",
            "template_name": "ISO 27001 Scope Statement Template",
            "created_at": datetime.utcnow().isoformat(),
            "placeholders_retained": True,
            "source_file": f"{year}-Scope-v0.json",
        },
        "sections": [
            {
                "id": "intro_purpose",
                "title": "1. Introduction and Purpose",
                "body": (
                    "The Information Security Management System (ISMS) of [Organization Name] is established "
                    "to protect the confidentiality, integrity, and availability of information assets supporting "
                    "the [Primary Business Function, e.g., Financial Services / Software Development] operations."
                ),
                "bullets": [],
            },
            {
                "id": "org_boundaries",
                "title": "2. Organizational Boundaries",
                "body": "The ISMS applies to the following departments and business units within [Organization Name]:",
                "bullets": [
                    "[Department A, e.g., Information Technology]",
                    "[Department B, e.g., Human Resources]",
                    "[Specific Project Team, e.g., Managed Services Division]",
                ],
            },
            {
                "id": "geo_boundaries",
                "title": "3. Geographic and Physical Boundaries",
                "body": "The scope includes all information processing facilities located at:",
                "bullets": [
                    "[Main Office Address]: Including the primary server room housing the Windows-based server cluster.",
                    "[Secondary Site/Data Center Address]: Hosting backup domain controllers and disaster recovery systems.",
                    "[Remote Work Policy]: The scope extends to the secure management of corporate-issued Windows workstations used by remote employees via [VPN/Zero Trust solution].",
                ],
            },
            {
                "id": "tech_boundaries",
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
                "id": "exclusions",
                "title": "5. Exclusions and Justifications",
                "body": "The following areas are excluded from the scope of the ISMS:",
                "bullets": [
                    "[Excluded Asset/Location]: Justified because [Reason, e.g., this facility is managed by a third-party landlord and does not store corporate data].",
                    "[Specific Business Unit]: Justified because it operates on a completely air-gapped network with no interaction with the primary enterprise domain.",
                ],
            },
            {
                "id": "stakeholders",
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

def ensure_v0_exists(year: int) -> Path:
    p = get_data_dir() / f"{year}-Scope-v0.json"
    if not p.exists():
        write_json(p, default_scope_template(year))
    return p

# -------------------------
# Helpers
# -------------------------

def _get_section(draft: Dict[str, Any], section_id: str, title_prefix: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find a section by id; if not found, optionally by title prefix like '2.'"""
    for s in (draft.get("sections") or []):
        if s.get("id") == section_id:
            return s
    if title_prefix:
        for s in (draft.get("sections") or []):
            t = (s.get("title") or "").strip()
            if t.startswith(title_prefix):
                return s
    return None

def _replace_everywhere(draft: Dict[str, Any], mapping: Dict[str, str]) -> None:
    def rep_text(txt: str) -> str:
        if not isinstance(txt, str):
            return txt
        out = txt
        for k, v in mapping.items():
            out = out.replace(k, v)
        return out

    meta = draft.get("meta") or {}
    for key in ("title", "template_name"):
        if isinstance(meta.get(key), str):
            meta[key] = rep_text(meta[key])
    draft["meta"] = meta

    for sec in (draft.get("sections") or []):
        if isinstance(sec.get("title"), str):
            sec["title"] = rep_text(sec["title"])
        if isinstance(sec.get("body"), str):
            sec["body"] = rep_text(sec["body"])
        bullets = sec.get("bullets")
        if isinstance(bullets, list):
            sec["bullets"] = [rep_text(b) if isinstance(b, str) else b for b in bullets]

def _replace_first_bracket_value(line: str, value: str) -> str:
    return re.sub(r"\[[^\]]+\]", value, line, count=1)

# -------------------------
# Fill state (in-memory)
# -------------------------

# _FILL_STATE[year] = {"in_fill": bool, "active": "s1".."s6"|None, "step": int, "buffer": dict|None, "exit_stage": 0|1}
_FILL_STATE: Dict[int, Dict[str, Any]] = {}

def _fill_sections() -> List[tuple[str, str, str]]:
    return [
        ("s1", "Introduction & Purpose",
         "Defines why the ISMS exists and what business function it protects (what you are protecting and why)."),
        ("s2", "Organizational Boundaries",
         "Specifies which departments, business units, and teams are included within the ISMS scope."),
        ("s3", "Geographic & Physical Boundaries",
         "Defines which sites, facilities, and remote-work arrangements are included in the scope."),
        ("s4", "Technical & Logical Boundaries",
         "Defines which systems and platforms are in scope (e.g., AD/Azure AD, servers, endpoints, networks, management tools)."),
        ("s5", "Exclusions & Justifications",
         "Lists what is explicitly out of scope and provides defensible justifications for each exclusion."),
        ("s6", "Stakeholders & External Dependencies",
         "Captures customers, regulators, and third parties/vendors that create scope requirements and dependencies."),
    ]

HELP_TEXT = (
    "The ISO 27001 Scope Document is a foundational piece of the Information Security Management System (ISMS). "
    "It is a formal, written statement that defines the exact boundaries of your information security program.\n\n"
    "Essentially, it answers the question: \"What exactly are we protecting, and where does our responsibility end?\""
)

COMMANDS_TEXT = (
    "Available commands:\n\n"
    "/help — more information\n"
    "/commands — available commands\n"
    "/fill — fill the scope document in conversation mode\n"
    "/autofill — load a specified version of the scope document (or samples)\n"
    "/load — load latest saved versions (non-v0) as buttons\n"
    "/submit — save as a new version\n"
    "/cancel — discard unsaved changes and reload the latest saved version\n"
    "/reset — reset to the baseline template (v0)\n"
    "/exit — exit fill mode\n"
)

# -------------------------
# Versioning helpers
# -------------------------

def list_versions_for_prefix(year: int, prefix: str) -> List[int]:
    d = get_data_dir()
    out: List[int] = []
    for p in d.glob(f"{prefix}*.json"):
        m = re.search(r"-v(\d+)\.json$", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))

def latest_saved_version(year: int) -> int:
    ensure_v0_exists(year)
    vs = list_versions_for_prefix(year, f"{year}-Scope-v")
    return max(vs) if vs else 0

def load_saved(year: int, version_num: int) -> Dict[str, Any]:
    p = get_data_dir() / f"{year}-Scope-v{version_num}.json"
    if not p.exists():
        ensure_v0_exists(year)
        p = get_data_dir() / f"{year}-Scope-v0.json"
    obj = read_json(p)
    obj.setdefault("meta", {})
    obj["meta"]["source_file"] = p.name
    return obj

def save_version_as(year: int, filename: str, obj: Dict[str, Any]) -> Path:
    p = get_data_dir() / filename
    write_json(p, obj)
    return p

def _parse_scope_filename(year: int, filename: str) -> Optional[Tuple[str, int]]:
    """
    Returns (group_key, version_num) for filenames like:
      {year}-Scope-v2.json               -> ("Base", 2)
      {year}-Scope-Financial-v3.json     -> ("Financial", 3)
      {year}-Scope-Draft-v10.json        -> ("Draft", 10)
    """
    # Base: 2026-Scope-v3.json
    m0 = re.match(rf"^{re.escape(str(year))}-Scope-v(\d+)\.json$", filename)
    if m0:
        return ("Base", int(m0.group(1)))

    # Named: 2026-Scope-Anything-v3.json
    m1 = re.match(rf"^{re.escape(str(year))}-Scope-(.+)-v(\d+)\.json$", filename)
    if m1:
        return (m1.group(1), int(m1.group(2)))

    return None

def discover_latest_non_v0_scope_files(year: int) -> List[LoadOption]:
    """
    Find every file in data/raw that matches {year}-Scope-*-vN.json (or Base {year}-Scope-vN.json),
    where N != 0. If multiple versions exist for the same group, keep only the latest version.

    IMPORTANT UI behavior:
      - button caption (label) MUST be the exact filename
      - button id MUST also be the exact filename
    """
    d = get_data_dir()
    best: Dict[str, Tuple[int, str]] = {}  # group -> (version, filename)

    # Include both patterns:
    # - 2026-Scope-v4.json
    # - 2026-Scope-Anything-v4.json
    for p in d.glob(f"{year}-Scope-*.json"):
        parsed = _parse_scope_filename(year, p.name)
        if not parsed:
            continue
        group, vnum = parsed
        if vnum == 0:
            continue
        cur = best.get(group)
        if (cur is None) or (vnum > cur[0]):
            best[group] = (vnum, p.name)

    # Sort: Base first, then name
    def sort_key(item: Tuple[str, Tuple[int, str]]) -> Tuple[int, str]:
        group = item[0]
        return (0 if group == "Base" else 1, group.lower())

    opts: List[LoadOption] = []
    for _, (_, fname) in sorted(best.items(), key=sort_key):
        # show exact filename as the button caption
        opts.append(LoadOption(id=fname, label=fname))

    return opts

def _looks_like_scope_filename(year: int, s: str) -> bool:
    s = (s or "").strip()
    if not s.lower().endswith(".json"):
        return False
    return _parse_scope_filename(year, s) is not None

def load_by_filename_if_exists(year: int, filename: str) -> Dict[str, Any]:
    """
    Safe-ish loader for /load button selections. Only allows files under data/raw
    that match the scope naming convention for the same year.
    """
    filename = (filename or "").strip()
    parsed = _parse_scope_filename(year, filename)
    if not parsed:
        raise FileNotFoundError(filename)

    p = get_data_dir() / filename
    if not p.exists():
        raise FileNotFoundError(filename)

    obj = read_json(p)
    obj.setdefault("meta", {})
    obj["meta"]["year"] = year
    obj["meta"]["source_file"] = p.name
    # keep meta.version as-is if present; otherwise infer
    if not obj["meta"].get("version"):
        _, vnum = parsed
        obj["meta"]["version"] = f"v{vnum}"
    return obj

# -------------------------
# API
# -------------------------

@router.post("/agent", response_model=AgentResponse)
def scope_agent(req: AgentRequest) -> AgentResponse:
    year = req.year
    ensure_v0_exists(year)

    draft = req.draft if req.draft is not None else load_saved(year, latest_saved_version(year))
    answer_raw = (req.answer or "").strip()

    cmd = req.command

    if cmd == "commands":
        return AgentResponse(message=COMMANDS_TEXT, draft=draft)

    if cmd == "help":
        return AgentResponse(message=HELP_TEXT, draft=draft)

    if cmd == "reset":
        fresh = load_saved(year, 0)
        _FILL_STATE[year] = {"in_fill": False, "active": None, "step": 0, "buffer": None, "exit_stage": 0}
        return AgentResponse(message="Returned to baseline template (v0).", draft=fresh, saved_version="v0")

    if cmd == "cancel":
        latest = load_saved(year, latest_saved_version(year))
        _FILL_STATE[year] = {"in_fill": False, "active": None, "step": 0, "buffer": None, "exit_stage": 0}
        return AgentResponse(
            message="Discarded unsaved changes and reloaded the latest saved version.",
            draft=latest,
            saved_version=latest.get("meta", {}).get("version"),
        )

    # -------------------------
    # /autofill (unchanged)
    # -------------------------
    if cmd == "autofill":
        if not answer_raw:
            opts = [
                LoadOption(id="sample_financial", label="Sample Scope Statement - Financial Industry"),
                LoadOption(id="sample_healthcare", label="Sample Scope Statement - Healthcare Industry"),
                LoadOption(id="sample_scope", label="Sample Scope"),
                LoadOption(id="base_scope", label="Base Scope Content"),
            ]
            return AgentResponse(
                message="Choose a scope content to load:",
                draft=draft,
                load_options=opts,
                next_question="__LOAD__",
            )

        # ✅ NEW: if frontend sends a filename, load it directly
        if _looks_like_scope_filename(year, answer_raw):
            try:
                loaded = load_by_filename_if_exists(year, answer_raw)
                return AgentResponse(
                    message=f"Loaded {loaded.get('meta', {}).get('source_file', answer_raw)}",
                    draft=loaded,
                    saved_version=loaded.get("meta", {}).get("version"),
                )
            except FileNotFoundError:
                return AgentResponse(message=f"Missing file: {answer_raw}", draft=draft)

        a = answer_raw.strip().lower()
        if a in ("sample_financial", "financial"):
            p = get_data_dir() / f"{year}-Scope-Financial-v0.json"
            if not p.exists():
                return AgentResponse(message=f"Missing file: {p.name}", draft=draft)
            loaded = read_json(p)
            loaded.setdefault("meta", {})
            loaded["meta"]["source_file"] = p.name
            return AgentResponse(message=f"Loaded {p.name}", draft=loaded, saved_version=loaded["meta"].get("version"))

        if a in ("sample_healthcare", "healthcare"):
            p = get_data_dir() / f"{year}-Scope-Healthcare-v0.json"
            if not p.exists():
                return AgentResponse(message=f"Missing file: {p.name}", draft=draft)
            loaded = read_json(p)
            loaded.setdefault("meta", {})
            loaded["meta"]["source_file"] = p.name
            return AgentResponse(message=f"Loaded {p.name}", draft=loaded, saved_version=loaded["meta"].get("version"))

        if a in ("sample_scope", "sample"):
            p = get_data_dir() / f"{year}-Scope-Sample-v0.json"
            if not p.exists():
                return AgentResponse(message=f"Missing file: {p.name}", draft=draft)
            loaded = read_json(p)
            loaded.setdefault("meta", {})
            loaded["meta"]["source_file"] = p.name
            return AgentResponse(
                message=f"Loaded {p.name}",
                draft=loaded,
                saved_version=loaded["meta"].get("version"),
            )

        if a in ("base_scope", "base", "v0"):
            p = get_data_dir() / f"{year}-Scope-v0.json"
            if not p.exists():
                ensure_v0_exists(year)
            loaded = read_json(p)
            loaded.setdefault("meta", {})
            loaded["meta"]["source_file"] = p.name
            return AgentResponse(
                message=f"Loaded {p.name}",
                draft=loaded,
                saved_version=loaded["meta"].get("version"),
            )

        ver = a
        if not ver.startswith("v"):
            ver = f"v{ver}"
        p = get_data_dir() / f"{year}-Scope-{ver}.json"
        if not p.exists():
            return AgentResponse(message=f"Version {ver} not found.", draft=draft)
        loaded = read_json(p)
        loaded.setdefault("meta", {})
        loaded["meta"]["source_file"] = p.name
        return AgentResponse(message=f"Loaded version {ver}.", draft=loaded, saved_version=loaded["meta"].get("version"))

    # -------------------------
    # /load (UPDATED)
    # Same button-driven flow as /autofill, but:
    # - discover every *non-v0* scope file
    # - if multiple versions exist for the same "group", only show the latest one
    # - button id is the exact filename to load
    # -------------------------
    if cmd == "load":
        if not answer_raw:
            opts = discover_latest_non_v0_scope_files(year)
            if not opts:
                return AgentResponse(
                    message=(
                        "No saved versions found (non-v0).\n\n"
                        "Tip: use /submit at least once to create v1+, then /load will show the latest versions."
                    ),
                    draft=draft,
                )
            return AgentResponse(
                message="Choose a saved version to load (latest per type):",
                draft=draft,
                load_options=opts,
                next_question="__LOAD__",
            )

        # answer_raw is expected to be the button id (filename)
        try:
            loaded = load_by_filename_if_exists(year, answer_raw)
            return AgentResponse(
                message=f"Loaded {loaded.get('meta', {}).get('source_file', answer_raw)}",
                draft=loaded,
                saved_version=loaded.get("meta", {}).get("version"),
            )
        except FileNotFoundError:
            # If the frontend sends something else, try to re-render options to recover gracefully.
            opts = discover_latest_non_v0_scope_files(year)
            if not opts:
                return AgentResponse(message="Selection not found, and no saved (non-v0) versions exist yet.", draft=draft)
            return AgentResponse(
                message="Selection not found. Please choose from the buttons:",
                draft=draft,
                load_options=opts,
                next_question="__LOAD__",
            )

    # -------------------------
    # /submit
    # -------------------------
    if cmd == "submit":
        src = (draft.get("meta", {}) or {}).get("source_file", "")
        if src == f"{year}-Scope-v0.json":
            out = copy.deepcopy(draft)
            out.setdefault("meta", {})
            out["meta"]["year"] = year
            out["meta"]["version"] = "v1"
            out["meta"]["source_file"] = f"{year}-Scope-Draft-v1.json"
            save_version_as(year, f"{year}-Scope-Draft-v1.json", out)
            update_system_scope_pointer(year, f"{year}-Scope-Draft-v1.json", status="In Progress")
            return AgentResponse(message=f"Saved baseline as {year}-Scope-Draft-v1.json.", draft=out, saved_version="v1")

        if src.endswith("-Scope-Sample-v1.json"):
            return AgentResponse(
                message=f"{src} is already the final version. No changes were saved.",
                draft=draft,
                saved_version=draft.get("meta", {}).get("version"),
            )

        v_latest = latest_saved_version(year)
        v_new = v_latest + 1
        out = copy.deepcopy(draft)
        out.setdefault("meta", {})
        out["meta"]["year"] = year
        out["meta"]["version"] = f"v{v_new}"
        out["meta"]["source_file"] = f"{year}-Scope-v{v_new}.json"
        save_version_as(year, f"{year}-Scope-v{v_new}.json", out)
        update_system_scope_pointer(year, f"{year}-Scope-v{v_new}.json", status="In Progress")
        return AgentResponse(
            message=f"Submitted. Saved new version as {year}-Scope-v{v_new}.json",
            draft=out,
            saved_version=f"v{v_new}",
        )

    # -------------------------
    # /fill (step-by-step)
    # -------------------------
    if cmd == "fill":
        state = _FILL_STATE.get(year) or {"in_fill": True, "active": None, "step": 0, "buffer": None, "exit_stage": 0}
        state["in_fill"] = True

        sections = _fill_sections()
        by_id = {sid: label for sid, label, _ in sections}
        help_map = {sid: help_text for sid, _, help_text in sections}

        sel_norm = answer_raw.strip().lower()

        if state.get("active") is None:
            if not answer_raw:
                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state
                return AgentResponse(
                    message="Fill mode started. Choose a section to work on:",
                    draft=draft,
                    load_options=opts,
                    next_question="__FILL__",
                )

            normalized = sel_norm
            if normalized.isdigit() and 1 <= int(normalized) <= 6:
                normalized = f"s{int(normalized)}"

            if normalized not in by_id:
                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message="Unknown section. Please choose one of the six sections shown.",
                    draft=draft,
                    load_options=opts,
                    next_question="__FILL__",
                )

            state["active"] = normalized
            state["step"] = 0
            state["buffer"] = {}
            state["exit_stage"] = 0
            _FILL_STATE[year] = state

            if normalized == "s1":
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Step 1/2 — Enter your Organization Name:"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )
            if normalized == "s2":
                state["buffer"] = {"items": []}
                _FILL_STATE[year] = state
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Enter a department / business unit / project name (one per message). Type **NA** to finish:"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )
            if normalized == "s3":
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Step 1/3 — Main Office Address (or NA):"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )
            if normalized == "s4":
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Step 1/4 — Identity Management system (e.g., AD / Azure AD tenant):"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )
            if normalized == "s5":
                state["buffer"] = {"items": []}
                _FILL_STATE[year] = state
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Enter an exclusion (one per message). Type **NA** to finish:"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )
            if normalized == "s6":
                return AgentResponse(
                    message=(
                        f"**{by_id[normalized]}**\n\n{help_map[normalized]}\n\n"
                        "Step 1/3 — Customers (or NA):"
                    ),
                    draft=draft,
                    next_question="__FILL__",
                )

        active = state.get("active")
        step = int(state.get("step") or 0)
        buf = state.get("buffer") or {}

        if not answer_raw:
            return AgentResponse(message="Please enter a value.", draft=draft, next_question="__FILL__")

        val = answer_raw
        is_na = val.strip().lower() == "na"

        # ---------- S1 ----------
        if active == "s1":
            if step == 0:
                buf["org"] = val
                state["buffer"] = buf
                state["step"] = 1
                _FILL_STATE[year] = state
                return AgentResponse(
                    message="Step 2/2 — Enter your Primary Business Function (or industry/business unit):",
                    draft=draft,
                    next_question="__FILL__",
                )

            if step == 1:
                buf["business"] = val
                out = copy.deepcopy(draft)
                _replace_everywhere(
                    out,
                    {
                        "[Organization Name]": buf["org"],
                        "[Primary Business Function, e.g., Financial Services / Software Development]": buf["business"],
                        "[Primary Business Function]": buf["business"],
                    },
                )
                out.setdefault("meta", {})
                out["meta"]["placeholders_retained"] = False

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message="✅ Updated Organization Name and Primary Business Function across the document.\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

        # ---------- S2 ----------
        if active == "s2":
            items = buf.get("items") if isinstance(buf, dict) else None
            if items is None:
                items = []
                buf = {"items": items}

            if is_na:
                clean = [x.strip() for x in items if x.strip()]
                out = copy.deepcopy(draft)
                sec = _get_section(out, "org_boundaries", title_prefix="2.")
                if sec is None:
                    return AgentResponse(message="⚠️ Could not find Section 2 in the document (id/title mismatch).", draft=draft, next_question="__FILL__")
                sec["bullets"] = clean

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message=f"✅ Updated Section 2 with {len(clean)} item(s).\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

            items.append(val)
            buf["items"] = items
            state["buffer"] = buf
            _FILL_STATE[year] = state
            return AgentResponse(message=f"Added: {val}\nAdd another, or type **NA** to finish:", draft=draft, next_question="__FILL__")

        # ---------- S3 ----------
        if active == "s3":
            if step == 0:
                buf["main"] = None if is_na else val
                state["buffer"] = buf
                state["step"] = 1
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 2/3 — Secondary Site/Data Center Address (or NA):", draft=draft, next_question="__FILL__")

            if step == 1:
                buf["secondary"] = None if is_na else val
                state["buffer"] = buf
                state["step"] = 2
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 3/3 — Remote Work Policy / Remote Coverage (or NA):", draft=draft, next_question="__FILL__")

            if step == 2:
                buf["remote"] = None if is_na else val

                out = copy.deepcopy(draft)
                sec = _get_section(out, "geo_boundaries", title_prefix="3.")
                if sec is None:
                    return AgentResponse(message="⚠️ Could not find Section 3 in the document (id/title mismatch).", draft=draft, next_question="__FILL__")

                tpls = sec.get("bullets") or []
                if len(tpls) < 3:
                    tpls = default_scope_template(year)["sections"][2]["bullets"]

                bullets: List[str] = []
                if buf.get("main"):
                    bullets.append(_replace_first_bracket_value(tpls[0], buf["main"]))
                if buf.get("secondary"):
                    bullets.append(_replace_first_bracket_value(tpls[1], buf["secondary"]))
                if buf.get("remote"):
                    line = _replace_first_bracket_value(tpls[2], buf["remote"])
                    bullets.append(line)

                sec["bullets"] = bullets

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message="✅ Updated Section 3 (removed any NA items).\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

        # ---------- S4 ----------
        if active == "s4":
            if step == 0:
                buf["identity"] = val
                state["buffer"] = buf
                state["step"] = 1
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 2/4 — Server Infrastructure (e.g., Hyper-V/VMware + server types):", draft=draft, next_question="__FILL__")

            if step == 1:
                buf["server"] = val
                state["buffer"] = buf
                state["step"] = 2
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 3/4 — Endpoint Management (e.g., Intune/Group Policy/SCCM):", draft=draft, next_question="__FILL__")

            if step == 2:
                buf["endpoint"] = val
                state["buffer"] = buf
                state["step"] = 3
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 4/4 — Network Infrastructure (e.g., LAN/WiFi/Firewalls/VPN):", draft=draft, next_question="__FILL__")

            if step == 3:
                buf["network"] = val

                out = copy.deepcopy(draft)
                sec = _get_section(out, "tech_boundaries", title_prefix="4.")
                if sec is None:
                    return AgentResponse(message="⚠️ Could not find Section 4 in the document (id/title mismatch).", draft=draft, next_question="__FILL__")

                tpls = sec.get("bullets") or []
                if len(tpls) < 4:
                    tpls = default_scope_template(year)["sections"][3]["bullets"]

                bullets: List[str] = []
                bullets.append(_replace_first_bracket_value(tpls[0], buf["identity"]))
                line2 = re.sub(r"\[[^\]]+\]", buf["server"], tpls[1])
                bullets.append(line2)
                bullets.append(_replace_first_bracket_value(tpls[2], buf["endpoint"]))
                bullets.append(f"Network Infrastructure: {buf['network']}")
                sec["bullets"] = bullets

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message="✅ Updated Section 4.\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

        # ---------- S5 ----------
        if active == "s5":
            items = buf.get("items") if isinstance(buf, dict) else None
            if items is None:
                items = []
                buf = {"items": items}

            if is_na:
                clean = [x.strip() for x in items if x.strip()]
                out = copy.deepcopy(draft)
                sec = _get_section(out, "exclusions", title_prefix="5.")
                if sec is None:
                    return AgentResponse(message="⚠️ Could not find Section 5 in the document (id/title mismatch).", draft=draft, next_question="__FILL__")
                sec["bullets"] = clean

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message=f"✅ Updated Section 5 with {len(clean)} exclusion(s).\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

            items.append(val)
            buf["items"] = items
            state["buffer"] = buf
            _FILL_STATE[year] = state
            return AgentResponse(message=f"Added: {val}\nAdd another, or type **NA** to finish:", draft=draft, next_question="__FILL__")

        # ---------- S6 ----------
        if active == "s6":
            if step == 0:
                buf["customers"] = None if is_na else val
                state["buffer"] = buf
                state["step"] = 1
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 2/3 — Regulators (or NA):", draft=draft, next_question="__FILL__")

            if step == 1:
                buf["regulators"] = None if is_na else val
                state["buffer"] = buf
                state["step"] = 2
                _FILL_STATE[year] = state
                return AgentResponse(message="Step 3/3 — Third-Party Vendors (or NA):", draft=draft, next_question="__FILL__")

            if step == 2:
                buf["vendors"] = None if is_na else val

                out = copy.deepcopy(draft)
                sec = _get_section(out, "stakeholders", title_prefix="6.")
                if sec is None:
                    return AgentResponse(message="⚠️ Could not find Section 6 in the document (id/title mismatch).", draft=draft, next_question="__FILL__")

                bullets: List[str] = []
                if buf.get("customers"):
                    bullets.append(f"Customers: {buf['customers']}")
                if buf.get("regulators"):
                    bullets.append(f"Regulators: {buf['regulators']}")
                if buf.get("vendors"):
                    bullets.append(f"Third-Party Vendors: {buf['vendors']}")
                sec["bullets"] = bullets

                state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
                _FILL_STATE[year] = state

                opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
                return AgentResponse(
                    message="✅ Updated Section 6 (removed any NA items).\n\nChoose another section, or type /exit to leave fill mode.",
                    draft=out,
                    load_options=opts,
                    next_question="__FILL__",
                )

        state.update({"active": None, "step": 0, "buffer": None, "exit_stage": 0})
        _FILL_STATE[year] = state
        opts = [LoadOption(id=sid, label=label) for sid, label, _ in sections]
        return AgentResponse(message="Fill state was reset (unexpected state). Choose a section:", draft=draft, load_options=opts, next_question="__FILL__")

    # -------------------------
    # /exit
    # -------------------------
    if cmd == "exit":
        state = _FILL_STATE.get(year) or {"in_fill": False, "active": None, "step": 0, "buffer": None, "exit_stage": 0}
        if not state.get("in_fill"):
            return AgentResponse(message="You're already in command mode.", draft=draft)

        sections = _fill_sections()
        active = state.get("active")

        if state.get("exit_stage", 0) == 0:
            state["exit_stage"] = 1
            _FILL_STATE[year] = state

            remaining = [LoadOption(id=sid, label=label) for sid, label, _ in sections if not active or sid != active]
            if not remaining:
                return AgentResponse(message="No remaining sections. Type /exit again to return to command mode.", draft=draft, next_question="__FILL__")

            return AgentResponse(message="Choose the next section to work on:", draft=draft, load_options=remaining, next_question="__FILL__")

        _FILL_STATE[year] = {"in_fill": False, "active": None, "step": 0, "buffer": None, "exit_stage": 0}
        return AgentResponse(message="Exited fill mode. Back to command mode.", draft=draft)

    return AgentResponse(message="Unknown command.", draft=draft)