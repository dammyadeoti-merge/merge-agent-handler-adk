
# Gemini Enterprise registration notes

Deploying the ADK code and registering it in Gemini Enterprise are separate steps.

## Deploying the code

Use `python deploy.py` from this repo to create a Reasoning Engine / Agent Platform Runtime resource.

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
