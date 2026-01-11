# MCP Router: Technical Specification

> **Status**: v1.0
> **Scope**: Phases 2-4 (Router Core → Desktop Integration → Dashboard)
> **Audience**: Developers, Designers, AI Assistants (Claude, Copilot, Ollama)

---

## 1. Vision & Goals

### Purpose

A containerized MCP router that unifies AI tool access across desktop applications. One endpoint, multiple MCP servers, enhanced prompts.

### Problem

- **Fragmented Configuration**: Each app (Claude Desktop, VS Code, Raycast) requires separate MCP server configs
- **Manual Prompt Engineering**: Users craft prompts without systematic enhancement
- **No Shared Context**: Knowledge gained in one session doesn't transfer to others
- **Setup Friction**: New MCP servers require per-app configuration changes

### Outcomes

| Outcome | How |
|---------|-----|
| **Reduced Setup Time** | Single router config replaces per-app MCP configuration |
| **Seamless Data Sharing** | Memory server enables cross-session context persistence |
| **Improved Prompt Quality** | Ollama enhancement refines prompts before hitting paid APIs |
| **Accelerated Learning** | Documentation + Learning Loop workflows capture knowledge automatically |

### Design Principles

1. **Elegant Simplicity**: Minimal config surface, sensible defaults, explicit overrides only when needed
2. **Professional Stack**: FastAPI, Docker Compose, industry-standard patterns—no experimental dependencies
3. **AI-Native Design**: Structured for AI readers (Claude, Copilot, Ollama) to parse, understand, and extend

### Non-Goals

- Not a general-purpose API gateway
- Not replacing Claude or Copilot—enhancing their capabilities
- Not managing LLM inference (Ollama handles that separately)
- Not a user management system—no registration, login, profiles, or RBAC
- Not exposed to the internet—runs on `localhost` for desktop apps

> **If external access is needed**: Use a simple API key header (`X-API-Key`), not a full auth system. Desktop clients are already authenticated by the OS.

### Target Clients

```
Claude MAX (Desktop & Code)
VS Code + GitHub Copilot Pro
Perplexity Pro (Desktop & Comet)
Raycast
Obsidian
ComfyUI → Draw Things
```

---

## 2. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Desktop Apps                             │
│  Claude Desktop  │  VS Code  │  Raycast  │  Obsidian  │  ComfyUI│
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP :9090
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Router (Container)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ FastAPI      │  │ Enhancement  │  │ MCP Server Aggregator │  │
│  │ Endpoints    │──│ Middleware   │──│ (Proxy + Circuit      │  │
│  │              │  │ (Ollama)     │  │  Breaker)             │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                      │
         │ HTTP               │ HTTP                 │ HTTP/STDIO
         ▼                    ▼                      ▼
┌────────────────┐  ┌────────────────┐  ┌─────────────────────────┐
│ Ollama         │  │ Memory Server  │  │ MCP Servers (Containers)│
│ (Native macOS) │  │ (Container)    │  │ - Context7              │
│ :11434         │  │                │  │ - Desktop Commander     │
│                │  │ Knowledge      │  │ - Sequential Thinking   │
│ Models:        │  │ Graph JSON     │  │ - Fetch                 │
│ - deepseek-r1  │◄─┤ + Embeddings   │  │                         │
│ - llama3       │  │                │  │                         │
│ - nomic-embed  │  │                │  │                         │
└────────────────┘  └────────────────┘  └─────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Colima (Docker)       │
                    │   Shared Volumes        │
                    │   - configs/            │
                    │   - secrets/            │
                    └─────────────────────────┘
```

### Components

| Component | Role | Runtime |
|-----------|------|---------|
| **Router** | HTTP proxy, enhancement orchestration, circuit breaker | Container |
| **Ollama** | Local LLM inference (prompt enhancement + embeddings) | Native macOS (GPU access) |
| **Qdrant** | Vector storage for embeddings (prompt cache, semantic search) | Container |
| **Memory Server** | Persistent knowledge graph with semantic search | Container |
| **Context7** | Library documentation lookup | Container |
| **Desktop Commander** | File operations, terminal commands | Container |
| **Sequential Thinking** | Structured reasoning chains | Container |

### Ollama Models

| Model | Purpose | Context | Use Case |
|-------|---------|---------|----------|
| `deepseek-r1:14b` | Complex reasoning, structured responses | 64K | Claude Desktop |
| `qwen2.5-coder:7b` | Code generation, programming tasks | 128K | VS Code, Copilot |
| `llama3.2:3b` | Fast enhancement, quick commands | 128K | Raycast, Obsidian |
| `nomic-embed-text` | Text embeddings, semantic search | 8K | Prompt cache, Memory |
| `phi3:mini` | Fallback, resource-constrained | 128K | Backup when others fail |

**Model Selection Trade-offs:**
- **Larger (14b+)**: Better quality, slower, requires more VRAM
- **Smaller (3b)**: Faster response, runs on any Mac, less accurate
- **Code-tuned**: Significantly outperform general models for programming

**Embedding Integration Points:**
- **Memory Server**: Store embeddings alongside entities for semantic retrieval
- **Prompt Cache**: Hash + embed prompts; skip enhancement if similar prompt cached
- **Learning Loop**: Cluster similar knowledge to avoid duplicates

### Data Flow

```
1. Client Request
   └─→ POST /mcp/context7/tools/call

2. Router Receives
   └─→ Parse JSON-RPC, identify target server

3. Enhancement (Optional)
   └─→ If enhancement rule matches:
       └─→ Send to Ollama → Get enhanced prompt → Continue

4. Circuit Breaker Check
   └─→ If upstream healthy: forward request
   └─→ If upstream down: return cached/fallback response

5. Upstream MCP Server
   └─→ Execute tool, return JSON-RPC response

6. Response Processing
   └─→ Optional: Extract knowledge → Memory Server
   └─→ Return to client
