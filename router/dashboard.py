"""Dashboard routes for MCP Router.

Serves the HTMX-powered dashboard and partial templates for real-time updates.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from router.middleware.enhance import EnhancementMiddleware
    from router.registry import ServerRegistry

logger = logging.getLogger(__name__)

# Initialize templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Create router
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_enhancement_middleware(request: Request) -> "EnhancementMiddleware | None":
    """Get enhancement middleware from app state."""
    return getattr(request.app.state, "enhancement_middleware", None)


def get_server_registry(request: Request) -> "ServerRegistry | None":
    """Get server registry from app state."""
    return getattr(request.app.state, "server_registry", None)


def get_request_log(request: Request) -> list:
    """Get request log from app state."""
    return list(getattr(request.app.state, "request_log", []))


@dashboard_router.get("", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Serve the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@dashboard_router.get("/health-partial", response_class=HTMLResponse)
async def health_partial(request: Request) -> HTMLResponse:
    """HTMX partial for services health status."""
    services = []

    # Check Ollama
    http_client = getattr(request.app.state, "http_client", None)
    if http_client:
        from router.config import get_settings

        settings = get_settings()
        try:
            response = await http_client.get(f"{settings.ollama_url}/api/tags", timeout=5.0)
            services.append({
                "name": "ollama",
                "status": "healthy" if response.status_code == 200 else "degraded",
            })
        except Exception:
            services.append({"name": "ollama", "status": "down"})

    # Check MCP servers
    registry = get_server_registry(request)
    if registry:
        server_health = await registry.all_health()
        services.extend(server_health)

    return templates.TemplateResponse(
        "partials/health.html",
        {"request": request, "services": services},
    )


@dashboard_router.get("/stats-partial", response_class=HTMLResponse)
async def stats_partial(request: Request) -> HTMLResponse:
    """HTMX partial for cache statistics."""
    middleware = get_enhancement_middleware(request)

    if middleware:
        stats = middleware.get_cache_stats()
    else:
        stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "hit_rate": 0.0,
        }

    return templates.TemplateResponse(
        "partials/stats.html",
        {"request": request, "stats": stats},
    )


@dashboard_router.get("/breakers-partial", response_class=HTMLResponse)
async def breakers_partial(request: Request) -> HTMLResponse:
    """HTMX partial for circuit breaker status."""
    registry = get_server_registry(request)

    if registry:
        breakers = registry.all_circuit_breaker_status()
    else:
        breakers = []

    return templates.TemplateResponse(
        "partials/breakers.html",
        {"request": request, "breakers": breakers},
    )


@dashboard_router.get("/activity-partial", response_class=HTMLResponse)
async def activity_partial(request: Request) -> HTMLResponse:
    """HTMX partial for recent activity log."""
    request_log = get_request_log(request)

    # Format activity items
    activity = []
    for item in reversed(request_log[-50:]):
        timestamp = item.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                time_str = timestamp[:8]
        else:
            time_str = "--:--:--"

        status = item.get("status", 0)
        if status >= 500:
            status_class = "5xx"
        elif status >= 400:
            status_class = "4xx"
        else:
            status_class = "2xx"

        activity.append({
            "time": time_str,
            "method": item.get("method", "?"),
            "path": item.get("path", "/"),
            "status": status,
            "status_class": status_class,
            "latency_ms": item.get("latency_ms", 0),
        })

    return templates.TemplateResponse(
        "partials/activity.html",
        {"request": request, "activity": activity},
    )
