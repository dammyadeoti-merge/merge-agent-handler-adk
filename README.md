
# Merge Agent Handler ADK Agent

This repo contains a minimal Google ADK agent that connects to Merge Agent Handler's MCP endpoint and can be deployed to Gemini Enterprise Agent Platform Runtime, then registered in Gemini Enterprise.

## Architecture

Gemini Enterprise -> ADK Agent on Agent Platform Runtime -> Merge Agent Handler MCP -> Tool Pack -> Registered User -> Connected SaaS accounts

This starter uses a **single shared registered user** and a **single tool pack** for initial Gemini Enterprise testing.

## Merge setup

In the Merge dashboard:

1. Create a Tool Pack.
2. Add the tools you want Gemini users to test.
3. Create a Registered User.
4. Link the relevant SaaS integrations for that Registered User.
5. Collect:
   - `MERGE_API_KEY`
   - `MERGE_TOOL_PACK_ID`
   - `MERGE_REGISTERED_USER_ID`

The agent connects to:

```text
POST https://ah-api.merge.dev/api/v1/tool-packs/{tool_pack_id}/registered-users/{registered_user_id}/mcp/
```

ADK's `McpToolset` calls `tools/list` to discover tool names and schemas, then proxies tool calls via `tools/call`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env, then:
set -a
source .env
set +a
```

## Deploy to Agent Platform Runtime

Authenticate and enable APIs first:

```bash
gcloud auth application-default login
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
gcloud services enable aiplatform.googleapis.com storage.googleapis.com
```

Then deploy:

```bash
python deploy.py
```

The deploy script prints an Agent Platform Reasoning Engine resource name. Keep that value for Gemini Enterprise registration.

## Register in Gemini Enterprise

In Google Cloud Console:

1. Go to Gemini Enterprise.
2. Open the Gemini Enterprise app where users will test the agent.
3. Go to Agents.
4. Click Add agent.
5. Choose Custom agent via Agent Platform.
6. Enter display name and description.
7. Paste the Agent Platform resource path printed by `deploy.py`.
8. Create the agent.
9. Share the agent with test users or groups.

## Phase 2: per-user routing

The starter repo uses one `MERGE_REGISTERED_USER_ID` for all Gemini users.

For production, keep the same org-level Merge API key and tool pack, but map:

```text
Gemini user email -> Merge registered_user_id
```

Then construct the MCP URL per request/session using the mapped registered user ID.

The key architectural change is that `registered_user_id` becomes dynamic while `tool_pack_id` usually remains stable.
