"""MCP Server Registry - manages server configurations and adapters.

Loads server definitions from configs/mcp-servers.json and creates
appropriate adapters (HTTP or STDIO) for each server.
"""

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from router.adapters.stdio import StdioAdapter
from router.circuit_breaker import CircuitBreakerRegistry
from router.models import JSONRPCRequest, JSONRPCResponse, ErrorCode, ServerConfig

logger = logging.getLogger(__name__)


class ServerRegistry:
    """Registry of MCP servers with transport adapters."""

    def __init__(
        self,
        config_path: Path | str = "configs/mcp-servers.json",
        http_client: httpx.AsyncClient | None = None,
    ):
        """Initialize server registry.

        Args:
            config_path: Path to server configuration file
            http_client: Shared HTTP client for HTTP-transport servers
        """
        self.config_path = Path(config_path)
        self.http_client = http_client
        self.servers: dict[str, ServerConfig] = {}
        self.stdio_adapters: dict[str, StdioAdapter] = {}
        self.circuit_breakers = CircuitBreakerRegistry()
        self._load_config()

    def _load_config(self) -> None:
        """Load server configurations from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)
                    for name, config in data.get("servers", {}).items():
                        self.servers[name] = ServerConfig(**config)
                        # Code Review Commet: Consider validating server configurations here to catch errors early. The variable config is a ServerConfig Pydantic model, not a dictionary. Calling .get('transport') will raise an AttributeError. Use config.transport instead to access the attribute.
                        logger.info(f"Registered server: {name} ({config.get('transport')})")
            else:
                logger.warning(f"Config not found at {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load server config: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize all servers (start STDIO adapters)."""
        for name, config in self.servers.items():
            if config.transport == "stdio" and config.command:
                adapter = StdioAdapter(
                    name=name,
                    command=config.command,
                    env=config.env,
                )
                self.stdio_adapters[name] = adapter
                try:
                    await adapter.start()
                except Exception as e:
                    logger.error(f"Failed to start {name}: {e}")
                    self.circuit_breakers.get(name).record_failure()

    async def shutdown(self) -> None:
        """Shutdown all STDIO adapters."""
        for adapter in self.stdio_adapters.values():
            await adapter.stop()

    def list_servers(self) -> list[str]:
        """List registered server names."""
        return list(self.servers.keys())

    def get_config(self, name: str) -> ServerConfig | None:
        """Get server configuration by name."""
        return self.servers.get(name)

    async def call(
        self,
        server: str,
        request: JSONRPCRequest,
    ) -> JSONRPCResponse:
        """Route JSON-RPC request to appropriate server.

        Args:
            server: Target server name
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        if server not in self.servers:
            return JSONRPCResponse(
                error={
                    "code": ErrorCode.INVALID_REQUEST,
                    "message": f"Unknown server: {server}",
                    "data": {"available": self.list_servers()},
                },
                id=request.id,
            )

        # Check circuit breaker
        breaker = self.circuit_breakers.get(server)
        if not breaker.can_execute():
            return JSONRPCResponse(
                error={
                    "code": ErrorCode.SERVER_ERROR,
                    "message": f"Server {server} circuit breaker open",
                    "data": {"state": breaker.status()},
                },
                id=request.id,
            )

        config = self.servers[server]

        try:
            if config.transport == "stdio":
                result = await self._call_stdio(server, request)
            else:
                result = await self._call_http(server, config, request)

            breaker.record_success()
            return result

        except Exception as e:
            logger.error(f"Request to {server} failed: {e}")
            breaker.record_failure()
            return JSONRPCResponse(
                error={
                    "code": ErrorCode.UPSTREAM_ERROR,
                    "message": str(e),
                },
                id=request.id,
            )

    async def _call_stdio(
        self,
        server: str,
        request: JSONRPCRequest,
    ) -> JSONRPCResponse:
        """Route request to STDIO adapter."""
        adapter = self.stdio_adapters.get(server)
        if not adapter:
            raise RuntimeError(f"STDIO adapter not initialized for {server}")

        response = await adapter.call(request.model_dump())
        return JSONRPCResponse(**response)

    async def _call_http(
        self,
        server: str,
        config: ServerConfig,
        request: JSONRPCRequest,
    ) -> JSONRPCResponse:
        """Route request to HTTP server."""
        if not self.http_client:
            raise RuntimeError("HTTP client not initialized")

        if not config.url:
            raise RuntimeError(f"No URL configured for {server}")

        response = await self.http_client.post(
            config.url,
            json=request.model_dump(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return JSONRPCResponse(**response.json())

    async def health_check(self, server: str) -> dict[str, Any]:
        """Check health of a specific server.

        Args:
            server: Server name

        Returns:
            Health status dictionary
        """
        if server not in self.servers:
            return {"name": server, "status": "unknown", "error": "Not registered"}

        config = self.servers[server]
        breaker = self.circuit_breakers.get(server)

        if config.transport == "stdio":
            adapter = self.stdio_adapters.get(server)
            healthy = adapter.is_healthy() if adapter else False
            return {
                "name": server,
                "status": "healthy" if healthy else "down",
                "transport": "stdio",
                "circuit_breaker": breaker.status(),
            }
        else:
            # HTTP health check
            if not self.http_client or not config.url:
                return {"name": server, "status": "unknown", "error": "No HTTP client"}

            health_url = config.url
            if config.health_endpoint:
                health_url = f"{config.url.rstrip('/')}{config.health_endpoint}"

            try:
                response = await self.http_client.get(health_url, timeout=5.0)
                return {
                    "name": server,
                    "status": "healthy" if response.status_code == 200 else "degraded",
                    "transport": "http",
                    "status_code": response.status_code,
                    "circuit_breaker": breaker.status(),
                }
            except Exception as e:
                return {
                    "name": server,
                    "status": "down",
                    "transport": "http",
                    "error": str(e),
                    "circuit_breaker": breaker.status(),
                }

    async def all_health(self) -> list[dict[str, Any]]:
        """Check health of all servers."""
        results = []
        for server in self.servers:
            results.append(await self.health_check(server))
        return results

    def all_circuit_breaker_status(self) -> list[dict]:
        """Get all circuit breaker statuses."""
        return self.circuit_breakers.all_status()
