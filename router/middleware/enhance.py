"""Prompt enhancement middleware using Ollama.

Enhances prompts based on client-specific rules before forwarding
to MCP servers or AI services.
"""

import json
import logging
from pathlib import Path

import httpx

from router.cache import PromptCache
from router.models import EnhancementConfig, EnhancementRule

logger = logging.getLogger(__name__)


# Model context limits (in tokens, approximate)
MODEL_LIMITS: dict[str, int] = {
    "llama3.2:3b": 128_000,
    "llama3": 8_000,
    "deepseek-r1:14b": 64_000,
    "deepseek-r1": 64_000,
    "qwen2.5-coder:7b": 128_000,
    "phi3:mini": 128_000,
    "nomic-embed-text": 8_000,
}


class EnhancementMiddleware:
    """Middleware for Ollama-based prompt enhancement."""

    def __init__(
        self,
        ollama_url: str,
        config_path: Path | str = "configs/enhancement-rules.json",
        cache: PromptCache | None = None,
    ):
        """Initialize enhancement middleware.

        Args:
            ollama_url: Ollama API base URL
            config_path: Path to enhancement rules config
            cache: Optional prompt cache instance
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.config_path = Path(config_path)
        self.cache = cache or PromptCache()
        self.config: EnhancementConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load enhancement rules from config file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)
                    # Parse default rule
                    default = EnhancementRule(**data.get("default", {}))
                    # Parse client-specific rules
                    clients = {
                        name: EnhancementRule(**rule)
                        for name, rule in data.get("clients", {}).items()
                    }
                    self.config = EnhancementConfig(
                        default=default,
                        clients=clients,
                        fallback_chain=data.get("fallback_chain", []),
                    )
                    logger.info(f"Loaded enhancement rules from {self.config_path}")
            else:
                logger.warning(f"Config not found at {self.config_path}, using defaults")
                self.config = EnhancementConfig(
                    default=EnhancementRule(
                        enabled=True,
                        model="llama3.2:3b",
                        system_prompt="Improve clarity and structure. Preserve intent.",
                    ),
                    clients={},
                    fallback_chain=[],
                )
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def get_rule(self, client: str | None) -> EnhancementRule:
        """Get enhancement rule for a client.

        Args:
            client: Client identifier (e.g., 'claude-desktop', 'vscode')

        Returns:
            EnhancementRule for the client or default
        """
        if self.config is None:
            self._load_config()

        assert self.config is not None

        if client and client in self.config.clients:
            return self.config.clients[client]
        return self.config.default

    async def enhance(
        self,
        prompt: str,
        client: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> dict:
        """Enhance a prompt using Ollama.

        Args:
            prompt: Original prompt text
            client: Client identifier for rule selection
            http_client: HTTP client for Ollama requests

        Returns:
            Dictionary with original, enhanced, model, and cached fields
        """
        rule = self.get_rule(client)

        # Check if enhancement is disabled
        if not rule.enabled:
            return {
                "original": prompt,
                "enhanced": prompt,
                "model": None,
                "cached": False,
                "skipped": True,
            }

        # Check cache first
        cached_entry = self.cache.get(prompt)
        if cached_entry:
            return {
                "original": prompt,
                "enhanced": cached_entry.response,
                "model": cached_entry.model,
                "cached": True,
            }

        # Create client if not provided
        client_created = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=60.0)
            client_created = True

        try:
            enhanced = await self._call_ollama(prompt, rule, http_client)

            # Cache the result
            self.cache.put(prompt, enhanced, rule.model)

            return {
                "original": prompt,
                "enhanced": enhanced,
                "model": rule.model,
                "cached": False,
            }
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            # Fallback: return original prompt
            return {
                "original": prompt,
                "enhanced": prompt,
                "model": rule.model,
                "cached": False,
                "error": str(e),
            }
        finally:
            if client_created:
                await http_client.aclose()

    async def _call_ollama(
        self,
        prompt: str,
        rule: EnhancementRule,
        http_client: httpx.AsyncClient,
    ) -> str:
        """Call Ollama API for enhancement.

        Includes fallback chain if primary model fails.
        """
        models_to_try = [rule.model]

        # Add fallback chain if configured
        if self.config and self.config.fallback_chain:
            models_to_try.extend(
                m for m in self.config.fallback_chain if m is not None and m != rule.model
            )

        last_error: Exception | None = None

        for model in models_to_try:
            try:
                # Check context limit
                if not self._check_context_limit(prompt, model):
                    logger.warning(f"Prompt too large for {model}, trying next")
                    continue

                response = await http_client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        # Code review comment: [nitpick] The enhancement prompt is hardcoded in the method. If different enhancement strategies or prompt templates are needed, this creates duplication. Consider moving the enhancement template to the EnhancementRule model or configuration to make it configurable per client.
                        # Suggestion: Build enhancement prompt from rule template (if provided)
                        # template = getattr(
                        #     rule,
                        #     "enhancement_prompt_template",
                        #     "Enhance this prompt:\n\n{prompt}",
                        # )
                        # enhancement_prompt = template.format(prompt=prompt)
                        # 
                        # response = await http_client.post(
                        #     f"{self.ollama_url}/api/generate",
                        #     json={
                        #         "model": model,
                        #         "prompt": enhancement_prompt,
                        "prompt": f"Enhance this prompt:\n\n{prompt}",
                        "system": rule.system_prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", prompt).strip()

            except httpx.HTTPError as e:
                logger.warning(f"Ollama {model} failed: {e}")
                last_error = e
                continue

        # All models failed
        if last_error:
            raise last_error
        return prompt

    def _check_context_limit(self, prompt: str, model: str) -> bool:
        """Check if prompt fits within model's context limit.

        Uses rough token estimation (4 chars per token).
        """
        estimated_tokens = len(prompt) // 4
        limit = MODEL_LIMITS.get(model, 8_000)
        return estimated_tokens < limit * 0.9  # 90% of limit for safety

    async def get_embedding(
        self,
        text: str,
        http_client: httpx.AsyncClient,
        model: str = "nomic-embed-text",
    ) -> list[float] | None:
        """Get embedding vector for text using Ollama.

        Args:
            text: Text to embed
            http_client: HTTP client
            model: Embedding model name

        Returns:
            Embedding vector or None if failed
        """
        try:
            response = await http_client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding")
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self.cache.clear()
