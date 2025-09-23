FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies including examples (for lionagi)
RUN uv sync --extra examples

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

# Default command
CMD ["uv", "run", "khivemcp", "examples/config/search_group_config.json", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]