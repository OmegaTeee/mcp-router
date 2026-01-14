"""MCP Router - Main FastAPI application.

A containerized MCP router that:
- Proxies multiple MCP servers through a single endpoint
- Enhances prompts via local Ollama before forwarding
- Provides circuit breakers for fault tolerance
- Supports client-specific enhancement rules
"""

import logging
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from router.cache import PromptCache
from router.config import get_settings
from router.dashboard import dashboard_router
from router.middleware.enhance import EnhancementMiddleware
from router.models import JSONRPCRequest, JSONRPCResponse, ErrorCode
from router.pipelines.documentation import documentation_pipeline
from router.registry import ServerRegistry
from router.sse import sse_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global state
http_client: httpx.AsyncClient | None = None
server_registry: ServerRegistry | None = None
enhancement_middleware: EnhancementMiddleware | None = None
# Code review comment: The variable request_log lacks a type annotation for the deque's contents. Adding deque[dict[str, Any]] would improve type safety and make it clear what structure the log entries have.
request_log: deque = deque(maxlen=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global http_client, server_registry, enhancement_middleware

    settings = get_settings()
    logger.info(f"Starting MCP Router on {settings.router_host}:{settings.router_port}")
    logger.info(f"Ollama endpoint: {settings.ollama_url}")

    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=60.0)

    # Initialize prompt cache (with Qdrant for L2 if configured)
    cache = PromptCache(
        max_size=settings.cache_max_size,
        similarity_threshold=settings.cache_similarity_threshold,
        qdrant_url=settings.qdrant_url,
    )

    # Initialize enhancement middleware
    enhancement_middleware = EnhancementMiddleware(
        ollama_url=settings.ollama_url,
        config_path="configs/enhancement-rules.json",
        cache=cache,
    )

    # Initialize server registry
    server_registry = ServerRegistry(
        config_path="configs/mcp-servers.json",
        http_client=http_client,
    )

    # Check Ollama connectivity
    try:
        response = await http_client.get(f"{settings.ollama_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "unknown") for m in models]
            logger.info(f"Ollama connected. Available models: {model_names}")
        else:
            logger.warning(f"Ollama returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"Ollama not available: {e}. Prompt enhancement will fail gracefully.")

    # Initialize STDIO adapters to spawn MCP server subprocesses
    await server_registry.initialize()

    # Store state for dashboard access
    app.state.http_client = http_client
    app.state.server_registry = server_registry
    app.state.enhancement_middleware = enhancement_middleware
    app.state.request_log = request_log

    yield

    # Cleanup
    if server_registry:
        await server_registry.shutdown()
    if http_client:
        await http_client.aclose()

    logger.info("MCP Router shutdown complete")


app = FastAPI(
    title="MCP Router",
    description="Containerized MCP router with Ollama prompt enhancement",
    version="0.2.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(dashboard_router)
app.include_router(sse_router)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for dashboard."""
    start = datetime.now()
    response = await call_next(request)
    elapsed = (datetime.now() - start).total_seconds() * 1000

    request_log.append({
        "timestamp": start.isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": round(elapsed, 1),
        "client": request.headers.get("X-Client-Name", "unknown"),
    })

    return response


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Aggregate health check for all services."""
    result: dict[str, Any] = {"status": "healthy", "services": [], "circuit_breakers": []}

    # Check Ollama
    if http_client:
        settings = get_settings()
        try:
            response = await http_client.get(f"{settings.ollama_url}/api/tags", timeout=5.0)
            result["services"].append({
                "name": "ollama",
                "status": "healthy" if response.status_code == 200 else "degraded",
            })
        except Exception:
            result["services"].append({"name": "ollama", "status": "down"})

    # Check MCP servers
    if server_registry:
        result["services"].extend(await server_registry.all_health())
        result["circuit_breakers"] = server_registry.all_circuit_breaker_status()

    # Overall status
    if any(s.get("status") == "down" for s in result["services"]):
        result["status"] = "degraded"

    return result


@app.get("/health/{server}")
async def server_health(server: str) -> dict[str, Any]:
    """Health check for specific MCP server."""
    if not server_registry:
        raise HTTPException(status_code=503, detail="Server registry not initialized")

    return await server_registry.health_check(server)


# =============================================================================
# Root & Info Endpoints
# =============================================================================


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with router info."""
    settings = get_settings()
    servers = server_registry.list_servers() if server_registry else []

    return {
        "name": "MCP Router",
        "version": "0.2.0",
        "ollama": {
            "url": settings.ollama_url,
            "model": settings.ollama_model,
        },
        "servers": servers,
        "endpoints": [
            "GET  /health",
            "GET  /health/{server}",
            "POST /ollama/enhance",
            "POST /mcp/{server}",
            "GET  /tools/schemas",
            "GET  /stats",
            "GET  /dashboard",
            "GET  /sse",
            "POST /message",
            "POST /pipelines/documentation",
        ],
    }


# =============================================================================
# Enhancement Endpoints
# =============================================================================


@app.post("/ollama/enhance")
async def enhance_prompt(request: Request) -> dict[str, Any]:
    """Enhance a prompt using Ollama before forwarding to AI services."""
    if not enhancement_middleware:
        raise HTTPException(status_code=503, detail="Enhancement middleware not initialized")

    body = await request.json()
    prompt = body.get("prompt", "")
    client = body.get("client") or request.headers.get("X-Client-Name")

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    result = await enhancement_middleware.enhance(
        prompt=prompt,
        client=client,
        http_client=http_client,
    )

    return result


# =============================================================================
# MCP Proxy Endpoints
# =============================================================================


@app.post("/mcp/{server}")
async def proxy_mcp_json_rpc(server: str, request: Request) -> JSONResponse:
    """Proxy JSON-RPC requests to upstream MCP servers.

    This is the main MCP routing endpoint. It:
    1. Parses the JSON-RPC request
    2. Optionally enhances the prompt (if applicable)
    3. Routes to the appropriate MCP server
    4. Returns the JSON-RPC response
    """
    if not server_registry:
        raise HTTPException(status_code=503, detail="Server registry not initialized")

    try:
        body = await request.json()
        rpc_request = JSONRPCRequest(**body)
    except Exception as e:
        return JSONResponse(
            content=JSONRPCResponse(
                error={"code": ErrorCode.PARSE_ERROR, "message": str(e)},
                id=None,
            ).model_dump(),
            status_code=400,
        )

    # Route to server
    response = await server_registry.call(server, rpc_request)

    return JSONResponse(
        content=response.model_dump(),
        status_code=200 if response.error is None else 502,
    )


@app.api_route("/mcp/{server}/{path:path}", methods=["GET", "POST"])
async def proxy_mcp_path(server: str, path: str, request: Request) -> JSONResponse:
    """Proxy path-based requests to upstream MCP servers.

    Supports both JSON-RPC and REST-style requests.
    """
    settings = get_settings()

    if not http_client:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    # Map server names to URLs (for HTTP-transport servers)
    server_map = {
        "context7": settings.context7_url,
        "desktop-commander": settings.desktop_commander_url,
        "sequential-thinking": settings.sequential_thinking_url,
    }

    if server not in server_map:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown server: {server}. Available: {list(server_map.keys())}",
        )

    upstream_url = f"{server_map[server]}/{path}"

    try:
        if request.method == "GET":
            response = await http_client.get(upstream_url)
        else:
            body = await request.body()
            response = await http_client.post(
                upstream_url,
                content=body,
                headers={"Content-Type": request.headers.get("content-type", "application/json")},
            )

        return JSONResponse(
            content=response.json() if response.content else {},
            status_code=response.status_code,
        )
    except httpx.HTTPError as e:
        logger.error(f"Upstream request to {server} failed: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


# =============================================================================
# Tool Schema Endpoints
# =============================================================================


@app.get("/tools/schemas")
async def list_tool_schemas() -> dict[str, Any]:
    """Fetch tool schemas from all registered MCP servers.

    Returns live schemas by calling tools/list on each server.
    """
    if not server_registry:
        raise HTTPException(status_code=503, detail="Server registry not initialized")

    schemas: dict[str, Any] = {}

    for server_name in server_registry.list_servers():
        try:
            request = JSONRPCRequest(method="tools/list", id=1)
            response = await server_registry.call(server_name, request)

            if response.error:
                schemas[server_name] = {"error": response.error}
            else:
                schemas[server_name] = response.result
        except Exception as e:
            schemas[server_name] = {"error": str(e)}

    return schemas


# =============================================================================
# Stats & Dashboard Endpoints
# =============================================================================


@app.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get router statistics."""
    stats: dict[str, Any] = {}

    if enhancement_middleware:
        stats["cache"] = enhancement_middleware.get_cache_stats()

    stats["recent_requests"] = list(request_log)[-50:]

    return stats


@app.post("/actions/clear-cache")
async def clear_cache() -> dict[str, str]:
    """Clear the prompt cache."""
    if enhancement_middleware:
        enhancement_middleware.clear_cache()
    return {"status": "cache_cleared"}


@app.post("/actions/reset-breakers")
async def reset_circuit_breakers() -> dict[str, str]:
    """Reset all circuit breakers."""
    if server_registry:
        server_registry.circuit_breakers.reset_all()
    return {"status": "breakers_reset"}


# =============================================================================
# Pipeline Endpoints
# =============================================================================


@app.post("/pipelines/documentation")
async def run_documentation_pipeline(
    repo_path: str,
    project_name: str,
    vault_path: str = "~/Obsidian/Projects",
) -> dict[str, Any]:
    """Generate documentation from a codebase and write to Obsidian.

    Args:
        repo_path: Path to the repository to document
        project_name: Name for the output file
        vault_path: Path to Obsidian vault
    """
    # Create wrapper functions for the pipeline
    async def enhance_fn(prompt: str, client: str) -> dict:
        if enhancement_middleware:
            return await enhancement_middleware.enhance(
                prompt=prompt,
                client=client,
                http_client=http_client,
            )
        return {"enhanced": prompt}

    async def route_fn(server: str, request: JSONRPCRequest):
        if server_registry:
            return await server_registry.call(server, request)
        return JSONRPCResponse(error={"code": -1, "message": "No registry"})

    return await documentation_pipeline(
        repo_path=repo_path,
        project_name=project_name,
        vault_path=vault_path,
        enhance_fn=enhance_fn,
        route_fn=route_fn,
    )


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Entry point for CLI."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "router.main:app",
        host=settings.router_host,
        port=settings.router_port,
        log_level=settings.log_level,
        reload=True,
    )


if __name__ == "__main__":
    main()
