"""Circuit breaker pattern for MCP server fault tolerance.

The circuit breaker prevents cascading failures by:
1. CLOSED: Normal operation, requests flow through
2. OPEN: Too many failures, requests rejected immediately
3. HALF_OPEN: Testing recovery, allowing one request through
"""

from datetime import datetime, timedelta
from enum import Enum


class State(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Per-server circuit breaker for fault tolerance."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
    ):
        """Initialize circuit breaker.

        Args:
            name: Server identifier
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self.name = name
        self.state = State.CLOSED
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.last_failure: datetime | None = None
        self.last_success: datetime | None = None

    def record_success(self) -> None:
        """Record a successful request."""
        self.failures = 0
        self.state = State.CLOSED
        self.last_success = datetime.now()

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failures += 1
        self.last_failure = datetime.now()

        if self.failures >= self.failure_threshold:
            self.state = State.OPEN

    def can_execute(self) -> bool:
        """Check if requests can be executed.

        Returns:
            True if request should proceed, False if circuit is open
        """
        if self.state == State.CLOSED:
            return True

        if self.state == State.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure and datetime.now() - self.last_failure > self.recovery_timeout:
                self.state = State.HALF_OPEN
                return True
            return False

        # HALF_OPEN: allow one request to test recovery
        return True

    def status(self) -> dict:
        """Get current circuit breaker status.

        Returns:
            Dictionary with state, failures, and timing info
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failures = 0
        self.state = State.CLOSED
        self.last_failure = None


class CircuitBreakerRegistry:
    """Registry of per-server circuit breakers."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
    ):
        """Initialize registry with default settings.

        Args:
            failure_threshold: Default failures before opening
            recovery_timeout: Default seconds before recovery attempt
        """
        self.breakers: dict[str, CircuitBreaker] = {}
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def get(self, server: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a server.

        Args:
            server: Server name

        Returns:
            CircuitBreaker instance for the server
        """
        if server not in self.breakers:
            self.breakers[server] = CircuitBreaker(
                name=server,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
            )
        return self.breakers[server]

    def all_status(self) -> list[dict]:
        """Get status of all circuit breakers.

        Returns:
            List of status dictionaries
        """
        return [b.status() for b in self.breakers.values()]

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()

    def reset(self, server: str) -> bool:
        """Reset a specific circuit breaker.

        Args:
            server: Server name

        Returns:
            True if breaker existed and was reset
        """
        if server in self.breakers:
            self.breakers[server].reset()
            return True
        return False
