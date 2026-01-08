"""MCP Router - Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from router.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# HTTP client for upstream requests
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global http_client
    settings = get_settings()

    logger.info(f"Starting MCP Router on {settings.router_host}:{settings.router_port}")
    logger.info(f"Ollama endpoint: {settings.ollama_url}")

    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=60.0)

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
        logger.warning(f"Ollama not available: {e}. Prompt enhancement disabled.")

    yield

    # Cleanup
    if http_client:
        await http_client.aclose()
    logger.info("MCP Router shutdown complete")


app = FastAPI(
    title="MCP Router",
    description="Containerized MCP router with Ollama prompt enhancement",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with router info."""
    settings = get_settings()
    return {
        "name": "MCP Router",
        "version": "0.1.0",
        "ollama": {
            "url": settings.ollama_url,
            "model": settings.ollama_model,
        },
        "endpoints": [
            "/health",
            "/ollama/enhance",
            "/mcp/{server}/{path}",
        ],
    }


@app.post("/ollama/enhance")
async def enhance_prompt(request: Request) -> dict[str, Any]:
    """Enhance a prompt using Ollama before forwarding to AI services."""
    settings = get_settings()

    if not http_client:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    body = await request.json()
    prompt = body.get("prompt", "")
    model = body.get("model", settings.ollama_model)

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    # System prompt for enhancement
    system_prompt = """You are a prompt enhancement assistant. Your task is to:
1. Clarify ambiguous requests
2. Add relevant context
3. Structure the prompt for better AI comprehension
4. Preserve the original intent

Return ONLY the enhanced prompt, no explanations."""

    try:
        response = await http_client.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": f"Enhance this prompt:\n\n{prompt}",
                "system": system_prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()
        enhanced = result.get("response", prompt)

        return {
            "original": prompt,
            "enhanced": enhanced.strip(),
            "model": model,
        }
    except httpx.HTTPError as e:
        logger.error(f"Ollama request failed: {e}")
        # Fallback: return original prompt
        return {
            "original": prompt,
            "enhanced": prompt,
            "model": model,
            "error": str(e),
        }


@app.api_route("/mcp/{server}/{path:path}", methods=["GET", "POST"])
async def proxy_mcp(server: str, path: str, request: Request) -> JSONResponse:
    """Proxy requests to upstream MCP servers."""
    settings = get_settings()

    if not http_client:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    # Map server names to URLs
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
