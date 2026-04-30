
# Gemini Enterprise registration notes

Deploying the ADK code and registering it in Gemini Enterprise are separate steps.

## Deploying the code

Before running `deploy.py`, configure your routing mode and the corresponding env vars in your shell or `.env` file — see the [README](../README.md) for the full list. The deploy script reads `MERGE_USER_ROUTING_MODE` and `MERGE_TOOL_PACK_ROUTING_MODE` to determine which env vars to pass to the deployed agent, so the routing configuration must be set correctly before deployment.

```bash
python deploy.py
```

This creates a Reasoning Engine / Agent Platform Runtime resource and prints the resource name needed for Gemini Enterprise registration.

## Registering the deployed agent

Gemini Enterprise provides a Google Cloud Console flow to register an already-deployed ADK agent:

- Gemini Enterprise
- Select app
- Agents
- Add agent
- Custom agent via Agent Platform
- Paste Agent Platform resource path

## UI deployment note

The console flow is available for registration and sharing. Actual ADK code deployment is typically done through Agent Platform Runtime deployment mechanisms such as the Python SDK, source files, container images, or Developer Connect for Git-based workflows.
