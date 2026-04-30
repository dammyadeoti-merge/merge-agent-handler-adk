"""Per-user MCP toolset that resolves Registered User and Tool Pack per invocation."""

from __future__ import annotations

import json
from typing import Optional
from urllib.parse import urlencode

import httpx
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_MERGE_API_BASE = "https://ah-api.merge.dev/api/v1"


def _error_tool(message: str) -> FunctionTool:
    """Returns a FunctionTool that surfaces a hard-fail message to the LLM."""
    async def account_not_configured() -> str:
        return message
    account_not_configured.__doc__ = message
    return FunctionTool(func=account_not_configured)


def _build_mcp_url(tool_pack_id: str, registered_user_id: str, mcp_format: str) -> str:
    base = (
        f"{_MERGE_API_BASE}/tool-packs/{tool_pack_id}/"
        f"registered-users/{registered_user_id}/mcp/"
    )
    if mcp_format:
        return f"{base}?{urlencode({'format': mcp_format})}"
    return base


class PerUserMcpToolset(BaseToolset):
    """Builds a per-invocation MCP connection using Merge routing configuration.

    Routing is controlled by two independent modes:

    user_routing_mode="static"   → registered_user_id comes from static_registered_user_id
    user_routing_mode="dynamic"  → registered_user_id is resolved by looking up the Gemini
                                   Enterprise caller's email (session.user_id) against
                                   GET /api/v1/registered-users/?origin_user_id=<email>

    tool_pack_routing_mode="static"  → tool_pack_id comes from static_tool_pack_id
    tool_pack_routing_mode="dynamic" → tool_pack_id is resolved from the Registered User's
                                       custom_groupings[team_grouping_key] via tool_pack_map.
                                       Falls back to tool_pack_map["default"] if the team
                                       key is missing or unmapped.

    If lookup fails in dynamic mode, get_tools() returns a single account_not_configured
    tool so the agent can surface a clear error message to the user.
    """

    def __init__(
        self,
        *,
        merge_api_key: str,
        user_routing_mode: str,
        tool_pack_routing_mode: str,
        static_registered_user_id: str = "",
        static_tool_pack_id: str = "",
        team_grouping_key: str = "Team",
        tool_pack_map: Optional[dict[str, str]] = None,
        mcp_format: str = "",
    ) -> None:
        self._api_key = merge_api_key
        self._user_routing = user_routing_mode
        self._tool_pack_routing = tool_pack_routing_mode
        self._static_user_id = static_registered_user_id
        self._static_tool_pack_id = static_tool_pack_id
        self._team_key = team_grouping_key
        self._tool_pack_map: dict[str, str] = tool_pack_map or {}
        self._mcp_format = mcp_format
        # Keyed by invocation_id to support concurrent sessions safely.
        self._mcp_toolsets: dict[str, McpToolset] = {}

    async def _lookup_registered_user(self, email: str) -> Optional[dict]:
        params = {"origin_user_id": email}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_MERGE_API_BASE}/registered-users/",
                params=params,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None

    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> list[BaseTool]:
        # ── 1. Resolve registered_user_id ────────────────────────────────────
        registered_user: Optional[dict] = None

        if self._user_routing == "dynamic":
            email = readonly_context.user_id if readonly_context else ""
            registered_user = await self._lookup_registered_user(email)
            if not registered_user:
                return [_error_tool(
                    f"Your Gemini Enterprise account ({email}) is not set up as a "
                    "Merge Agent Handler Registered User. "
                    "Please contact your administrator."
                )]
            registered_user_id = registered_user["id"]
        else:
            registered_user_id = self._static_user_id

        # ── 2. Resolve tool_pack_id ───────────────────────────────────────────
        if self._tool_pack_routing == "dynamic":
            groupings: dict = (
                (registered_user or {})
                .get("shared_credential_group") or {}
            ).get("custom_groupings", {})

            team = groupings.get(self._team_key)
            tool_pack_id = (
                self._tool_pack_map.get(team or "")
                or self._tool_pack_map.get("default")
            )
            if not tool_pack_id:
                label = (
                    f"team '{team}'" if team
                    else "your account (no team grouping found)"
                )
                return [_error_tool(
                    f"No Tool Pack is configured for {label} and no 'default' "
                    "fallback exists in MERGE_TOOL_PACK_MAP. "
                    "Please contact your administrator."
                )]
        else:
            tool_pack_id = self._static_tool_pack_id

        # ── 3. Build per-invocation McpToolset ───────────────────────────────
        mcp_url = _build_mcp_url(tool_pack_id, registered_user_id, self._mcp_format)
        toolset = McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
        )

        inv_id = (
            readonly_context.invocation_id
            if readonly_context and hasattr(readonly_context, "invocation_id")
            else "default"
        )
        self._mcp_toolsets[inv_id] = toolset
        return await toolset.get_tools(readonly_context)

    async def close(self) -> None:
        for ts in self._mcp_toolsets.values():
            try:
                await ts.close()
            except Exception:
                pass
        self._mcp_toolsets.clear()
