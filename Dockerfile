# Build stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Run tests and build package
RUN python -m pytest
RUN pip install --no-cache-dir .

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Copy built package from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/automcp /usr/local/bin/automcp

# Create non-root user
RUN useradd -m -u 1000 automcp
USER automcp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AUTOMCP_CONFIG_DIR=/etc/automcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "automcp.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
