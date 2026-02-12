# ============================================================================
# Kimi K2.5 Agent Swarm - Production Dockerfile
# Multi-stage build for security and optimization
# ============================================================================

# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r kimi && useradd -r -g kimi kimi

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /home/kimi/.local

# Copy application code
COPY --chown=kimi:kimi server/ ./server/
COPY --chown=kimi:kimi database/ ./database/
COPY --chown=kimi:kimi config/ ./config/

# Set environment
ENV PATH=/home/kimi/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/server

# Security: Run as non-root
USER kimi

# Security: Read-only filesystem for app code (data dirs are volume-mounted)
# Note: Writable dirs should be mounted as volumes

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run FastAPI server
CMD ["python", "-m", "uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
