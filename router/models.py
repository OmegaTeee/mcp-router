"""JSON-RPC models for MCP protocol handling."""

from typing import Any

from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request model per MCP specification."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to invoke")
    params: dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: int | str | None = Field(default=None, description="Request identifier")


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: dict[str, Any] | None = Field(default=None, description="Additional error data")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response model."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: dict[str, Any] | list[Any] | None = Field(default=None, description="Result data")
    error: JSONRPCError | None = Field(default=None, description="Error object if failed")
    id: int | str | None = Field(default=None, description="Request identifier")


# Standard JSON-RPC error codes
class ErrorCode:
    """Standard JSON-RPC and MCP error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes (-32000 to -32099)
    SERVER_ERROR = -32000  # Circuit breaker open
    TIMEOUT = -32001
    UPSTREAM_ERROR = -32002


class MCPToolCall(BaseModel):
    """MCP tool call parameters."""

    name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPToolResult(BaseModel):
    """MCP tool result content."""

    type: str = Field(default="text", description="Content type")
    text: str = Field(default="", description="Text content")


class ServerConfig(BaseModel):
    """MCP server configuration."""

    transport: str = Field(..., description="Transport type: 'http' or 'stdio'")
    url: str | None = Field(default=None, description="Server URL (for HTTP transport)")
    command: list[str] | None = Field(default=None, description="Command (for STDIO transport)")
    health_endpoint: str | None = Field(default=None, description="Health check path")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class EnhancementRule(BaseModel):
    """Client-specific enhancement configuration."""

    enabled: bool = Field(default=True, description="Whether enhancement is enabled")
    model: str = Field(..., description="Ollama model to use")
    system_prompt: str = Field(..., description="System prompt for enhancement")


class EnhancementConfig(BaseModel):
    """Full enhancement configuration."""

    default: EnhancementRule = Field(..., description="Default enhancement rule")
    clients: dict[str, EnhancementRule] = Field(
        default_factory=dict, description="Client-specific rules"
    )
    fallback_chain: list[str | None] = Field(
        default_factory=list, description="Fallback model chain"
    )
