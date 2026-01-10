# ADR-001: Use FastAPI for Router Service

**Status:** Accepted
**Date:** 2026-01-06
**Deciders:** visualval

## Context

Need a framework for the MCP Router HTTP service. Options considered:
- FastAPI (Python)
- aiohttp (Python)
- Go (net/http or Gin)

## Decision

Use **FastAPI** for the router service.

## Consequences

### Positive
- Async-first design matches MCP's streaming needs
- Automatic OpenAPI docs for debugging
- Pydantic validation catches config errors early
- Large ecosystem for AI/ML integration
- Familiar Python syntax for rapid iteration

### Negative
- Python startup time slower than Go
- GIL limits true parallelism (mitigated by async)

### Neutral
- Requires Python 3.11+ for best performance

## Links

- Documented in: `REFACTOR_PLAN.md`
