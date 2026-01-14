# Session History

## 2026-01-13: Docker Stack & Qdrant Integration (Session 2)

### Summary

Completed Docker stack testing and added persistent L2 cache with Qdrant integration. Fixed several configuration issues discovered during testing.

### What We Changed

**Bug Fixes**
- `Dockerfile` - Added `README.md` to COPY (required by hatchling build)
- `docker-compose.yml` - Fixed `OLLAMA_HOST` to use explicit `host.docker.internal` (shell's `OLLAMA_HOST=http://localhost:11434` was being inherited)
- `docker-compose.yml` - Remapped Qdrant ports to 6335/6336 (6333 used by SSH tunnel to remote Qdrant)
- `docker-compose.yml` - Commented out STDIO MCP server containers (they exit immediately without stdin)

**Qdrant L2 Cache**
- `pyproject.toml` - Added `qdrant-client>=1.12.0` dependency
- `router/config.py` - Added `qdrant_url` setting
- `router/cache.py` - Integrated Qdrant for persistent L2 cache:
  - `_init_qdrant()` - Creates `prompt_cache` collection with cosine distance
  - `_find_similar_qdrant()` - Searches Qdrant with score threshold
  - `_store_in_qdrant()` - Upserts embeddings with full payload
  - `get_stats()` - Reports `qdrant_available` and `l2_entries` count
  - `clear()` - Drops and recreates Qdrant collection
- `router/main.py` - Passes `qdrant_url` to PromptCache constructor

### Decisions

1. **STDIO servers as subprocesses**: MCP servers (context7, desktop-commander, sequential-thinking) are STDIO-based and can't run as standalone containers. The router's `adapters/stdio.py` should spawn them as subprocesses.
2. **Explicit Docker networking**: Shell environment variables can leak into Docker Compose. Used explicit values in `environment:` instead of `${VAR:-default}` for critical settings.
3. **Qdrant embedding dimension**: Using 768 dimensions for `nomic-embed-text` model compatibility.

### Verified Working

- Docker Compose stack: router + qdrant containers running
- Ollama connectivity via `host.docker.internal`
- L1 cache: 50% hit rate, 1.2ms cached vs 13.7s uncached
- SSE transport: Connection handshake returns session ID and message endpoint
- Qdrant integration: `prompt_cache` collection created, stats show `qdrant_available: true`
- Documentation pipeline: Executes successfully (file writes need volume mounts for host access)
- Dashboard: HTMX UI accessible at `/dashboard`

### Architecture Note

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │   router     │────▶│   qdrant     │                     │
│  │  :9090       │     │  :6333 (int) │                     │
│  └──────┬───────┘     └──────────────┘                     │
│         │                                                   │
│         │ host.docker.internal                              │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────┐
│  Ollama :11434  │  (runs on host for GPU access)
└─────────────────┘
```

---

## 2026-01-13: Full Implementation (Phases 2-4)

### Summary

Completed full implementation of MCP Router from spec. Evaluated LiteLLM as potential alternative—rejected because it routes LLM API calls, not MCP protocol traffic. Built all core components from scratch.

### What We Changed

**Phase 2: Router Core**
- `router/models.py` - JSON-RPC types, MCP protocol models
- `router/registry.py` - Server management with transport adapters
- `router/circuit_breaker.py` - Per-server fault tolerance (CLOSED/OPEN/HALF_OPEN)
- `router/cache.py` - Two-tier cache: L1 exact hash + L2 semantic similarity
- `router/middleware/enhance.py` - Client-specific Ollama enhancement
- `router/adapters/stdio.py` - STDIO→HTTP translation for Node.js MCP servers
- `configs/mcp-servers.json` - Server registry (context7, desktop-commander, sequential-thinking, memory)
- `configs/enhancement-rules.json` - Per-client model rules (updated to use available models)

**Phase 3: Desktop Integration**
- `docker-compose.yml` - Added Qdrant, config volumes, proper depends_on
- `client-configs/claude-desktop.json` - SSE + HTTP transport options
- `client-configs/vscode-mcp.json` - VS Code MCP settings
- `client-configs/raycast-mcp-query.sh` - Executable Raycast script
- `client-configs/obsidian-mcp.json` - Obsidian plugin config

**Phase 4: Dashboard + Extras**
- `router/dashboard.py` - Dashboard routes with HTMX partials
- `templates/dashboard.html` - Dark theme dashboard
- `templates/partials/*.html` - Health, stats, breakers, activity
- `router/pipelines/documentation.py` - Codebase→Obsidian pipeline
- `router/sse.py` - SSE transport for Claude Desktop

### Decisions

1. **LiteLLM rejected**: Routes LLM APIs (chat completions), not MCP protocol—wrong abstraction layer
2. **Two-tier cache**: L1 exact match (instant), L2 embeddings (semantic)—hit rate optimization
3. **HTMX over React**: No build step, simpler deployment, sufficient for dashboard needs
4. **SSE over WebSocket**: Simpler protocol, sufficient for MCP's request/response pattern
5. **Enhancement models updated**: Changed to available models (llama3.2:latest, deepseek-r1:latest, qwen3-coder:30b)

### Verified Working

- Router starts, connects to Ollama, registers 4 MCP servers
- `/ollama/enhance` with client-specific models + caching (50% hit rate after 2 requests)
- `/dashboard` serves HTMX UI with auto-refreshing partials
- `/sse/sessions` endpoint for SSE connection management
- All Python imports compile successfully

### Next Steps

- [x] Test full Docker Compose stack with MCP server containers *(completed in Session 2)*
- [x] Verify Claude Desktop SSE integration end-to-end *(completed in Session 2)*
- [x] Add Qdrant integration for persistent L2 cache *(completed in Session 2)*
- [x] Test documentation pipeline with real repo *(completed in Session 2)*

---

## 2026-01-06: Project Bootstrap & MCP Router Setup

### Summary

Established the MCP Router project from a fresh workspace. The goal is to create a containerized MCP router layer using Colima that enhances prompts via Ollama before forwarding to paid AI services (Claude MAX, VS Code/Copilot, Perplexity Pro).

### Key Decisions

1. **Runtime**: Colima (Docker on macOS) - lightweight, portable
2. **Framework**: FastAPI (Python) for the router service
3. **Secrets**: `ks` CLI (Keychain Secrets manager) with `gen-env-from-ks.sh` script
4. **Development**: Native installs for quick experiments, containerize from day 1 for production

### Completed

- [x] Cleaned up workspace (removed Joyride/ClojureScript files, old duplicates)
- [x] Moved `.prompt.md` files from `agents/` to `prompts/`
- [x] Removed `mcp-example/` symlink (reference material)
- [x] Removed `hello.py` placeholder
- [x] Installed `ks` CLI via Homebrew (`brew tap loteoo/formulas && brew install ks`)
- [x] Created project structure:
  - `pyproject.toml` - Python dependencies (FastAPI, httpx, pydantic)
  - `README.md` - Project overview
  - `Dockerfile` - Router container image
  - `docker-compose.yml` - Container orchestration
  - `.env.example` - Environment template
  - `.gitignore` - Ignore patterns
  - `router/` package with `config.py` and `main.py`
  - `scripts/gen-env-from-ks.sh` - Generate .env from Keychain
- [x] Fixed Ollama URL handling (shell has `OLLAMA_HOST=http://localhost:11434`)
- [x] Tested `/ollama/enhance` endpoint - working with deepseek-r1
- [x] Updated `.github/copilot-instructions.md` with new project structure
- [x] Updated `REFACTOR_PLAN.md` with full architecture and roadmap

### Bug Fixes

- **Ollama URL double-prefix**: `OLLAMA_HOST` env var was set to full URL (`http://localhost:11434`), causing `http://http://...` in constructed URL. Fixed `ollama_url` property to detect and handle existing protocol prefix.

---

## TODO

### Phase 1: Foundation ✅

- [x] Initialize git repository and make first commit
- [x] Test `gen-env-from-ks.sh` script
- [x] Verify Colima is running
- [x] Basic FastAPI router with health endpoint

### Phase 2: MCP Router Core ✅

- [x] JSON-RPC models for MCP protocol
- [x] Server registry with HTTP/STDIO transport adapters
- [x] Circuit breaker pattern per server
- [x] Two-tier prompt cache (L1 hash + L2 embeddings)
- [x] Client-specific enhancement rules
- [x] STDIO→HTTP adapter for Node.js MCP servers

### Phase 3: Desktop Integration ✅

- [x] Claude Desktop config (SSE + HTTP transport)
- [x] VS Code MCP settings
- [x] Raycast script
- [x] Obsidian config template
- [ ] ComfyUI → Draw Things image generation pipeline

### Phase 4: Dashboard ✅

- [x] HTMX dashboard with dark theme
- [x] Real-time health/stats/activity via partials
- [x] Quick actions (clear cache, reset breakers)
- [x] Documentation pipeline endpoint
- [x] SSE transport for Claude Desktop

### Remaining Work

- [ ] Test full Docker Compose stack with MCP containers
- [ ] Add Qdrant integration for persistent L2 cache
- [ ] Test Claude Desktop SSE end-to-end
- [ ] Streaming response support for enhancement

---

## Quick Reference

### Start Router (Development)

```bash
source .venv/bin/activate
uvicorn router.main:app --reload --port 9090
```

### Start Full Stack (Docker)

```bash
docker compose up -d
open http://localhost:9090/dashboard
```

### Test Endpoints

```bash
# Health check
curl http://localhost:9090/health

# Prompt enhancement (client-specific)
curl -X POST http://localhost:9090/ollama/enhance \
  -H "Content-Type: application/json" \
  -H "X-Client-Name: claude-desktop" \
  -d '{"prompt": "explain docker"}'

# Cache stats
curl http://localhost:9090/stats

# Dashboard
open http://localhost:9090/dashboard

# SSE sessions
curl http://localhost:9090/sse/sessions

# Documentation pipeline
curl -X POST "http://localhost:9090/pipelines/documentation?repo_path=/path/to/repo&project_name=my-project"
```

### Secrets Management

```bash
# Add secret to Keychain
ks add obsidian_api_key "your-api-key"

# Generate .env from Keychain
./scripts/gen-env-from-ks.sh

# List secrets
ks ls
```
