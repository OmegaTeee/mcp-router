# MCP Router Architecture

## Vision

A lightweight, containerized **MCP router layer** running locally via Colima that:
1. Routes requests to daily-driver MCP servers
2. Uses Ollama to enhance prompts before forwarding to paid AI services
3. Provides unified tool access across desktop applications

## System Overview

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

## Target Integrations

### AI Services (Enhanced via Ollama)
- Claude MAX (Desktop & Code)
- VS Code + GitHub Copilot Pro
- Perplexity Pro (Desktop & Comet Browser)

### Desktop Applications
- Raycast
- Obsidian
- ComfyUI → Draw Things (image generation workflows)

## Key Components

### Router Service (FastAPI)
- HTTP server on port 9090
- MCP JSON-RPC protocol handling
- Configuration-driven server registration
- Health checks for upstream servers

### Prompt Enhancement
- Ollama middleware for prompt preprocessing
- Configurable rules per endpoint
- Fallback to direct routing if unavailable
- Caching for repeated prompts

### MCP Servers
- Desktop Commander (file ops, terminal)
- Context7 (library docs)
- Sequential Thinking (reasoning)
- Fetch (web content)

## Directory Structure

```
mcp-router/
├── router/               # Main FastAPI application
│   ├── main.py          # Entry point
│   ├── config.py        # Configuration loading
│   └── middleware/      # Request processing
├── docs/                # Technical documentation
├── scripts/             # Utility scripts
└── configs/             # App-specific MCP configs
```

## Related Decisions

- [ADR-001: Use FastAPI](decisions/001-use-fastapi.md)
