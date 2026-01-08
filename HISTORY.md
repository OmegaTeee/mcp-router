# Session History

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

### Phase 1: Foundation (In Progress)

- [ ] Initialize git repository and make first commit
- [ ] Test `gen-env-from-ks.sh` script
- [ ] Add secrets to Keychain: `ks add obsidian_api_key`, `ks add figma_api_key`
- [ ] Verify Colima is running: `colima status`
- [ ] Test Docker build: `docker compose build`

### Phase 2: MCP Router Core

- [ ] Add MCP server proxy endpoints (currently placeholders)
- [ ] Implement proper MCP JSON-RPC protocol handling
- [ ] Add caching layer for repeated prompts
- [ ] Add health checks for upstream MCP servers
- [ ] Configure enhancement rules per endpoint

### Phase 3: Desktop Integration

- [ ] Create Claude Desktop config pointing to router
- [ ] Create VS Code MCP settings
- [ ] Create Raycast MCP integration config
- [ ] Create Obsidian plugin configuration
- [ ] ComfyUI → Draw Things image generation pipeline

### Phase 4: Web Interface

- [ ] Dashboard for server status monitoring
- [ ] Configuration editor UI
- [ ] Prompt enhancement rules UI

### Questions to Resolve

- [ ] GPU passthrough for Ollama in Colima - needed?
- [ ] MCP server containers vs native processes during dev?
- [ ] Streaming response support for prompt enhancement?

---

## Quick Reference

### Start Router (Development)

```bash
source .venv/bin/activate
uvicorn router.main:app --reload --port 9090
```

### Test Endpoints

```bash
# Health check
curl http://localhost:9090/health

# Prompt enhancement
curl -X POST http://localhost:9090/ollama/enhance \
  -H "Content-Type: application/json" \
  -d '{"prompt": "explain docker"}'
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