```

### Transport Abstraction

The router normalizes transport differences so clients see a unified HTTP interface:

| MCP Server | Native Transport | Router Adapter |
|------------|------------------|----------------|
| Context7 | STDIO | Subprocess wrapper → HTTP |
| Desktop Commander | STDIO | Subprocess wrapper → HTTP |
| Sequential Thinking | STDIO | Subprocess wrapper → HTTP |
| Memory Server | HTTP | Direct proxy |
| Custom servers | Either | Auto-detected |

### Port Mapping

| Service | Port | Exposure |
|---------|------|----------|
| Router | 9090 | Host (all clients connect here) |
| Ollama | 11434 | Host (native macOS) |
| Qdrant | 6333 | Host (REST API + dashboard) |
| Context7 | 3001 | Internal only |
| Desktop Commander | 3002 | Internal only |
| Sequential Thinking | 3003 | Internal only |
| Memory Server | 3004 | Internal only |

### Extension Points

**Adding a new MCP server:**
1. Add container definition to `docker-compose.yml`
2. Register in `configs/mcp-servers.json`
3. Router auto-discovers on next restart

See [Adding a Custom MCP Server](#adding-a-custom-mcp-server) for detailed walkthrough with port selection and transport types.

**Adding a new client:**
1. Point client to `http://localhost:9090`
2. Add client-specific enhancement rules to `configs/enhancement-rules.json`
3. No router changes needed

---

## 3. Phase 2: MCP Router Core

> **Approach**: Ship a simple working model first. Add complexity only when real-world constraints demand it.

### 3.1 Router Service

**MVP: Single entry point that proxies to MCP servers**

```python
# router/main.py - Core structure
app = FastAPI(title="MCP Router", lifespan=lifespan)

# Endpoints
GET  /health              # Aggregate health
GET  /health/{server}     # Per-server health
POST /mcp/{server}/{path} # Proxy to upstream MCP server
POST /ollama/enhance      # Direct enhancement (optional)
```

**Server Registry** (`configs/mcp-servers.json`):

```json
{
  "servers": {
    "context7": {
      "url": "http://context7:3001",
      "transport": "http",
      "health_endpoint": "/health"
    },
    "desktop-commander": {
      "url": "http://desktop-commander:3002",
      "transport": "http",
      "health_endpoint": "/health"
    },
    "sequential-thinking": {
      "url": "http://sequential-thinking:3003",
      "transport": "http",
      "health_endpoint": "/health"
    },
    "memory": {
      "url": "http://memory:3004",
      "transport": "http",
      "health_endpoint": "/health"
    }
  }
}
```

**JSON-RPC Models**:

```python
# router/models.py
from pydantic import BaseModel

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict = {}
    id: int | str | None = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: dict | None = None
    error: dict | None = None
    id: int | str | None = None
```

---

### 3.2 Enhancement Middleware

**MVP: Client-based rules only**

Start with simple client identification. Add endpoint/prompt-type rules when needed.

**Enhancement Rules** (`configs/enhancement-rules.json`):

```json
{
  "default": {
    "enabled": true,
    "model": "llama3.2:3b",
    "system_prompt": "Improve clarity and structure. Preserve intent. Return only the enhanced prompt."
  },
  "clients": {
    "claude-desktop": {
      "model": "deepseek-r1:14b",
      "system_prompt": "Provide structured responses with clear reasoning. Use Markdown."
    },
    "vscode": {
      "model": "qwen2.5-coder:7b",
      "system_prompt": "Code-first responses. Include file paths. Minimal prose."
    },
    "raycast": {
      "model": "llama3.2:3b",
      "system_prompt": "Action-oriented. Suggest CLI commands. Under 200 words."
    },
    "obsidian": {
      "model": "llama3.2:3b",
      "system_prompt": "Format in Markdown. Use [[wikilinks]] and #tags."
    }
  },
  "fallback_chain": ["phi3:mini", null]
}
```

**Middleware Logic**:

```python
# router/middleware/enhance.py
async def enhance_prompt(prompt: str, client: str, settings: Settings) -> str:
    rules = load_rules()
    client_rules = rules["clients"].get(client, rules["default"])

    if not client_rules.get("enabled", True):
        return prompt  # Pass-through

    response = await ollama_generate(
        model=client_rules["model"],
        prompt=prompt,
        system=client_rules["system_prompt"]
    )
    return response.get("response", prompt)
```

**Client Detection**: Via `X-Client-Name` header or User-Agent parsing.

**Context Window Management**:

Models have different context limits. Route prompts to appropriate models:

```python
# router/middleware/enhance.py
MODEL_LIMITS = {
    "llama3": 8_000,
    "deepseek-r1": 64_000,
}

async def enhance_with_fallback(prompt: str, preferred_model: str) -> str:
    """Try preferred model, fall back if prompt too large."""
    token_count = count_tokens(prompt)  # tiktoken or similar

    if token_count <= MODEL_LIMITS.get(preferred_model, 8_000):
        return await ollama_generate(model=preferred_model, prompt=prompt)

    # Fallback to larger context model
    if token_count <= MODEL_LIMITS["deepseek-r1"]:
        return await ollama_generate(model="deepseek-r1", prompt=prompt)

    # Too large for any model - return original
    logger.warning(f"Prompt too large ({token_count} tokens), skipping enhancement")
    return prompt
```

**Prompt Cache** (two-tier):

> **How it works (plain English)**: The cache avoids re-processing similar prompts. **L1** uses exact text matching—if you send the identical prompt twice, it returns the cached result instantly. **L2** uses "embeddings"—a way to convert text into numbers that capture meaning. When two prompts are semantically similar (e.g., "explain Docker" and "what is Docker?"), their embeddings will be close together. We measure closeness with a "dot product" (a math operation)—if the result exceeds 0.85, we consider it a match and return the cached response. **LRU** (Least Recently Used) means we discard the oldest unused entries when the cache fills up.

```python
# router/cache.py
from collections import OrderedDict
import numpy as np

class PromptCache:
    def __init__(self, max_size: int = 1000, similarity_threshold: float = 0.85):
        self.max_size = max_size
        self.threshold = similarity_threshold
        self.exact_cache: OrderedDict[str, str] = OrderedDict()  # L1: hash
        self.embed_cache: list[tuple[np.ndarray, str, str]] = []  # L2: (embedding, prompt, response)

    def get(self, prompt: str, embedding: np.ndarray | None = None) -> str | None:
        # L1: Exact match (instant)
        if prompt in self.exact_cache:
            self.exact_cache.move_to_end(prompt)
            return self.exact_cache[prompt]

        # L2: Semantic similarity
        if embedding is not None:
            for cached_embed, _, cached_response in self.embed_cache:
                similarity = np.dot(embedding, cached_embed)
                if similarity >= self.threshold:
                    return cached_response

        return None

    def put(self, prompt: str, response: str, embedding: np.ndarray | None = None):
        # LRU eviction
        if len(self.exact_cache) >= self.max_size:
            self.exact_cache.popitem(last=False)

        self.exact_cache[prompt] = response

        if embedding is not None:
            self.embed_cache.append((embedding, prompt, response))
            if len(self.embed_cache) > self.max_size:
                self.embed_cache.pop(0)
```

