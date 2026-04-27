
"""Deploy this ADK agent to Gemini Enterprise Agent Platform Runtime.

Run from the repository root:

    export GOOGLE_CLOUD_PROJECT="your-gcp-project"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    export MERGE_API_KEY="..."
    export MERGE_TOOL_PACK_ID="..."
    export MERGE_REGISTERED_USER_ID="..."

    python deploy.py

The script prints the Agent Platform Reasoning Engine resource name.
Use that resource path when registering the agent in Gemini Enterprise.
"""

import os
import vertexai

from merge_agent.agent import root_agent


PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

# For production, prefer Secret Manager for MERGE_API_KEY. This sample passes
# env vars at deployment time for a quick proof of concept.
env_vars = {
    "MERGE_API_KEY": os.environ["MERGE_API_KEY"],
    "MERGE_TOOL_PACK_ID": os.environ["MERGE_TOOL_PACK_ID"],
    "MERGE_REGISTERED_USER_ID": os.environ["MERGE_REGISTERED_USER_ID"],
    "ADK_MODEL": os.getenv("ADK_MODEL", "gemini-flash-latest"),
}

if os.getenv("MERGE_MCP_FORMAT"):
    env_vars["MERGE_MCP_FORMAT"] = os.environ["MERGE_MCP_FORMAT"]

remote_agent = client.agent_engines.create(
    agent=root_agent,
    config={
        "display_name": os.getenv("AGENT_DISPLAY_NAME", "Merge Agent Handler Assistant"),
        "description": (
            "ADK agent that uses Merge Agent Handler MCP tools through a "
            "shared registered user and tool pack."
        ),
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]>=1.112.0",
            "mcp>=1.9.0",
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
