# MCP Router Project Plan

## Vision

A lightweight, containerized **MCP router layer** running locally via Colima that:
1. Routes requests to daily-driver MCP servers
2. Uses Ollama to enhance prompts before forwarding to paid AI services
3. Provides unified tool access across desktop applications

## Target Integrations

### AI Services (Enhanced via Ollama)
- Claude MAX (Desktop & Code)
- VS Code + GitHub Copilot Pro
- Perplexity Pro (Desktop & Comet Browser)

### Desktop Applications
- Raycast
- Obsidian
- ComfyUI → Draw Things (image generation workflows)

### Future
- Web interface for customization

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Desktop Apps                              │
│  (Claude, VS Code, Perplexity, Raycast, Obsidian, ComfyUI)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Router (Container)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ HTTP Proxy  │──│ Ollama      │──│ MCP Server Aggregator   │  │
│  │ :9090       │  │ Prompt      │  │ (Context7, Desktop Cmdr,│  │
│  │             │  │ Enhancement │  │  Fetch, Sequential, etc)│  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Colima (Docker Runtime)                       │
│  - Ollama container (deepseek-r1, llama3, etc.)                 │
│  - MCP server containers                                         │
│  - Shared volumes for config/secrets                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Current)

### 1.1 Project Setup
- [x] Create workspace structure
- [x] Set up `.github/` for Copilot configuration
- [ ] Add `pyproject.toml` with dev dependencies
- [ ] Add `README.md` with project overview
- [ ] Add `.gitignore` for Python/Docker/secrets

### 1.2 Colima + Docker
- [ ] Install/configure Colima (`brew install colima`)
- [ ] Create `docker-compose.yml` for local stack
- [ ] Ollama container with GPU passthrough (if available)
- [ ] Volume mounts for model persistence

### 1.3 Reference Extraction
- [ ] Extract useful patterns from `mcp-example/`:
  - Keychain secrets management → adapt for Docker secrets
  - `proxy-config.json` structure → base for router config
  - Wrapper script patterns → containerized equivalents
- [ ] Remove `mcp-example/` symlink when done

---

## Phase 2: MCP Router Core

### 2.1 Router Service
- [ ] Create `router/` directory for main service
- [ ] HTTP server exposing MCP endpoints
- [ ] Configuration-driven server registration
- [ ] Health checks for upstream servers

### 2.2 Ollama Integration
- [ ] Prompt enhancement middleware
- [ ] Configurable enhancement rules per endpoint
- [ ] Fallback to direct routing if Ollama unavailable
- [ ] Caching layer for repeated prompts

### 2.3 MCP Server Containers
- [ ] Desktop Commander (file ops, terminal)
- [ ] Context7 (library docs)
- [ ] Sequential Thinking (reasoning)
- [ ] Fetch (web content)
- [ ] Custom servers as needed

---

## Phase 3: Desktop Integration

### 3.1 Application Configs
- [ ] Claude Desktop config pointing to router
- [ ] VS Code MCP settings
- [ ] Raycast MCP integration
- [ ] Obsidian plugin configuration

### 3.2 Image Generation Pipeline
- [ ] ComfyUI → Draw Things workflow
- [ ] MCP tools for image generation requests
- [ ] Prompt enhancement for image descriptions

---

## Phase 4: Web Interface

### 4.1 Dashboard
- [ ] Server status monitoring
- [ ] Configuration editor
- [ ] Prompt enhancement rules UI
- [ ] Usage analytics

---

## Files to Create

```
Insiders/
├── README.md                    # Project overview
├── pyproject.toml               # Python dependencies
├── .gitignore                   # Ignore patterns
├── .env.example                 # Environment template
├── docker-compose.yml           # Container orchestration
├── router/                      # Main router service
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── config.py                # Configuration loading
│   ├── middleware/
│   │   └── ollama_enhance.py    # Prompt enhancement
│   └── servers/                 # MCP server definitions
├── configs/                     # App-specific configs
│   ├── claude-desktop.json
│   ├── vscode-mcp.json
│   └── raycast.json
└── scripts/                     # Utility scripts
    ├── setup-colima.sh
    └── start-stack.sh
```

---

## Environment Variables

```bash
# .env.example
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=deepseek-r1
ROUTER_PORT=9090
LOG_LEVEL=info
```

---

## Next Steps

1. **Create `pyproject.toml`** with base dependencies (fastapi, httpx, pydantic)
2. **Create `docker-compose.yml`** with Ollama + router services
3. **Extract patterns** from `mcp-example/` before removing symlink
4. **Scaffold `router/`** with basic HTTP server

---

## Questions to Resolve

- [ ] GPU passthrough for Ollama in Colima - is it configured?
- [ ] Preferred framework for router? (FastAPI, aiohttp, or Go?)
- [ ] Should router run in container or native for development?
- [ ] Keychain secrets → how to handle in containers? (Docker secrets, env files, or Vault?)