**Future Enhancements** (add when needed):
- Per-endpoint rules (`/mcp/context7/*` uses different model)
- Prompt-type detection (code vs docs vs Q&A)
- Redis upgrade path for distributed caching

---

### 3.2.1 Vector Storage with Qdrant

> **When to add**: Upgrade from in-memory cache when you need persistence across restarts or have >10K cached prompts.

Qdrant replaces the in-memory `embed_cache` with persistent, indexed vector storage.

**Why Qdrant over in-memory:**
- **Persistence**: Cache survives router restarts
- **Scale**: Handles millions of vectors efficiently
- **Speed**: HNSW index for sub-millisecond similarity search
- **Dashboard**: Built-in UI at `http://localhost:6333/dashboard`

**Docker Setup** (add to docker-compose.yml):

```yaml
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

**Colima Prerequisite** (macOS):

```bash
# Ensure Colima is running with Docker runtime
colima status
colima start --runtime docker

# Point Docker CLI to Colima
docker context use colima
# OR
export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
```

**Python Integration**:

```python
# router/cache_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

class QdrantPromptCache:
    """Persistent vector cache using Qdrant."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection: str = "prompt_cache",
        similarity_threshold: float = 0.85,
        vector_size: int = 768  # nomic-embed-text dimension
    ):
        self.client = QdrantClient(url=url)
        self.collection = collection
        self.threshold = similarity_threshold

        # Create collection if not exists
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    def get(self, embedding: list[float]) -> str | None:
        """Search for similar prompt, return cached response if found."""
        results = self.client.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=1,
            score_threshold=self.threshold
        )

        if results:
            return results[0].payload.get("response")
        return None

    def put(self, prompt: str, response: str, embedding: list[float]):
        """Store prompt-response pair with embedding."""
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "prompt": prompt,
                        "response": response
                    }
                )
            ]
        )

    def clear(self):
        """Clear all cached entries."""
        self.client.delete_collection(self.collection)
```

**Integration with Enhancement Middleware**:

```python
# router/middleware/enhance.py
from router.cache_qdrant import QdrantPromptCache

# Initialize (in FastAPI lifespan)
cache = QdrantPromptCache(url=settings.qdrant_url)

async def enhance_prompt(prompt: str, client: str) -> str:
    # Generate embedding via Ollama
    embedding = await ollama_embed(prompt, model="nomic-embed-text")

    # Check Qdrant cache
    cached = cache.get(embedding)
    if cached:
        return cached

    # Enhance via Ollama
    enhanced = await ollama_generate(...)

    # Store in Qdrant
    cache.put(prompt, enhanced, embedding)

    return enhanced
```

**Settings Addition** (`router/config.py`):

```python
class Settings(BaseSettings):
    # ... existing settings ...
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "prompt_cache"
```

**Health Check** (add Qdrant to `/health`):

```python
async def check_qdrant_health() -> dict:
    try:
        client = QdrantClient(url=settings.qdrant_url)
        info = client.get_collection(settings.qdrant_collection)
        return {
            "name": "qdrant",
            "status": "healthy",
            "vectors_count": info.vectors_count
        }
    except Exception as e:
        return {"name": "qdrant", "status": "down", "error": str(e)}
```

---

### 3.3 Circuit Breaker & Graceful Fallback

**Per-server circuit breakers** — one failing MCP server shouldn't block others.

```python
# router/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta

class State(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 30
    ):
        self.name = name
        self.state = State.CLOSED
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.last_failure: datetime | None = None

    def record_success(self):
        self.failures = 0
        self.state = State.CLOSED

    def record_failure(self):
        self.failures += 1
        self.last_failure = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = State.OPEN

    def can_execute(self) -> bool:
        if self.state == State.CLOSED:
            return True
        if self.state == State.OPEN:
            if datetime.now() - self.last_failure > self.recovery_timeout:
                self.state = State.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: allow one request

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None
        }

# Registry of per-server breakers
class CircuitBreakerRegistry:
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def get(self, server: str) -> CircuitBreaker:
        if server not in self.breakers:
            self.breakers[server] = CircuitBreaker(name=server)
        return self.breakers[server]

    def all_status(self) -> list[dict]:
        return [b.status() for b in self.breakers.values()]
```

**Fallback Strategy**:

| Scenario | Fallback | User Impact |
|----------|----------|-------------|
| Ollama down | Return the user's original request without enhancement | Request still works, just unenhanced |
| MCP server down | Return error with retry hint; other servers unaffected | Clear error message suggests retry |
| Timeout | Return partial response if available | Degraded but functional |
| Model context exceeded | Fallback to larger model or skip enhancement | Automatic recovery, user unaware |

> **Note**: "Original request" = the exact prompt the user sent before any Ollama enhancement was applied.

**Health Endpoint** exposes all breaker states:

```python
@app.get("/health")
async def health_check(registry: CircuitBreakerRegistry) -> dict:
    return {
        "status": "healthy",
        "circuit_breakers": registry.all_status()
    }
```

---

### 3.4 MCP Server Containers

**MVP: Four core servers**

```yaml
# docker-compose.yml
services:
  router:
    build: .
    ports:
      - "9090:9090"
    environment:
      - OLLAMA_HOST=host.docker.internal
      - OLLAMA_PORT=11434
    volumes:
      - ./configs:/app/configs:ro
    depends_on:
      - context7
      - desktop-commander
      - sequential-thinking

  context7:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@upstash/context7-mcp/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
    expose:
      - "3001"

  desktop-commander:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@wonderwhy-er/desktop-commander/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
      - ${HOME}:/host-home:rw
    expose:
      - "3002"

  sequential-thinking:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
    expose:
      - "3003"
```

### Adding a Custom MCP Server

#### Transport Types

MCP servers communicate via one of two transports:

| Transport | Description | Use When |
|-----------|-------------|----------|
| **STDIO** | Newline-delimited JSON over stdin/stdout | Most Node.js MCP servers (default) |
| **HTTP** | REST/JSON-RPC over HTTP | Servers with built-in HTTP support |

Most community MCP servers use **STDIO**. The router wraps these via `StdioAdapter` (see Section 3.4).

#### Port Selection

Internal ports start at **3001** and increment:

| Port Range | Reserved For |
|------------|--------------|
| 3001-3010 | Core MCP servers (Context7, Desktop Commander, etc.) |
| 3011-3050 | Custom/user MCP servers |
| 9090 | Router (exposed to host) |
| 11434 | Ollama (native macOS) |

**Rule**: Pick the next unused port in the 3011-3050 range for custom servers.

#### Step-by-Step Walkthrough

1. **Add to `docker-compose.yml`** (file location: project root):

```yaml
  my-server:
    image: node:20-slim
    working_dir: /app
    command: ["node", "path/to/server.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
    expose:
      - "3011"  # Next available port
```

2. **Register in `configs/mcp-servers.json`** (file location: `configs/`):

For **STDIO** servers (most common):
```json
"my-server": {
  "transport": "stdio",
  "command": ["node", "path/to/server.js"]
}
```

For **HTTP** servers:
```json
"my-server": {
  "transport": "http",
  "url": "http://my-server:3011",
  "health_endpoint": "/health"
}
```

3. **Restart**: `docker compose up -d`

4. **Verify**: `curl http://localhost:9090/health | jq '.circuit_breakers'`

**STDIO → HTTP Transport Adapter**:

For MCP servers that only support STDIO (most Node.js servers), the router wraps them:

```python
# router/adapters/stdio.py
import asyncio
import json
from asyncio.subprocess import Process

class StdioAdapter:
    """Wraps STDIO MCP servers as HTTP-callable services."""

    def __init__(
        self,
        command: list[str],
        timeout: float = 30.0,
        max_restarts: int = 3
    ):
        self.command = command
        self.timeout = timeout
        self.max_restarts = max_restarts
        self.process: Process | None = None
        self.restart_count = 0

    async def start(self):
        """Start the subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def call(self, request: dict) -> dict:
        """Send JSON-RPC request, receive response."""
        if not self.process or self.process.returncode is not None:
            await self._restart()

        # Write newline-delimited JSON per MCP spec
        line = json.dumps(request) + "\n"
        self.process.stdin.write(line.encode())
        await self.process.stdin.drain()

        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=self.timeout
            )
            return json.loads(response_line.decode())
        except asyncio.TimeoutError:
            await self._restart()
            raise TimeoutError(f"STDIO server timed out after {self.timeout}s")

    async def _restart(self):
        """Restart crashed process with limits."""
        if self.restart_count >= self.max_restarts:
            raise RuntimeError(f"Max restarts ({self.max_restarts}) exceeded")

        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()

        self.restart_count += 1
        await self.start()

    async def stop(self):
        """Graceful shutdown."""
        if self.process:
            self.process.terminate()
            await self.process.wait()

    def is_healthy(self) -> bool:
        return self.process is not None and self.process.returncode is None
