FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files (README.md required by pyproject.toml for hatchling build)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# Install Node.js MCP server packages (STDIO-based)
# These are spawned as subprocesses by router/adapters/stdio.py
COPY package.json ./
RUN npm install --production

# Copy application code
COPY router/ ./router/

# Copy configs (these can be overridden via volume mount)
COPY configs/ ./configs/

# Copy templates for dashboard
COPY templates/ ./templates/

# Expose port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run the application
CMD ["uvicorn", "router.main:app", "--host", "0.0.0.0", "--port", "9090"]
