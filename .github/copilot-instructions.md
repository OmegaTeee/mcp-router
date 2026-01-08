# MCP Router - AI Coding Agent Workspace

Containerized MCP router layer for enhancing prompts via Ollama before forwarding to paid AI services.

## Project Structure

```
Insiders/
├── .github/
│   ├── agents/               # Copilot chat modes (custom agents)
│   ├── instructions/         # Context-specific instruction files
│   ├── prompts/              # Reusable prompt templates
│   └── copilot-instructions.md
├── router/                   # FastAPI router service
│   ├── __init__.py
│   ├── config.py             # Pydantic settings from .env
│   └── main.py               # FastAPI app with /ollama/enhance endpoint
├── scripts/
│   └── gen-env-from-ks.sh    # Generate .env from Keychain via ks
├── .venv/                    # Python virtual environment
├── docker-compose.yml        # Container orchestration
├── Dockerfile                # Router container image
├── pyproject.toml            # Python dependencies
└── REFACTOR_PLAN.md          # Project roadmap (start here)
```

## Target Stack

- **Runtime**: Colima (Docker on macOS)
- **Prompt Enhancement**: Ollama (deepseek-r1, llama3)
- **Router**: FastAPI HTTP proxy aggregating MCP servers
- **Clients**: Claude MAX, VS Code/Copilot, Perplexity, Raycast, Obsidian

## Key Files

| Location | Purpose |
|----------|---------|
| `REFACTOR_PLAN.md` | Full roadmap and architecture |
| `.github/agents/*.agent.md` | Custom Copilot chat modes |
| `.github/prompts/*.prompt.md` | Reusable prompt templates |
| `.github/instructions/*.instructions.md` | MCP server development guides |

## Conventions

- **Agents** (`*.agent.md`) - Copilot chat modes with specific expertise
- **Prompts** (`*.prompt.md`) - Reusable templates invoked with `#`
- **Instructions** (`*.instructions.md`) - Auto-apply based on `applyTo` globs
- Python environment: `.venv/` at workspace root

## Secrets Management

Uses `ks` CLI (Keychain Secrets manager) to store secrets in macOS Keychain:

```bash
# Add a secret
ks add obsidian_api_key "your-api-key"

# Generate .env from Keychain
./scripts/gen-env-from-ks.sh
```

## Development Workflow

```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run router locally (connects to native Ollama)
uvicorn router.main:app --reload --port 9090

# Or run full stack in containers
docker compose up -d
```
