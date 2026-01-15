"""STDIO transport adapter for MCP servers.

Wraps STDIO-based MCP servers (most Node.js servers) as callable services.
Handles subprocess management, JSON-RPC message framing, and automatic restarts.
"""

import asyncio
import itertools
import json
import logging
from asyncio.subprocess import Process
from typing import Any

logger = logging.getLogger(__name__)


class StdioAdapter:
    """Wraps STDIO MCP servers as HTTP-callable services.

    Most community MCP servers communicate via newline-delimited JSON over
    stdin/stdout. This adapter manages the subprocess lifecycle and provides
    an async interface for sending requests.
    """

    def __init__(
        self,
        name: str,
        command: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_restarts: int = 3,
    ):
        """Initialize STDIO adapter.

        Args:
            name: Server identifier for logging
            command: Command and args to start the server
            env: Additional environment variables
            timeout: Request timeout in seconds
            max_restarts: Maximum restart attempts before giving up
        """
        self.name = name
        self.command = command
        self.env = env or {}
        self.timeout = timeout
        self.max_restarts = max_restarts

        self.process: Process | None = None
        self.restart_count = 0
        self._lock = asyncio.Lock()
        self._request_id_gen = itertools.count(1)

    async def start(self) -> None:
        """Start the subprocess."""
        import os

        # Merge environment
        full_env = {**os.environ, **self.env}

        logger.info(f"Starting STDIO server {self.name}: {' '.join(self.command)}")

        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )

        # Start stderr reader (for logging)
        asyncio.create_task(self._read_stderr())

        logger.info(f"STDIO server {self.name} started (PID: {self.process.pid})")

    async def _read_stderr(self) -> None:
        """Read and log stderr output."""
        if not self.process or not self.process.stderr:
            return

        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                logger.debug(f"[{self.name}] {line.decode().strip()}")
        except Exception as e:
            logger.debug(f"[{self.name}] stderr reader stopped: {e}")

    async def call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send JSON-RPC request and receive response.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response object

        Raises:
            RuntimeError: If max restarts exceeded
            TimeoutError: If response not received in time
        """
        async with self._lock:
            # Ensure process is running
            if not self.is_healthy():
                await self._restart()

            if not self.process or not self.process.stdin or not self.process.stdout:
                raise RuntimeError(f"Server {self.name} not available")

            # Assign request ID if not present
            if "id" not in request or request["id"] is None:
                request["id"] = next(self._request_id_gen)

            # Write newline-delimited JSON per MCP spec
            line = json.dumps(request) + "\n"

            try:
                self.process.stdin.write(line.encode())
                await self.process.stdin.drain()

                # Read response with timeout
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=self.timeout,
                )

                if not response_line:
                    raise RuntimeError(f"Server {self.name} closed connection")

                return json.loads(response_line.decode())

            except asyncio.TimeoutError:
                logger.error(f"Server {self.name} timed out after {self.timeout}s")
                await self._restart()
                raise TimeoutError(f"STDIO server {self.name} timed out")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {self.name}: {e}")
                raise RuntimeError(f"Invalid response from {self.name}")

    async def _restart(self) -> None:
        """Restart crashed process with limits."""
        if self.restart_count >= self.max_restarts:
            raise RuntimeError(
                f"Server {self.name} exceeded max restarts ({self.max_restarts})"
            )

        logger.warning(
            f"Restarting {self.name} (attempt {self.restart_count + 1}/{self.max_restarts})"
        )

        await self.stop()
        self.restart_count += 1
        await self.start()

    async def stop(self) -> None:
        """Graceful shutdown."""
        if self.process:
            logger.info(f"Stopping STDIO server {self.name}")

            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Force killing {self.name}")
                self.process.kill()
                await self.process.wait()

            self.process = None

    def is_healthy(self) -> bool:
        """Check if subprocess is running."""
        return self.process is not None and self.process.returncode is None

    def reset_restart_count(self) -> None:
        """Reset restart counter after successful operation."""
        self.restart_count = 0

    def status(self) -> dict[str, Any]:
        """Get adapter status."""
        return {
            "name": self.name,
            "healthy": self.is_healthy(),
            "pid": self.process.pid if self.process else None,
            "restart_count": self.restart_count,
            "max_restarts": self.max_restarts,
        }


class StdioAdapterRegistry:
    """Registry of STDIO adapters for MCP servers."""

    def __init__(self):
        """Initialize empty registry."""
        self.adapters: dict[str, StdioAdapter] = {}

    def register(
        self,
        name: str,
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> StdioAdapter:
        """Register a new STDIO adapter.

        Args:
            name: Server identifier
            command: Command to start server
            env: Environment variables

        Returns:
            The created adapter
        """
        adapter = StdioAdapter(name=name, command=command, env=env)
        self.adapters[name] = adapter
        return adapter

    def get(self, name: str) -> StdioAdapter | None:
        """Get adapter by name."""
        return self.adapters.get(name)

    async def start_all(self) -> None:
        """Start all registered adapters."""
        for adapter in self.adapters.values():
            await adapter.start()

    async def stop_all(self) -> None:
        """Stop all registered adapters."""
        for adapter in self.adapters.values():
            await adapter.stop()

    def all_status(self) -> list[dict[str, Any]]:
        """Get status of all adapters."""
        return [adapter.status() for adapter in self.adapters.values()]
