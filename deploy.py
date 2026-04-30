"""Deploy this ADK agent to Gemini Enterprise Agent Platform Runtime.

Run from the repository root:

    export GOOGLE_CLOUD_PROJECT="your-gcp-project"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    export MERGE_API_KEY="..."

    # Static routing (default):
    export MERGE_USER_ROUTING_MODE="static"
    export MERGE_TOOL_PACK_ROUTING_MODE="static"
    export MERGE_TOOL_PACK_ID="..."
    export MERGE_REGISTERED_USER_ID="..."

    # Dynamic user routing:
    export MERGE_USER_ROUTING_MODE="dynamic"
    export MERGE_TOOL_PACK_ROUTING_MODE="static"
    export MERGE_TOOL_PACK_ID="..."

    # Full dynamic routing:
    export MERGE_USER_ROUTING_MODE="dynamic"
    export MERGE_TOOL_PACK_ROUTING_MODE="dynamic"
    export MERGE_TEAM_GROUPING_KEY="Team"
    export MERGE_TOOL_PACK_MAP='{"Engineering": "uuid-1", "Sales": "uuid-2", "default": "uuid-fallback"}'

    python deploy.py

The script prints the Agent Platform Reasoning Engine resource name.
Use that resource path when registering the agent in Gemini Enterprise.
"""

import json
import os
import vertexai

from merge_agent.agent import root_agent


PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

USER_ROUTING = os.getenv("MERGE_USER_ROUTING_MODE", "static").strip().lower()
TOOL_PACK_ROUTING = os.getenv("MERGE_TOOL_PACK_ROUTING_MODE", "static").strip().lower()

client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

# For production, prefer Secret Manager for MERGE_API_KEY. This sample passes
# env vars at deployment time for a quick proof of concept.
env_vars: dict[str, str] = {
    "MERGE_API_KEY": os.environ["MERGE_API_KEY"],
    "MERGE_USER_ROUTING_MODE": USER_ROUTING,
    "MERGE_TOOL_PACK_ROUTING_MODE": TOOL_PACK_ROUTING,
    "ADK_MODEL": os.getenv("ADK_MODEL", "gemini-flash-latest"),
}

# Static registered user — only needed in static user routing mode
if USER_ROUTING == "static":
    env_vars["MERGE_REGISTERED_USER_ID"] = os.environ["MERGE_REGISTERED_USER_ID"]

# Static tool pack — only needed in static tool pack routing mode
if TOOL_PACK_ROUTING == "static":
    env_vars["MERGE_TOOL_PACK_ID"] = os.environ["MERGE_TOOL_PACK_ID"]

# Dynamic tool pack vars — only needed in dynamic tool pack routing mode
if TOOL_PACK_ROUTING == "dynamic":
    env_vars["MERGE_TEAM_GROUPING_KEY"] = os.getenv("MERGE_TEAM_GROUPING_KEY", "Team")
    # Prefer a local JSON file (MERGE_TOOL_PACK_MAP_FILE); fall back to the raw
    # env var string. Either way, the deployed agent receives a JSON string via
    # MERGE_TOOL_PACK_MAP since files aren't guaranteed to be accessible at runtime.
    _map_file = os.getenv("MERGE_TOOL_PACK_MAP_FILE", "").strip()
    if _map_file:
        with open(_map_file) as _f:
            env_vars["MERGE_TOOL_PACK_MAP"] = json.dumps(json.load(_f))
    else:
        env_vars["MERGE_TOOL_PACK_MAP"] = os.environ["MERGE_TOOL_PACK_MAP"]

if os.getenv("MERGE_MCP_FORMAT"):
    env_vars["MERGE_MCP_FORMAT"] = os.environ["MERGE_MCP_FORMAT"]

remote_agent = client.agent_engines.create(
    agent=root_agent,
    config={
        "display_name": os.getenv("AGENT_DISPLAY_NAME", "Merge Agent Handler Assistant"),
        "description": (
            "ADK agent that uses Merge Agent Handler MCP tools with configurable "
            "static or dynamic routing for Registered Users and Tool Packs."
        ),
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]>=1.112.0",
            "mcp>=1.9.0",
            "httpx>=0.27.0",
        ],
        "env_vars": env_vars,
        "agent_framework": "google-adk",
    },
)

print("\nDeployed agent:")
print(remote_agent)

resource_name = (
    getattr(remote_agent, "resource_name", None)
    or getattr(getattr(remote_agent, "api_resource", None), "name", None)
    or getattr(remote_agent, "name", None)
)

if resource_name:
    print("\nAgent Platform resource name:")
    print(resource_name)
    if not str(resource_name).startswith("https://"):
        print("\nGemini Enterprise may ask for this as:")
        print(f"https://{LOCATION}-aiplatform.googleapis.com/v1/{resource_name}")
else:
    print("\nCould not infer resource name automatically. Inspect the object above.")
