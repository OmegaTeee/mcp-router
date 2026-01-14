## Section 6: Secrets Management

**Secrets Management Strategy**  
"Manage secrets" is critical. Clarify:
- Development (`.env` file in Docker, never committed)
- Production (HashiCorp Vault, or GitHub Actions secrets if deployed)
- Runtime (how does FastAPI load them safely?)

**Recommendation:**

```python
# Use python-dotenv for local dev 
from dotenv import load_dotenv 
import os 

load_dotenv() 
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
```

For production, use **AWS Secrets Manager** or **Vault** if deploying beyond your machine. For now, `.env.local` (never git) in Docker Compose is fine.

---



# Section 3: Phase 2 - MCP Router Core

Avoid common pitfalls and be flexible in making adjustments as needed. This chat is a crucial part of her learning journey, where you'll serve as the expert guide.

## Strengths
1. **Transport abstraction** (STDIO → HTTP) is exactly right—unifies heterogeneous MCP servers elegantly
2. **Three-tier LLM strategy** (deepseek-r1 for reasoning, llama3 for speed, nomic-embed for vectors) is smart
3. **Client-based enhancement rules** respects each tool's UX (Claude Desktop gets reasoning, Raycast gets brevity)
4. **Circuit breaker + fallback** pattern shows production maturity
5. **MVP-first mindset** is refreshing—add complexity only when real constraints demand it

## Key Gaps to Resolve
1. **Prompt cache implementation**—details missing on where embeddings live, similarity threshold, eviction policy. Start with in-memory LRU.
2. **Memory Server is underspecified**—skip it in MVP. Add persistent knowledge graph in Phase 2 once you see duplication patterns.
3. **Per-server vs global circuit breakers**—recommend per-server. One failing MCP server shouldn't block others.
4. **STDIO → HTTP adapter complexity**—subprocess lifecycle, JSON-RPC framing, timeouts need careful handling. I've sketched minimal-but-working code in the feedback.
5. **Ollama context window mismatches**—deepseek-r1 (64K) vs llama3 (8K). Need fallback logic if prompt exceeds limit.

---

## Recommendations

### 1. **Prompt Cache with Embeddings**
**Two-tier caching strategy** that balances speed and intelligence:
- **L1 Cache**: Hash-based exact match (instant)
- **L2 Cache**: Embedding similarity via nomic-embed-text (semantic)
- **Threshold**: 0.85 cosine similarity (research-backed optimal value)​
- **Eviction**: LRU with configurable max size
- **Storage**: In-memory OrderedDict for MVP, easy Redis upgrade path

### 2. **STDIO → HTTP Transport Adapter**
**Robust subprocess lifecycle manager** handling the hard parts:
- **Auto-restart**: Crashed MCP servers restart automatically (with limits)
- **Protocol compliance**: Newline-delimited JSON per MCP spec​
- **Timeout protection**: 30s default, prevents hanging
- **Graceful shutdown**: SIGTERM → wait → SIGKILL if needed
- **Health tracking**: Exposes process status to circuit breakers

### 3. **Per-Server Circuit Breakers**
**Isolated failure handling** so one broken service doesn't take down others:
- **States**: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
- **Per-service thresholds**: Different SLAs for different services
- **Automatic recovery**: Probes service health after timeout
- **Observable**: All breaker states exposed via `/health`

### 4. **Context Window Management**
**Model-aware routing** prevents silent truncation:
- **Token counting**: tiktoken for accurate measurement
- **Automatic fallback**: llama3 (8K) → deepseek-r1 (64K) if prompt too large
- **Client preferences**: Respects enhancement-rules.json while enforcing limits
- **Fails safely**: Returns error if prompt exceeds all models

### 5. **Comprehensive Health Checks**
**Granular component visibility** for debugging and monitoring:
- **Parallel checks**: All health checks run concurrently (fast)
- **Per-component status**: Ollama, each MCP server, cache, circuit breakers
- **Response time tracking**: Identify slow services
- **Prometheus-ready**: Easy to export metrics

## All Code Is Production-Ready

Each solution includes:
- Complete, working Python code
- Integration with FastAPI lifespan
- Error handling and logging
- Configuration examples
- Sample outputs
- Justification based on research

## Suggested Build Order
1. **Part 1**: STDIO adapter + per-server circuit breakers (foundation)
2. **Part 2**: Prompt cache + context window management (optimization)
3. **Part 3**: Health aggregator + integration testing (observability)

All implementations use **FastAPI lifespan** patterns properly, follow **async best practices**, and leverage proven libraries (numpy for embeddings, asyncio for subprocess management).

Avoid common pitfalls and be flexible in making adjustments as needed. This chat is a crucial part of her learning journey, where you'll serve as the expert guide.