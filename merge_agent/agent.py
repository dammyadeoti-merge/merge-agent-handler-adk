"""ADK agent that connects Gemini/Agent Engine to Merge Agent Handler MCP.

This file is intentionally small:
- Merge owns the tool schemas through the Tool Pack.
- PerUserMcpToolset resolves the correct Registered User and Tool Pack per
  invocation based on MERGE_USER_ROUTING_MODE and MERGE_TOOL_PACK_ROUTING_MODE.
- ADK's McpToolset (wrapped inside PerUserMcpToolset) discovers tools via
  tools/list and proxies calls via tools/call.
"""

import json
import os

from google.adk.agents import LlmAgent

from merge_agent.toolset import PerUserMcpToolset


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ── Routing mode ──────────────────────────────────────────────────────────────
USER_ROUTING = os.getenv("MERGE_USER_ROUTING_MODE", "static").strip().lower()
TOOL_PACK_ROUTING = os.getenv("MERGE_TOOL_PACK_ROUTING_MODE", "static").strip().lower()

_VALID_USER_MODES = {"static", "dynamic"}
_VALID_TOOL_PACK_MODES = {"static", "dynamic"}

if USER_ROUTING not in _VALID_USER_MODES:
    raise RuntimeError(
        f"MERGE_USER_ROUTING_MODE must be 'static' or 'dynamic', got '{USER_ROUTING}'"
    )
if TOOL_PACK_ROUTING not in _VALID_TOOL_PACK_MODES:
    raise RuntimeError(
        f"MERGE_TOOL_PACK_ROUTING_MODE must be 'static' or 'dynamic', "
        f"got '{TOOL_PACK_ROUTING}'"
    )
if USER_ROUTING == "static" and TOOL_PACK_ROUTING == "dynamic":
    raise RuntimeError(
        "Invalid configuration: MERGE_TOOL_PACK_ROUTING_MODE=dynamic requires "
        "MERGE_USER_ROUTING_MODE=dynamic"
    )

# ── Credentials ───────────────────────────────────────────────────────────────
MERGE_API_KEY = _required_env("MERGE_API_KEY")

# ── Static mode vars ──────────────────────────────────────────────────────────
STATIC_USER_ID = os.getenv("MERGE_REGISTERED_USER_ID", "")
STATIC_TOOL_PACK_ID = os.getenv("MERGE_TOOL_PACK_ID", "")

if USER_ROUTING == "static" and not STATIC_USER_ID:
    raise RuntimeError(
        "MERGE_REGISTERED_USER_ID is required when MERGE_USER_ROUTING_MODE=static"
    )
if TOOL_PACK_ROUTING == "static" and not STATIC_TOOL_PACK_ID:
    raise RuntimeError(
        "MERGE_TOOL_PACK_ID is required when MERGE_TOOL_PACK_ROUTING_MODE=static"
    )

# ── Dynamic tool pack vars ────────────────────────────────────────────────────
TEAM_GROUPING_KEY = os.getenv("MERGE_TEAM_GROUPING_KEY", "Team").strip()

if TOOL_PACK_ROUTING == "dynamic":
    _map_file = os.getenv("MERGE_TOOL_PACK_MAP_FILE", "").strip()
    _map_raw = os.getenv("MERGE_TOOL_PACK_MAP", "").strip()
    if _map_file:
        try:
            with open(_map_file) as _f:
                TOOL_PACK_MAP: dict[str, str] = json.load(_f)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Could not load MERGE_TOOL_PACK_MAP_FILE '{_map_file}': {exc}"
            ) from exc
    elif _map_raw:
        try:
            TOOL_PACK_MAP = json.loads(_map_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"MERGE_TOOL_PACK_MAP is not valid JSON: {exc}"
            ) from exc
    else:
        raise RuntimeError(
            "MERGE_TOOL_PACK_ROUTING_MODE=dynamic requires either "
            "MERGE_TOOL_PACK_MAP_FILE (path to a JSON file) or MERGE_TOOL_PACK_MAP "
            "(JSON string). Neither is set."
        )
    if not TOOL_PACK_MAP:
        raise RuntimeError(
            "Tool pack map must not be empty when MERGE_TOOL_PACK_ROUTING_MODE=dynamic"
        )
else:
    TOOL_PACK_MAP = {}

# ── Optional ──────────────────────────────────────────────────────────────────
MCP_FORMAT = os.getenv("MERGE_MCP_FORMAT", "").strip()

root_agent = LlmAgent(
    model=os.getenv("ADK_MODEL", "gemini-flash-latest"),
    name="merge_agent_handler_assistant",
    description=(
        "Uses Merge Agent Handler tools to securely retrieve and act on "
        "business data from the user's connected SaaS applications."
    ),
    instruction="""
You are an enterprise assistant connected to Merge Agent Handler.

Use the available Merge tools whenever the user asks for data or actions that
should come from connected SaaS systems. Do not invent IDs, records, fields, or
tool results. If a tool requires an identifier or required input that the user
has not provided, ask a concise follow-up question.

If the only available tool is `account_not_configured`, call it immediately
and relay its response verbatim to the user without modification.
""",
    tools=[
        PerUserMcpToolset(
            merge_api_key=MERGE_API_KEY,
            user_routing_mode=USER_ROUTING,
            tool_pack_routing_mode=TOOL_PACK_ROUTING,
            static_registered_user_id=STATIC_USER_ID,
            static_tool_pack_id=STATIC_TOOL_PACK_ID,
            team_grouping_key=TEAM_GROUPING_KEY,
            tool_pack_map=TOOL_PACK_MAP,
            mcp_format=MCP_FORMAT,
        )
    ],
)
