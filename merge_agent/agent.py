
"""ADK agent that connects Gemini/Agent Engine to Merge Agent Handler MCP.

This file is intentionally small:
- Merge owns the tool schemas through the Tool Pack.
- ADK's McpToolset discovers tools via tools/list.
- Tool calls are proxied to Agent Handler via tools/call.
"""

import os
from urllib.parse import urlencode

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


MERGE_API_KEY = _required_env("MERGE_API_KEY")
MERGE_TOOL_PACK_ID = _required_env("MERGE_TOOL_PACK_ID")
MERGE_REGISTERED_USER_ID = _required_env("MERGE_REGISTERED_USER_ID")

# Optional. Merge's MCP endpoint supports a format query parameter.
# Leave unset to use the endpoint default, or set MERGE_MCP_FORMAT=json / event-stream.
MERGE_MCP_FORMAT = os.getenv("MERGE_MCP_FORMAT", "").strip()

base_mcp_url = (
    "https://ah-api.merge.dev/api/v1/"
    f"tool-packs/{MERGE_TOOL_PACK_ID}/"
    f"registered-users/{MERGE_REGISTERED_USER_ID}/mcp/"
)

if MERGE_MCP_FORMAT:
    mcp_url = f"{base_mcp_url}?{urlencode({'format': MERGE_MCP_FORMAT})}"
else:
    mcp_url = base_mcp_url


root_agent = LlmAgent(
    model=os.getenv("ADK_MODEL", "gemini-flash-latest"),
    name="merge_agent_handler_assistant",
    description=(
        "Uses Merge Agent Handler tools to securely retrieve and act on "
        "business data from the customer's connected SaaS applications."
    ),
    instruction="""
You are an enterprise assistant connected to Merge Agent Handler.

Use the available Merge tools whenever the user asks for data or actions that
should come from connected SaaS systems. Do not invent IDs, records, fields, or
tool results. If a tool requires an identifier or required input that the user
has not provided, ask a concise follow-up question.

This initial implementation uses a shared registered user for testing in
Gemini Enterprise. Treat tool results as coming from that shared registered
user's connected accounts and tool pack.
""",
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_url,
                headers={
                    "Authorization": f"Bearer {MERGE_API_KEY}",
                    "Content-Type": "application/json",
                    # ADK/MCP HTTP transports commonly accept either JSON or event stream.
                    "Accept": "application/json, text/event-stream",
                },
            ),
            # Optional hardening: uncomment to expose only a subset of tools even if the
            # Tool Pack contains more. Prefer controlling this in the Merge dashboard.
            # tool_filter=["list_employees", "get_employee"],
        )
    ],
)
