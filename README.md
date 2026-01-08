# MCP Router

A lightweight, containerized MCP (Model Context Protocol) router that enhances prompts via Ollama before forwarding to AI services.

## Features

- **Prompt Enhancement**: Uses local Ollama models (deepseek-r1, llama3) to improve prompts
- **MCP Aggregation**: Single HTTP endpoint for multiple MCP servers
- **Containerized**: Runs in Docker via Colima on macOS
- **Keychain Integration**: Secrets managed via `ks` CLI

## Target Clients

- Claude MAX (Desktop & Code)
- VS Code + GitHub Copilot Pro
- Perplexity Pro (Desktop & Comet)
- Raycast
- Obsidian
- ComfyUI → Draw Things

## Quick Start

### Prerequisites

```bash
# Install Colima and Docker
brew install colima docker

# Install ks (Keychain Secrets manager)
brew tap loteoo/formulas && brew install ks
ks init

# Start Colima
colima start
```

### Setup

```bash
# Clone and enter project
cd ~/Projects/Insiders

# Generate .env from Keychain secrets
./scripts/gen-env-from-ks.sh

# Start the stack
docker compose up -d

# Check status
docker compose ps
```

### Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run locally (without Docker)
uvicorn router.main:app --reload --port 9090
```

## Architecture

```
Desktop Apps → MCP Router (:9090) → Ollama Enhancement → MCP Servers
                    │
                    ├── /context7/
                    ├── /desktop-commander/
                    ├── /sequential-thinking/
                    ├── /fetch/
                    └── /ollama/
```

## Configuration

### Environment Variables

See `.env.example` for all options. Generate from Keychain:

```bash
./scripts/gen-env-from-ks.sh
```

### Adding Secrets

```bash
# Add a secret to Keychain
ks add obsidian_api_key "your-api-key"

# Regenerate .env
./scripts/gen-env-from-ks.sh
```

## Project Structure

```
├── router/              # FastAPI router service
├── configs/             # Application-specific MCP configs
├── scripts/             # Utility scripts
├── docker-compose.yml   # Container orchestration
└── .github/             # Copilot agents, prompts, instructions
```

## License

MIT
