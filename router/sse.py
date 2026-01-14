"""SSE (Server-Sent Events) Transport for MCP.

Implements the SSE transport protocol used by Claude Desktop.
Clients connect to /sse to receive a session, then send messages
to /message?session_id=X and receive responses via the SSE stream.

MCP SSE Protocol:
1. Client GETs /sse → receives session_id and endpoint URL
2. Client POSTs to /message?session_id=X with JSON-RPC
3. Server streams responses back via SSE
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from router.models import JSONRPCRequest, JSONRPCResponse

logger = logging.getLogger(__name__)

# SSE Router
sse_router = APIRouter(tags=["sse"])

# Session storage (in-memory for simplicity)
# In production, use Redis or similar for distributed sessions
# Code review commet: Consider session expiration and cleanup mechanisms. The global sessions dictionary is accessed from multiple async handlers without synchronization. This creates a race condition where concurrent requests could lead to inconsistent state during session creation, deletion, or access. Consider using asyncio.Lock() to protect critical sections or use a thread-safe data structure.
sessions: dict[str, "SSESession"] = {}


class SSESession:
    """Represents an SSE connection session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.active = True
        self.created_at = asyncio.get_event_loop().time()

    async def send(self, event: str, data: Any) -> None:
        """Queue an SSE event to be sent."""
        if not self.active:
            return

        if isinstance(data, dict):
            data = json.dumps(data)

        message = f"event: {event}\ndata: {data}\n\n"
        await self.queue.put(message)

    async def send_json_rpc(self, response: JSONRPCResponse) -> None:
        """Send a JSON-RPC response."""
        await self.send("message", response.model_dump())

    def close(self) -> None:
        """Close the session."""
        self.active = False


async def event_generator(session: SSESession) -> AsyncGenerator[str, None]:
    """Generate SSE events from session queue."""
    try:
        while session.active:
            try:
                # Wait for events with timeout to allow cleanup
                message = await asyncio.wait_for(
                    session.queue.get(),
                    timeout=30.0,
                )
                yield message
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        logger.info(f"SSE session {session.session_id} cancelled")
    finally:
        session.close()
        if session.session_id in sessions:
            del sessions[session.session_id]


@sse_router.get("/sse")
async def sse_connect(request: Request) -> StreamingResponse:
    """Establish SSE connection for MCP transport.

    Returns a streaming response with:
    - Initial endpoint event containing the message URL
    - Subsequent message events with JSON-RPC responses
    """
    # Create new session
    session_id = str(uuid.uuid4())
    session = SSESession(session_id)
    sessions[session_id] = session

    logger.info(f"New SSE session: {session_id}")

    # Get base URL for message endpoint
    base_url = str(request.base_url).rstrip("/")
    message_url = f"{base_url}/message?session_id={session_id}"

    # Queue initial endpoint event
    await session.send("endpoint", message_url)

    return StreamingResponse(
        event_generator(session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@sse_router.post("/message")
async def sse_message(
    session_id: str,
    request: Request,
) -> dict[str, str]:
    """Receive MCP message and route to appropriate server.

    The response is sent via the SSE stream, not in this HTTP response.
    """
    # Validate session
    session = sessions.get(session_id)
    if not session or not session.active:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Parse JSON-RPC request
    try:
        body = await request.json()
        rpc_request = JSONRPCRequest(**body)
    except Exception as e:
        error_response = JSONRPCResponse(
            error={"code": -32700, "message": f"Parse error: {e}"},
            id=None,
        )
        await session.send_json_rpc(error_response)
        return {"status": "error_sent"}

    # Get server registry from app state
    server_registry = getattr(request.app.state, "server_registry", None)

    if not server_registry:
        error_response = JSONRPCResponse(
            error={"code": -32603, "message": "Server registry not available"},
            id=rpc_request.id,
        )
        await session.send_json_rpc(error_response)
        return {"status": "error_sent"}

    # Determine target server from method or params
    # MCP methods are typically like "tools/call" with server in params
    # or we can use a header/param to specify
    target_server = request.headers.get("X-MCP-Server")

    if not target_server:
        # Try to infer from method - check all servers
        # For now, broadcast to first available or return error
        servers = server_registry.list_servers()
        if servers:
            target_server = servers[0]
        else:
            error_response = JSONRPCResponse(
                error={"code": -32600, "message": "No target server specified"},
                id=rpc_request.id,
            )
            await session.send_json_rpc(error_response)
            return {"status": "error_sent"}

    # Route request
    try:
        response = await server_registry.call(target_server, rpc_request)
        await session.send_json_rpc(response)
        return {"status": "response_sent"}
    except Exception as e:
        error_response = JSONRPCResponse(
            error={"code": -32603, "message": str(e)},
            id=rpc_request.id,
        )
        await session.send_json_rpc(error_response)
        return {"status": "error_sent"}


@sse_router.delete("/sse/{session_id}")
async def sse_disconnect(session_id: str) -> dict[str, str]:
    """Explicitly close an SSE session."""
    session = sessions.get(session_id)
    if session:
        session.close()
        del sessions[session_id]
        logger.info(f"SSE session closed: {session_id}")
        return {"status": "closed"}

    raise HTTPException(status_code=404, detail="Session not found")


@sse_router.get("/sse/sessions")
async def list_sessions() -> dict[str, Any]:
    """List active SSE sessions (for debugging)."""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "active": s.active,
                "queue_size": s.queue.qsize(),
            }
            for s in sessions.values()
        ],
    }
