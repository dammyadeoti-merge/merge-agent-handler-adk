
# Merge Agent Handler ADK Agent

This repo contains a minimal Google ADK agent that connects to Merge Agent Handler's MCP endpoint and can be deployed to Gemini Enterprise Agent Platform Runtime, then registered in Gemini Enterprise.

## Architecture

Gemini Enterprise -> ADK Agent on Agent Platform Runtime -> Merge Agent Handler MCP -> Tool Pack -> Registered User -> Connected SaaS accounts

Supports static (shared) or dynamic (per-user) routing for both Registered Users and Tool Packs — see [Routing modes](#routing-modes).

## Merge setup

In the Merge dashboard:

1. Create a Tool Pack.
2. Add the tools you want Gemini users to test.
3. Create a Registered User for each person who will use the agent.
   - Set `origin_user_id` to the user's **Google Workspace email address** (e.g. `user@yourcompany.com`). This is how the agent maps a Gemini Enterprise session to the correct Registered User at runtime.
   - Set `origin_user_name` to the user's display name.
   - If you plan to use **dynamic tool pack mapping**, populate `custom_groupings` with the team key you configure in `MERGE_TEAM_GROUPING_KEY` (default: `"Team"`). For example: `"custom_groupings": { "Team": "Engineering" }`. Users without this grouping, or whose team is not present in `tool_pack_map.json`, will fall back to the `"default"` entry in that file.
4. Link the relevant SaaS integrations for each Registered User.
5. Collect:
   - `MERGE_API_KEY`
   - `MERGE_TOOL_PACK_ID` (static tool pack routing only)
   - `MERGE_REGISTERED_USER_ID` (static user routing only)
   - Tool Pack UUIDs per team (dynamic tool pack routing — entered in `tool_pack_map.json`)

The agent connects to:

```text
POST https://ah-api.merge.dev/api/v1/tool-packs/{tool_pack_id}/registered-users/{registered_user_id}/mcp/
```

`PerUserMcpToolset` resolves the correct Registered User and Tool Pack per session, then delegates to `McpToolset` which calls `tools/list` to discover tool names and schemas and proxies tool calls via `tools/call`.

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

If using dynamic tool pack routing, also copy and fill in the tool pack map:

```bash
cp tool_pack_map.example.json tool_pack_map.json
# Fill in tool_pack_map.json with your team → Tool Pack UUID mappings
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

## Routing modes

The agent supports three routing configurations, set via `MERGE_USER_ROUTING_MODE` and `MERGE_TOOL_PACK_ROUTING_MODE` in your `.env`:

| User routing | Tool pack routing | Behavior |
|---|---|---|
| `static` | `static` | Single shared Registered User and Tool Pack for all Gemini users (default, good for initial testing) |
| `dynamic` | `static` | Each Gemini user is mapped to their own Registered User via email; all users share one Tool Pack |
| `dynamic` | `dynamic` | Each Gemini user is mapped to their own Registered User, and their Tool Pack is determined by their team grouping |

`static + dynamic` is an invalid combination and will raise an error at startup.

### Dynamic user routing

Set `MERGE_USER_ROUTING_MODE=dynamic`. The agent reads the authenticated Gemini Enterprise user's email from the session and calls `GET /api/v1/registered-users/?origin_user_id=<email>` to resolve their Merge Registered User. This is why `origin_user_id` must be set to the user's email when creating Registered Users (see [Merge setup](#merge-setup)).

If no Registered User is found for the email, the agent responds with an error message rather than accessing any tools.

### Dynamic tool pack routing

Set `MERGE_TOOL_PACK_ROUTING_MODE=dynamic` (requires `MERGE_USER_ROUTING_MODE=dynamic`). Copy `tool_pack_map.example.json` to `tool_pack_map.json` and fill in your Tool Pack UUIDs:

```bash
cp tool_pack_map.example.json tool_pack_map.json
```

```json
{
  "Engineering": "your-tool-pack-uuid-for-engineering",
  "Sales": "your-tool-pack-uuid-for-sales",
  "default": "your-default-tool-pack-uuid"
}
```

Set `MERGE_TEAM_GROUPING_KEY` to match the key you use in `custom_groupings` when creating Registered Users (defaults to `"Team"`). Point `MERGE_TOOL_PACK_MAP_FILE` at your file in `.env`:

```bash
MERGE_TEAM_GROUPING_KEY=Team
MERGE_TOOL_PACK_MAP_FILE=./tool_pack_map.json
```

At runtime the agent reads the user's `custom_groupings[MERGE_TEAM_GROUPING_KEY]` value from their Registered User record and uses it to select the correct Tool Pack. Users with a missing or unmapped team fall back to the `"default"` entry. If no `"default"` is configured, the agent responds with an error. `tool_pack_map.json` is gitignored — only the example template is committed.

## Reference

- [Agent Handler API Reference](https://docs.merge.dev/merge-agent-handler/agent-handler)
- [Google Agent Development Kit Documentation](https://adk.dev/get-started/python/)
- [Google: Register and Manage ADK Agents on Gemini Enterprise Agent Platform](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-adk-agent?utm_source=chatgpt.com)