```

**Server Registry with Transport Type**:

```json
{
  "servers": {
    "context7": {
      "transport": "stdio",
      "command": ["node", "node_modules/@upstash/context7-mcp/dist/index.js"]
    },
    "memory": {
      "transport": "http",
      "url": "http://memory:3004"
    }
  }
}
```

**Note**: Memory Server is Phase 3 — skip in MVP. Add persistent knowledge graph once you observe duplication patterns in usage.

**Future Enhancements**:
- Auto-discovery of MCP servers on network
- Hot-reload of server registry without restart

---

## 4. Phase 3: Desktop Integration

### 4.1 Client Configurations

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-router": {
      "command": "curl",
      "args": ["-X", "POST", "http://localhost:9090/mcp"],
      "env": {}
    }
  }
}
```

Or point directly to router's SSE endpoint:

```json
{
  "mcpServers": {
    "mcp-router": {
      "url": "http://localhost:9090/sse",
      "transport": "sse"
    }
  }
}
```

**VS Code** (`.vscode/mcp.json` or workspace settings):

```json
{
  "mcp.servers": {
    "mcp-router": {
      "type": "http",
      "url": "http://localhost:9090",
      "headers": {
        "X-Client-Name": "vscode"
      }
    }
  }
}
```

**Raycast Script** (`~/.config/raycast/scripts/mcp-query.sh`):

```bash
#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title MCP Query
# @raycast.mode fullOutput
# @raycast.argument1 { "type": "text", "placeholder": "Query" }

curl -s -X POST http://localhost:9090/mcp/sequential-thinking/tools/call \
  -H "Content-Type: application/json" \
  -H "X-Client-Name: raycast" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"think\",\"arguments\":{\"query\":\"$1\"}},\"id\":1}"
```

**Obsidian** (via Obsidian MCP plugin or custom script):

```json
{
  "mcp_endpoint": "http://localhost:9090",
  "client_name": "obsidian",
  "default_vault_path": "~/Obsidian",
  "auto_link": true
}
```

---

### 4.2 Documentation Pipeline

**Purpose**: Automatically generate documentation from codebases and write to Obsidian.

**Trigger Points**:
- Raycast command: `raycast://extensions/mcp-router/document-repo`
- VS Code command palette: `MCP: Document Current Workspace`
- CLI: `curl -X POST http://localhost:9090/pipelines/documentation`

**Flow**:

```
1. Trigger (repo_path, project_name)
   │
2. Repomix Pack
   └─→ Compress codebase to token-efficient format
   │
3. Ollama Enhancement (deepseek-r1:14b)
   └─→ System: "Document this codebase for beginners..."
   │
4. Sequential Thinking
   └─→ Structure into logical sections
   │
5. Write to Obsidian
   └─→ ~/Obsidian/Projects/{project_name}.md
```

**Implementation** (`router/pipelines/documentation.py`):

