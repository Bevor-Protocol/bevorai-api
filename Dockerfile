FROM python:3.11-slim

ARG PORT=8000

WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.5

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

RUN npx @redocly/cli build-docs openapi.yaml

# Copy application code
COPY app ./app
COPY scripts ./scripts

# Make pre-deploy script executable
RUN chmod +x scripts/pre-deploy.sh

# Expose port
EXPOSE ${PORT}
# Echo port for debugging
RUN echo "Port is set to: ${PORT}"
