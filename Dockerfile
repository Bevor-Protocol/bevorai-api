# based on python3.13-alpine, pre-built with uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine

ARG PORT=8000

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy poetry files
COPY pyproject.toml uv.lock ./

ADD . /app
# Use the same cache key source for consistency
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app ./app
COPY scripts ./scripts

# Make pre-deploy script executable
RUN chmod +x scripts/pre-deploy.sh

# Expose port
EXPOSE ${PORT}
# Echo port for debugging
RUN echo "Port is set to: ${PORT}"