```python
from router.models import JSONRPCRequest

async def documentation_pipeline(
    repo_path: str,
    project_name: str,
    vault_path: str = "~/Obsidian/Projects"
) -> dict:
    """Generate documentation from codebase → Obsidian."""

    # Step 1: Pack repository (if Repomix available)
    # For MVP, accept pre-packed content or raw path

    # Step 2: Enhance with documentation focus
    doc_prompt = f"""
    Generate technical documentation for: {repo_path}

    Include:
    - Architecture overview (max 500 words)
    - Setup instructions with exact commands
    - Key components and their responsibilities
    - Common workflows
    """

    enhanced = await enhance_prompt(
        prompt=doc_prompt,
        client="documentation-pipeline",
        model="deepseek-r1:14b",
        system="""You are a technical documentation specialist.
        Format in Markdown with clear headers.
        Include code blocks for commands.
        Use [[wikilinks]] for cross-references."""
    )

    # Step 3: Structure with Sequential Thinking
    structure_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "sequentialthinking",
            "arguments": {
                "thought": enhanced,
                "thought_number": 1,
                "total_thoughts": 3
            }
        }
    )
    structured = await route_to_server("sequential-thinking", structure_request)

    # Step 4: Write to Obsidian vault
    output_path = f"{vault_path}/{project_name}.md"

    doc_content = f"""---
tags: [project, documentation, auto-generated]
created: {datetime.now().isoformat()}
source: {repo_path}
---

# {project_name}

{structured['result']}

---
*Generated by MCP Router Documentation Pipeline*
"""

    # Use Desktop Commander to write file
    write_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "write_file",
            "arguments": {
                "path": output_path,
                "content": doc_content
            }
        }
    )
    await route_to_server("desktop-commander", write_request)

    return {
        "status": "complete",
        "output_path": output_path,
        "obsidian_url": f"obsidian://open?vault=Obsidian&file=Projects/{project_name}"
    }
```

**Router Endpoint**:

```python
@app.post("/pipelines/documentation")
async def run_documentation_pipeline(
    repo_path: str,
    project_name: str,
    vault_path: str = "~/Obsidian/Projects"
) -> dict:
    return await documentation_pipeline(repo_path, project_name, vault_path)
```

**Vault Path Conventions**:

| Content Type | Path |
|--------------|------|
| Project docs | `~/Obsidian/Projects/{name}.md` |
| API reference | `~/Obsidian/Projects/{name}/API.md` |
| Meeting notes | `~/Obsidian/Meetings/{date}-{topic}.md` |
| Learning notes | `~/Obsidian/Learning/{topic}.md` |


---

## 5. Phase 4: Dashboard

> **Approach**: Simple static HTML + HTMX. No build step, no React/Vue complexity. Served directly from the router.

### Overview

Single-page dashboard at `/dashboard` showing system health, activity, and quick actions.

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Router Dashboard                              [Refresh]│
├─────────────────────────────────────────────────────────────┤
│  Services                          │  Enhancement Stats     │
│  ┌─────────────────────────────┐   │  ┌───────────────────┐ │
│  │ ● Router        healthy     │   │  │ Cache Hits: 847   │ │
│  │ ● Ollama        healthy     │   │  │ Cache Miss: 123   │ │
│  │ ● Context7      healthy     │   │  │ Hit Rate: 87.3%   │ │
│  │ ○ Desktop Cmd   degraded    │   │  │                   │ │
│  │ ● Seq Thinking  healthy     │   │  │ Model Usage:      │ │
│  └─────────────────────────────┘   │  │ llama3.2: 654     │ │
│                                    │  │ deepseek: 201     │ │
│  Circuit Breakers                  │  │ qwen2.5: 115      │ │
│  ┌─────────────────────────────┐   │  └───────────────────┘ │
│  │ context7: CLOSED (0 fails)  │   │                        │
│  │ desktop-cmd: HALF_OPEN (2)  │   │  Quick Actions         │
│  │ seq-thinking: CLOSED (0)    │   │  [Clear Cache]         │
│  └─────────────────────────────┘   │  [Restart Desktop Cmd] │
├─────────────────────────────────────────────────────────────┤
│  Recent Activity (last 50)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 12:34:01 POST /mcp/context7/tools/call    200   45ms   ││
│  │ 12:33:58 POST /ollama/enhance             200   1.2s   ││
│  │ 12:33:45 GET  /health                     200   12ms   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Implementation

**Router Endpoint** (`router/dashboard.py`):

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

@dashboard_router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "MCP Router Dashboard"
    })

@dashboard_router.get("/health-partial", response_class=HTMLResponse)
async def health_partial(request: Request):
    """HTMX partial for health status."""
    health = await get_all_health()
    return templates.TemplateResponse("partials/health.html", {
        "request": request,
        "services": health
    })

@dashboard_router.get("/stats-partial", response_class=HTMLResponse)
async def stats_partial(request: Request):
    """HTMX partial for enhancement stats."""
    stats = get_cache_stats()
    return templates.TemplateResponse("partials/stats.html", {
        "request": request,
        "stats": stats
    })

@dashboard_router.get("/activity-partial", response_class=HTMLResponse)
async def activity_partial(request: Request):
    """HTMX partial for recent activity."""
    activity = get_recent_requests(limit=50)
    return templates.TemplateResponse("partials/activity.html", {
        "request": request,
        "activity": activity
    })
