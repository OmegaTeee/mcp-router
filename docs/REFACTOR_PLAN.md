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

## Phase 1: Foundation ✅ COMPLETE

### 1.1 Project Setup
- [x] Create workspace structure
- [x] Set up `.github/` for Copilot configuration
- [x] Add `pyproject.toml` with dev dependencies
- [x] Add `README.md` with project overview
- [x] Add `.gitignore` for Python/Docker/secrets

### 1.2 Colima + Docker
- [x] Install/configure Colima (`brew install colima`)
- [x] Create `docker-compose.yml` for local stack
- [x] Ollama container with GPU passthrough (if available)
- [x] Volume mounts for model persistence

### 1.3 Reference Extraction
- [x] Refactor `mcp-example/`:
  - Keychain secrets management → adapt for Docker secrets
  - `proxy-config.json` structure → base for router config
  - Wrapper script patterns → containerized equivalents
- [x] Remove `mcp-example/` symlink when done

---

## Phase 2: MCP Router Core ✅ COMPLETE

### 2.1 Router Service
- [x] Create `router/` directory for main service
- [x] HTTP server exposing MCP endpoints (FastAPI on :9090)
- [x] Configuration-driven server registration
- [x] Health checks for upstream servers (`/health`, `/health/{server}`)

### 2.2 Ollama Integration
- [x] Prompt enhancement middleware (`middleware/enhance.py`)
- [x] Configurable enhancement rules per endpoint
- [x] Fallback to direct routing if Ollama unavailable
- [x] Caching layer for repeated prompts (Two-tier L1/L2)

### 2.3 MCP Server Containers
- [x] Desktop Commander (file ops, terminal)
- [x] Context7 (library docs)
- [x] Sequential Thinking (reasoning)
- [x] Fetch (web content)
- [x] Memory (persistent storage)

### 2.4 Additional Features (Beyond Original Plan)
- [x] Circuit breaker pattern for fault tolerance
- [x] SSE transport layer for Claude Desktop
- [x] STDIO adapter for Node.js MCP servers
- [x] Qdrant integration for semantic cache (L2)
- [x] Documentation pipeline to Obsidian
- [x] Path validation security for file operations
- [x] Production-safe reload configuration

---

## Phase 3: Desktop Integration 🟡 PARTIAL

### 3.1 Application Configs
- [x] Claude Desktop config pointing to router
- [x] VS Code MCP settings
- [x] Raycast MCP integration
- [x] Obsidian plugin configuration

### 3.2 Image Generation Pipeline
- [ ] ComfyUI → Draw Things workflow
- [ ] MCP tools for image generation requests
- [ ] Prompt enhancement for image descriptions

---

## Phase 4: Web Interface 🟡 PARTIAL

### 4.1 Dashboard
- [x] Server status monitoring (`/dashboard`)
- [ ] Configuration editor
- [ ] Prompt enhancement rules UI
- [x] Usage analytics (request logging)

---

## Current Project Structure

```
mcp-router/
├── README.md                    # Project overview
├── pyproject.toml               # Python dependencies
├── .gitignore                   # Ignore patterns
├── .env.example                 # Environment template
├── .env                         # Local environment (not committed)
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Router container image
├── mcp.json                     # Client config for testing router
├── router/                      # Main router service
│   ├── __init__.py
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Configuration loading
│   ├── models.py                # Pydantic models
│   ├── registry.py              # Server registry
│   ├── cache.py                 # Two-tier L1/L2 cache
│   ├── circuit_breaker.py       # Fault tolerance
│   ├── dashboard.py             # Web dashboard routes
│   ├── sse.py                   # SSE transport
│   ├── adapters/
│   │   └── stdio.py             # STDIO transport adapter
│   ├── middleware/
│   │   └── enhance.py           # Ollama enhancement
│   └── pipelines/
│       └── documentation.py     # Doc generation pipeline
├── configs/                     # Server configurations
│   ├── mcp-servers.json         # MCP server definitions
│   └── enhancement-rules.json   # Enhancement rules
├── client-configs/              # App-specific configs
│   ├── claude-desktop.json
│   ├── vscode-mcp.json
│   ├── raycast-mcp-query.sh
│   └── obsidian-mcp.json
├── scripts/                     # Utility scripts
│   ├── gen-env-from-ks.sh       # Generate .env from Keychain
│   └── create-api-keys.sh
├── templates/                   # Dashboard templates
└── docs/                        # Documentation
    ├── ARCHITECTURE.md
    ├── REFACTOR_PLAN.md
    └── decisions/
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
QDRANT_URL=http://localhost:6333  # Optional L2 cache
```

---

## Next Steps

1. **Phase 3 completion**: Implement ComfyUI → Draw Things pipeline
2. **Phase 4 completion**: Add configuration editor and rules UI
3. **Testing**: Add unit tests for core modules (circuit breaker, cache, registry)
4. **Documentation**: Update ARCHITECTURE.md with new features

---

## Resolved Questions

- [x] GPU passthrough for Ollama in Colima - configured via docker-compose
- [x] Preferred framework for router? → FastAPI
- [x] Should router run in container or native? → Both supported
- [x] Keychain secrets → `scripts/gen-env-from-ks.sh` generates .env
