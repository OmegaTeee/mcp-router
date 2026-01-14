"""Configuration management for MCP Router."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama Configuration
    ollama_host: str = Field(default="localhost", description="Ollama server host")
    ollama_port: int = Field(default=11434, description="Ollama server port")
    ollama_model: str = Field(default="deepseek-r1", description="Default Ollama model")

    # Router Configuration
    router_host: str = Field(default="0.0.0.0", description="Router bind host")
    router_port: int = Field(default=9090, description="Router bind port")
    log_level: str = Field(default="info", description="Logging level")

    # MCP Server URLs (when running in containers)
    context7_url: str = Field(default="http://context7:3001", description="Context7 server URL")
    desktop_commander_url: str = Field(
        default="http://desktop-commander:3002", description="Desktop Commander server URL"
    )
    sequential_thinking_url: str = Field(
        default="http://sequential-thinking:3003", description="Sequential Thinking server URL"
    )

    # Cache Configuration
    cache_max_size: int = Field(default=1000, description="Max cache entries")
    cache_similarity_threshold: float = Field(
        default=0.85, description="Semantic similarity threshold for L2 cache"
    )

    # Qdrant Configuration (for persistent L2 cache)
    qdrant_url: str | None = Field(default=None, description="Qdrant server URL")

    # Optional API Keys
    obsidian_api_key: str | None = Field(default=None, description="Obsidian REST API key")
    figma_api_key: str | None = Field(default=None, description="Figma API key")

    @property
    def ollama_url(self) -> str:
        """Construct Ollama API URL."""
        # Handle case where OLLAMA_HOST might already include protocol
        host = self.ollama_host
        if host.startswith("http://") or host.startswith("https://"):
            # Already a full URL, extract just host:port or use as-is
            return host.rstrip("/")
        return f"http://{host}:{self.ollama_port}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