```

**Main Template** (`templates/dashboard.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        :root {
            --bg: #1a1a2e;
            --card: #16213e;
            --text: #eee;
            --green: #4ecca3;
            --yellow: #ffc107;
            --red: #e74c3c;
        }
        body {
            font-family: system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card {
            background: var(--card);
            border-radius: 8px;
            padding: 16px;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .healthy { background: var(--green); }
        .degraded { background: var(--yellow); }
        .down { background: var(--red); }
        table { width: 100%; border-collapse: collapse; }
        td, th { padding: 8px; text-align: left; border-bottom: 1px solid #333; }
        button {
            background: var(--green);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 4px;
        }
        button:hover { opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MCP Router Dashboard</h1>

        <div class="grid">
            <!-- Services Health -->
            <div class="card"
                 hx-get="/dashboard/health-partial"
                 hx-trigger="load, every 5s"
                 hx-swap="innerHTML">
                Loading health...
            </div>

            <!-- Enhancement Stats -->
            <div class="card"
                 hx-get="/dashboard/stats-partial"
                 hx-trigger="load, every 10s"
                 hx-swap="innerHTML">
                Loading stats...
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="card" style="margin-top: 20px;">
            <h3>Quick Actions</h3>
            <button hx-post="/dashboard/actions/clear-cache"
                    hx-swap="none"
                    hx-confirm="Clear prompt cache?">
                Clear Cache
            </button>
            <button hx-post="/dashboard/actions/restart/desktop-commander"
                    hx-swap="none"
                    hx-confirm="Restart Desktop Commander?">
                Restart Desktop Cmd
            </button>
        </div>

        <!-- Recent Activity -->
        <div class="card" style="margin-top: 20px;"
             hx-get="/dashboard/activity-partial"
             hx-trigger="load, every 3s"
             hx-swap="innerHTML">
            Loading activity...
        </div>
    </div>
</body>
</html>
```

**Health Partial** (`templates/partials/health.html`):

```html
<h3>Services</h3>
<ul style="list-style: none; padding: 0;">
{% for service in services %}
    <li>
        <span class="status-dot {{ service.status }}"></span>
        {{ service.name }} - {{ service.status }}
        {% if service.latency %}({{ service.latency }}ms){% endif %}
    </li>
{% endfor %}
</ul>

<h3>Circuit Breakers</h3>
<ul style="list-style: none; padding: 0;">
{% for breaker in breakers %}
    <li>{{ breaker.name }}: {{ breaker.state }} ({{ breaker.failures }} failures)</li>
{% endfor %}
</ul>
```

**Quick Actions** (`router/dashboard.py`):

```python
@dashboard_router.post("/actions/clear-cache")
async def clear_cache():
    """Clear the prompt cache."""
    cache = get_prompt_cache()
    cache.exact_cache.clear()
    cache.embed_cache.clear()
    return {"status": "cache_cleared"}

@dashboard_router.post("/actions/restart/{server}")
async def restart_server(server: str):
    """Restart a specific MCP server."""
    adapter = get_adapter(server)
    if hasattr(adapter, '_restart'):
        await adapter._restart()
        return {"status": f"{server}_restarted"}
    return {"status": "not_restartable", "server": server}
```

**Request Logging Middleware**:

```python
from collections import deque
from datetime import datetime

request_log: deque = deque(maxlen=50)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.now()
    response = await call_next(request)
    elapsed = (datetime.now() - start).total_seconds() * 1000

    request_log.append({
        "timestamp": start.isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": round(elapsed, 1)
    })

    return response

def get_recent_requests(limit: int = 50) -> list:
    return list(request_log)[-limit:]
```

### Dependencies

Minimal - no build step required:

```txt
# requirements.txt (additions)
jinja2>=3.1.0
```

HTMX loaded from CDN (or bundle locally for offline use).

### Accessing the Dashboard

```
http://localhost:9090/dashboard
```

**Future Enhancements**:
- WebSocket for real-time updates (replace polling)
- Request filtering/search
- Model response time graphs
- Dark/light mode toggle

---

## 6. Secrets Management

> **Principle**: Never hardcode secrets. Load from environment. Different strategies for dev vs production.

### Secrets Inventory

| Secret | Purpose | Required By |
|--------|---------|-------------|
| `OLLAMA_URL` | Ollama API endpoint | Router |
| `GITHUB_TOKEN` | GitHub API access (Context7) | Context7 |
| `ANTHROPIC_API_KEY` | Claude API fallback | Router (optional) |
| `OPENAI_API_KEY` | OpenAI fallback | Router (optional) |
| `UPSTASH_REDIS_URL` | Redis for distributed cache | Router (future) |

### Development: `.env` File

**Never commit `.env` to git.** Add to `.gitignore`.

```bash
# .env (local development only)
OLLAMA_URL=http://localhost:11434
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
# Optional fallback APIs
ANTHROPIC_API_KEY=sk-ant-xxxx
OPENAI_API_KEY=sk-xxxx
```

**Loading in FastAPI** (`router/config.py`):

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Required
    ollama_url: str = "http://localhost:11434"

    # Optional - for MCP servers
    github_token: str | None = None

    # Optional - API fallbacks
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Cache settings
    cache_max_size: int = 1000
    cache_similarity_threshold: float = 0.85

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Usage in Router**:

```python
from router.config import get_settings

settings = get_settings()
ollama_client = OllamaClient(base_url=settings.ollama_url)
```

### Docker Compose: Environment Variables

Pass secrets via environment, not files:

```yaml
# docker-compose.yml
services:
  router:
    build: .
    ports:
      - "9090:9090"
    environment:
      - OLLAMA_URL=${OLLAMA_URL:-http://host.docker.internal:11434}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    env_file:
      - .env  # For local dev only
```

**Or use Docker secrets** (more secure for production):

```yaml
services:
  router:
    secrets:
      - github_token
    environment:
      - GITHUB_TOKEN_FILE=/run/secrets/github_token

secrets:
  github_token:
    file: ./secrets/github_token.txt
```

### Production Options

**Option 1: GitHub Actions Secrets** (for CI/CD):

```yaml
# .github/workflows/deploy.yml
env:
  OLLAMA_URL: ${{ secrets.OLLAMA_URL }}
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Option 2: HashiCorp Vault** (self-hosted production):

```python
import hvac

def load_secrets_from_vault():
    client = hvac.Client(url='http://vault:8200')
    client.token = os.getenv('VAULT_TOKEN')

    secrets = client.secrets.kv.v2.read_secret_version(
        path='mcp-router/prod'
    )
    return secrets['data']['data']
```

**Option 3: AWS Secrets Manager** (cloud production):

```python
import boto3

def load_secrets_from_aws():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='mcp-router/prod')
    return json.loads(response['SecretString'])
```

### Runtime Loading Pattern

```python
# router/config.py
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

def get_environment() -> Environment:
    return Environment(os.getenv("ENVIRONMENT", "development"))

def load_secrets() -> dict:
    env = get_environment()

    if env == Environment.DEVELOPMENT:
        # Load from .env file
        from dotenv import load_dotenv
        load_dotenv()
        return {
            "ollama_url": os.getenv("OLLAMA_URL"),
            "github_token": os.getenv("GITHUB_TOKEN"),
        }

    elif env == Environment.PRODUCTION:
        # Load from Vault/AWS/etc
        return load_secrets_from_vault()  # or AWS, etc.
```

### Security Checklist

- [ ] `.env` in `.gitignore`
- [ ] No secrets in `docker-compose.yml` (use env vars)
- [ ] No secrets in code or configs
- [ ] Rotate tokens quarterly (set calendar reminder)
- [ ] Use least-privilege tokens (read-only where possible)
- [ ] Audit secret access in production logs

---

## 7. AI Context Reference

> **Purpose**: Structured context for AI assistants (Claude, Copilot, Ollama) to understand and work with this project.

### 7.1 System Prompts

**Claude Desktop** (complex reasoning, documentation):

```
You are assisting with the MCP Router project—a containerized FastAPI service that proxies MCP servers and enhances prompts via Ollama.

Tech stack: FastAPI, Docker Compose, Ollama, Python 3.12
Key files: router/main.py, configs/mcp-servers.json, configs/enhancement-rules.json
Architecture: Desktop Apps → Router :9090 → MCP Servers (Context7, Desktop Commander, Sequential Thinking)

When helping:
- Provide structured responses with clear reasoning
- Use Markdown formatting
- Reference specific file paths
- Suggest production-ready patterns (circuit breakers, graceful fallback)
```

**VS Code / Copilot** (code-focused, minimal prose):

```
MCP Router project. FastAPI + Docker Compose.

Key paths:
- router/main.py: FastAPI app, endpoints
- router/middleware/enhance.py: Ollama prompt enhancement
- router/circuit_breaker.py: Per-server circuit breakers
- router/adapters/stdio.py: STDIO→HTTP wrapper
- configs/*.json: Server registry, enhancement rules

Style: Code-first. Include file paths. Minimal prose. Type hints required.
```

**Raycast** (quick actions, CLI-oriented):

```
MCP Router - local AI tool proxy.

Quick commands:
- Health check: curl http://localhost:9090/health
- Enhance prompt: curl -X POST http://localhost:9090/ollama/enhance -d '{"prompt":"..."}'
- Restart: docker compose restart router
- Logs: docker compose logs -f router

Keep responses under 200 words. Suggest CLI commands.
```

**Obsidian** (documentation, wikilinks):

```
MCP Router documentation context.

Format responses in Markdown. Use:
- [[wikilinks]] for cross-references
- #tags for categorization
- Code blocks with language hints
- YAML frontmatter for metadata

Vault structure:
- Projects/{name}.md - Project documentation
- Learning/{topic}.md - Technical notes
```

### 7.2 Tool Schemas

**Auto-generate from MCP servers** — don't maintain manually.

```python
# router/tools/schema_generator.py
async def get_all_tool_schemas() -> dict:
    """Fetch tool schemas from all registered MCP servers."""
    schemas = {}

    for server_name, config in load_server_registry().items():
        try:
            # MCP servers expose their tools via tools/list
            response = await call_server(server_name, {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            })
            schemas[server_name] = response.get("result", {}).get("tools", [])
        except Exception as e:
            schemas[server_name] = {"error": str(e)}

    return schemas

# Endpoint to fetch current schemas
@app.get("/tools/schemas")
async def list_tool_schemas():
    """Returns all tool schemas from registered MCP servers."""
    return await get_all_tool_schemas()
```

**Usage**: Fetch live schemas via `GET /tools/schemas` rather than hardcoding.

### 7.3 Routing Decision Tree

```
REQUEST ARRIVES AT ROUTER
         │
         ▼
┌─────────────────────┐
│ Parse JSON-RPC      │
│ Extract: server,    │
│ method, params      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     NO      ┌─────────────────┐
│ Server registered?  │────────────▶│ Return 404      │
└─────────┬───────────┘             └─────────────────┘
          │ YES
          ▼
┌─────────────────────┐     OPEN    ┌─────────────────┐
│ Circuit breaker     │────────────▶│ Return 503      │
│ state?              │             │ + retry hint    │
└─────────┬───────────┘             └─────────────────┘
          │ CLOSED/HALF_OPEN
          ▼
┌─────────────────────┐     YES     ┌─────────────────┐
│ Enhancement rule    │────────────▶│ Call Ollama     │
│ matches?            │             │ enhance prompt  │
└─────────┬───────────┘             └────────┬────────┘
          │ NO                                │
          │◀──────────────────────────────────┘
          ▼
┌─────────────────────┐
│ Check prompt cache  │
│ L1: exact hash      │
│ L2: embedding sim   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     HIT     ┌─────────────────┐
│ Cache result?       │────────────▶│ Return cached   │
└─────────┬───────────┘             └─────────────────┘
          │ MISS
          ▼
┌─────────────────────┐
│ Forward to MCP      │
│ server (HTTP/STDIO) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ERROR   ┌─────────────────┐
│ Response OK?        │────────────▶│ Record failure  │
└─────────┬───────────┘             │ Update breaker  │
          │ SUCCESS                 └─────────────────┘
          ▼
┌─────────────────────┐
│ Cache response      │
│ Record success      │
│ Return to client    │
└─────────────────────┘
```

### 7.4 Project Context Block

**Copy-paste this into any AI assistant for project context:**

```markdown
# MCP Router Project Context

## What is this?
A containerized MCP (Model Context Protocol) router that:
- Proxies multiple MCP servers through a single endpoint (:9090)
- Enhances prompts via local Ollama before forwarding
- Provides circuit breakers for fault tolerance
- Supports Claude Desktop, VS Code, Raycast, Obsidian clients

## Tech Stack
- **Backend**: FastAPI (Python 3.12)
- **Container**: Docker Compose + Colima
- **LLM**: Ollama (native macOS for GPU)
- **Models**: deepseek-r1:14b, qwen2.5-coder:7b, llama3.2:3b, nomic-embed-text

## Key Files
- `router/main.py` - FastAPI app entry point
- `router/middleware/enhance.py` - Prompt enhancement logic
- `router/circuit_breaker.py` - Per-server circuit breakers
- `router/adapters/stdio.py` - STDIO→HTTP wrapper
- `configs/mcp-servers.json` - Server registry
- `configs/enhancement-rules.json` - Client-specific rules
- `docker-compose.yml` - Container orchestration

## Architecture
Desktop Apps → Router (:9090) → Ollama (:11434) + MCP Servers

## Current Phase
Phase 2: MCP Router Core (router, enhancement, circuit breakers)
```

### 7.5 Common Tasks

**Add a new MCP server:**
```bash
# 1. Add to docker-compose.yml
# 2. Register in configs/mcp-servers.json
# 3. Restart
docker compose up -d
```

**Test enhancement locally:**
```bash
curl -X POST http://localhost:9090/ollama/enhance \
  -H "Content-Type: application/json" \
  -d '{"prompt": "explain docker networking", "client": "claude-desktop"}'
```

**Check system health:**
```bash
curl http://localhost:9090/health | jq
```

**View circuit breaker states:**
```bash
curl http://localhost:9090/health | jq '.circuit_breakers'
```

**Clear prompt cache:**
```bash
curl -X POST http://localhost:9090/dashboard/actions/clear-cache
```

**Tail router logs:**
```bash
docker compose logs -f router
```

**Run documentation pipeline:**
```bash
curl -X POST "http://localhost:9090/pipelines/documentation?repo_path=/path/to/repo&project_name=my-project"
```

---

## Appendix A: Configuration Files

### `configs/mcp-servers.json`

```json
{
  "servers": {
    "context7": {
      "transport": "stdio",
      "command": ["node", "node_modules/@upstash/context7-mcp/dist/index.js"],
      "health_endpoint": null
    },
    "desktop-commander": {
      "transport": "stdio",
      "command": ["node", "node_modules/@wonderwhy-er/desktop-commander/dist/index.js"],
      "health_endpoint": null
    },
    "sequential-thinking": {
      "transport": "stdio",
      "command": ["node", "node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js"],
      "health_endpoint": null
    },
    "memory": {
      "transport": "http",
      "url": "http://memory:3004",
      "health_endpoint": "/health"
    }
  }
}
```

### `configs/enhancement-rules.json`

```json
{
  "default": {
    "enabled": true,
    "model": "llama3.2:3b",
    "system_prompt": "Improve clarity and structure. Preserve intent. Return only the enhanced prompt."
  },
  "clients": {
    "claude-desktop": {
      "model": "deepseek-r1:14b",
      "system_prompt": "Provide structured responses with clear reasoning. Use Markdown."
    },
    "vscode": {
      "model": "qwen2.5-coder:7b",
      "system_prompt": "Code-first responses. Include file paths. Minimal prose."
    },
    "raycast": {
      "model": "llama3.2:3b",
      "system_prompt": "Action-oriented. Suggest CLI commands. Under 200 words."
    },
    "obsidian": {
      "model": "llama3.2:3b",
      "system_prompt": "Format in Markdown. Use [[wikilinks]] and #tags."
    }
  },
  "fallback_chain": ["phi3:mini", null]
}
```

### `docker-compose.yml`

```yaml
version: "3.8"

services:
  router:
    build: .
    ports:
      - "9090:9090"
    environment:
      - OLLAMA_URL=${OLLAMA_URL:-http://host.docker.internal:11434}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - ENVIRONMENT=${ENVIRONMENT:-development}
    env_file:
      - .env
    volumes:
      - ./configs:/app/configs:ro
      - ./templates:/app/templates:ro
    depends_on:
      - context7
      - desktop-commander
      - sequential-thinking
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  context7:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@upstash/context7-mcp/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
    expose:
      - "3001"

  desktop-commander:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@wonderwhy-er/desktop-commander/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
      - ${HOME}:/host-home:rw
    expose:
      - "3002"

  sequential-thinking:
    image: node:20-slim
    working_dir: /app
    command: ["node", "node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js"]
    volumes:
      - ./node_modules:/app/node_modules:ro
    expose:
      - "3003"

  # Optional: Vector storage for persistent prompt cache
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

### `.env.example`

```bash
# Required
OLLAMA_URL=http://localhost:11434

# Optional - for MCP servers
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Optional - API fallbacks
ANTHROPIC_API_KEY=sk-ant-xxxx
OPENAI_API_KEY=sk-xxxx

# Environment
ENVIRONMENT=development
```

### `requirements.txt`

```txt
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
python-dotenv>=1.0.0
jinja2>=3.1.0
numpy>=1.26.0
qdrant-client>=1.7.0  # Optional: for persistent vector cache
```

### `.gitignore`

```
# Secrets
.env
secrets/

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node
node_modules/

# IDE
.vscode/
.idea/

# Docker
*.log

# Qdrant
qdrant_storage/
```

---

## Appendix B: API Reference

### Health Endpoints

#### `GET /health`

Aggregate health status of all services.

**Response:**
```json
{
  "status": "healthy",
  "circuit_breakers": [
    {"name": "context7", "state": "closed", "failures": 0, "last_failure": null},
    {"name": "desktop-commander", "state": "half_open", "failures": 2, "last_failure": "2024-01-15T10:30:00"}
  ]
}
```

#### `GET /health/{server}`

Health status of a specific MCP server.

**Response:**
```json
{
  "server": "context7",
  "status": "healthy",
  "latency_ms": 45
}
```

---

### MCP Proxy Endpoints

#### `POST /mcp/{server}/{path:path}`

Proxy JSON-RPC requests to upstream MCP servers.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "resolve",
    "arguments": {"libraryName": "fastapi"}
  },
  "id": 1
}
```

**Headers:**
- `X-Client-Name`: Client identifier (e.g., `claude-desktop`, `vscode`)

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{"type": "text", "text": "FastAPI documentation..."}]
  },
  "id": 1
}
```

---

### Enhancement Endpoints

#### `POST /ollama/enhance`

Directly enhance a prompt via Ollama.

**Request:**
```json
{
  "prompt": "explain docker networking",
  "client": "claude-desktop"
}
```

**Response:**
```json
{
  "original": "explain docker networking",
  "enhanced": "Explain Docker networking concepts including bridge networks, host networking, overlay networks, and how containers communicate. Include practical examples.",
  "model": "deepseek-r1:14b",
  "cached": false
}
```

---

### Tool Schema Endpoints

#### `GET /tools/schemas`

Fetch tool schemas from all registered MCP servers.

**Response:**
```json
{
  "context7": [
    {
      "name": "resolve",
      "description": "Resolve library documentation",
      "inputSchema": {
        "type": "object",
        "properties": {
          "libraryName": {"type": "string"}
        },
        "required": ["libraryName"]
      }
    }
  ],
  "desktop-commander": [
    {
      "name": "read_file",
      "description": "Read file contents",
      "inputSchema": {...}
    }
  ]
}
```

---

### Pipeline Endpoints

#### `POST /pipelines/documentation`

Generate documentation from a codebase.

**Query Parameters:**
- `repo_path` (required): Path to repository
- `project_name` (required): Name for output file
- `vault_path` (optional): Obsidian vault path (default: `~/Obsidian/Projects`)

**Response:**
```json
{
  "status": "complete",
  "output_path": "~/Obsidian/Projects/my-project.md",
  "obsidian_url": "obsidian://open?vault=Obsidian&file=Projects/my-project"
}
```

---

### Dashboard Endpoints

#### `GET /dashboard`

Serve the dashboard HTML page.

#### `POST /dashboard/actions/clear-cache`

Clear the prompt cache.

**Response:**
```json
{"status": "cache_cleared"}
```

#### `POST /dashboard/actions/restart/{server}`

Restart a specific MCP server (STDIO adapters only).

**Response:**
```json
{"status": "context7_restarted"}
```

---

### Error Responses

All endpoints return standard JSON-RPC errors:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {"detail": "Server 'unknown' not registered"}
  },
  "id": 1
}
```

**Common Error Codes:**
| Code | Meaning |
|------|---------|
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| -32000 | Server error (circuit breaker open) |
| -32001 | Timeout |
