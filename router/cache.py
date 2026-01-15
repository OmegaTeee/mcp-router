"""Two-tier prompt cache with exact hash and semantic similarity matching.

L1 Cache: Exact string matching using hash lookups (instant, in-memory)
L2 Cache: Semantic similarity using Qdrant vector database (persistent)

L1 uses LRU eviction when full. L2 relies on Qdrant for storage management.
"""

import hashlib
import logging
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

# Qdrant collection name for prompt cache
QDRANT_COLLECTION = "prompt_cache"

# Embedding dimension for nomic-embed-text model
EMBEDDING_DIM = 768


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    prompt: str
    response: str
    model: str
    created_at: datetime = field(default_factory=datetime.now)
    hits: int = 0


@dataclass
class CacheStats:
    """Cache statistics."""

    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    total_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate overall cache hit rate."""
        total = self.l1_hits + self.l1_misses + self.l2_hits + self.l2_misses
        if total == 0:
            return 0.0
        return (self.l1_hits + self.l2_hits) / total

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "l1_hits": self.l1_hits,
            "l1_misses": self.l1_misses,
            "l2_hits": self.l2_hits,
            "l2_misses": self.l2_misses,
            "total_entries": self.total_entries,
            "hit_rate": round(self.hit_rate * 100, 2),
        }


class PromptCache:
    """Two-tier prompt cache with exact and semantic matching.

    L1 uses exact string hashing for instant lookups (in-memory).
    L2 uses Qdrant vector database for semantic similarity (persistent).
    """

    def __init__(
        self,
        max_size: int = 1000,
        similarity_threshold: float = 0.85,
        qdrant_url: str | None = None,
    ):
        """Initialize the cache.

        Args:
            max_size: Maximum entries in L1 cache
            similarity_threshold: Cosine similarity threshold for L2 (0.0-1.0)
            qdrant_url: Qdrant server URL (None to disable L2)
        """
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold

        # L1: Exact match cache (hash -> entry)
        self.exact_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # L2: Qdrant client for vector similarity
        self.qdrant: QdrantClient | None = None
        self.qdrant_url: str | None = None
        self.qdrant_available = False

        if qdrant_url:
            self._init_qdrant(qdrant_url)

        self.stats = CacheStats()

    def _init_qdrant(self, url: str) -> None:
        """Initialize Qdrant client and collection."""
        try:
            self.qdrant_url = url
            self.qdrant = QdrantClient(url=url, timeout=5.0)

            # Check if collection exists, create if not
            collections = self.qdrant.get_collections().collections
            collection_names = [c.name for c in collections]

            if QDRANT_COLLECTION not in collection_names:
                self.qdrant.create_collection(
                    collection_name=QDRANT_COLLECTION,
                    vectors_config=qdrant_models.VectorParams(
                        size=EMBEDDING_DIM,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {QDRANT_COLLECTION}")
            else:
                logger.info(f"Using existing Qdrant collection: {QDRANT_COLLECTION}")

            self.qdrant_available = True
            logger.info(f"Qdrant L2 cache connected: {url}")

        except Exception as e:
            logger.warning(f"Qdrant not available, L2 cache disabled: {e}")
            self.qdrant = None
            self.qdrant_available = False

    def _hash_prompt(self, prompt: str) -> str:
        """Create hash key for prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def get(
        self,
        prompt: str,
        embedding: list[float] | None = None,
    ) -> CacheEntry | None:
        """Look up prompt in cache.

        Args:
            prompt: The prompt to look up
            embedding: Optional embedding vector for L2 lookup

        Returns:
            CacheEntry if found, None otherwise
        """
        # L1: Exact match (fast path)
        prompt_hash = self._hash_prompt(prompt)
        if prompt_hash in self.exact_cache:
            entry = self.exact_cache[prompt_hash]
            # Move to end (LRU)
            self.exact_cache.move_to_end(prompt_hash)
            entry.hits += 1
            self.stats.l1_hits += 1
            logger.debug(f"L1 cache hit for prompt hash {prompt_hash}")
            return entry

        self.stats.l1_misses += 1

        # L2: Semantic similarity via Qdrant (if available and embedding provided)
        if embedding is not None and self.qdrant_available and self.qdrant:
            best_match = self._find_similar_qdrant(embedding)
            if best_match is not None:
                best_match.hits += 1
                self.stats.l2_hits += 1
                logger.debug("L2 cache hit via Qdrant semantic similarity")
                return best_match

            self.stats.l2_misses += 1

        return None

    def _find_similar_qdrant(self, embedding: list[float]) -> CacheEntry | None:
        """Find semantically similar cached entry using Qdrant.

        Uses cosine similarity with configurable threshold.
        """
        if not self.qdrant:
            return None

        try:
            results = self.qdrant.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=embedding,
                limit=1,
                score_threshold=self.similarity_threshold,
            )

            if results:
                payload = results[0].payload
                if payload:
                    created_at_raw = payload.get("created_at")
                    created_at = (
                        datetime.fromisoformat(created_at_raw)
                        if created_at_raw
                        else datetime.now()
                    )
                    return CacheEntry(
                        prompt=payload.get("prompt", ""),
                        response=payload.get("response", ""),
                        model=payload.get("model", ""),
                        created_at=created_at,
                        hits=payload.get("hits", 0),
                    )
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}")

        return None

    def put(
        self,
        prompt: str,
        response: str,
        model: str,
        embedding: list[float] | None = None,
    ) -> None:
        """Store prompt-response pair in cache.

        Args:
            prompt: Original prompt
            response: Enhanced response
            model: Model used for enhancement
            embedding: Optional embedding for L2 cache (stored in Qdrant)
        """
        entry = CacheEntry(prompt=prompt, response=response, model=model)

        # L1: Store with exact hash
        prompt_hash = self._hash_prompt(prompt)

        # LRU eviction if needed
        if len(self.exact_cache) >= self.max_size:
            self.exact_cache.popitem(last=False)

        self.exact_cache[prompt_hash] = entry

        # L2: Store in Qdrant if embedding provided and Qdrant available
        if embedding is not None and self.qdrant_available and self.qdrant:
            self._store_in_qdrant(prompt_hash, embedding, entry)

        self.stats.total_entries = len(self.exact_cache)

    def _store_in_qdrant(
        self,
        point_id: str,
        embedding: list[float],
        entry: CacheEntry,
    ) -> None:
        """Store embedding and metadata in Qdrant."""
        if not self.qdrant:
            return

        try:
            self.qdrant.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    qdrant_models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "prompt_hash": point_id,
                            "prompt": entry.prompt,
                            "response": entry.response,
                            "model": entry.model,
                            "created_at": entry.created_at.isoformat(),
                            "hits": entry.hits,
                        },
                    )
                ],
            )
            logger.debug(f"Stored embedding in Qdrant for prompt hash {point_id}")
        except Exception as e:
            logger.warning(f"Failed to store in Qdrant: {e}")

    def clear(self) -> None:
        """Clear all cache entries (L1 and L2)."""
        self.exact_cache.clear()

        # Clear Qdrant collection if available
        if self.qdrant_available and self.qdrant and self.qdrant_url:
            try:
                self.qdrant.delete_collection(QDRANT_COLLECTION)
                self._init_qdrant(self.qdrant_url)
                logger.info("Qdrant L2 cache cleared")
            except Exception as e:
                logger.warning(f"Failed to clear Qdrant: {e}")

        self.stats = CacheStats()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """Get cache statistics including Qdrant info."""
        stats = self.stats.to_dict()
        stats["qdrant_available"] = self.qdrant_available

        if self.qdrant_available and self.qdrant:
            try:
                collection_info = self.qdrant.get_collection(QDRANT_COLLECTION)
                stats["l2_entries"] = collection_info.points_count
            except Exception:
                stats["l2_entries"] = 0
        else:
            stats["l2_entries"] = 0

        return stats
