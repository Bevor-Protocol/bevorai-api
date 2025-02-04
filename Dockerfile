FROM python:3.11-slim

ARG PORT=8000

WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.5

# RUN apt-get update && apt-get install -y \
#     curl gnupg \
#     && rm -rf /var/lib/apt/lists/*

# # Install Doppler CLI
# RUN curl -Lf --silent "https://cli.doppler.com/install.sh" | sh

# ENV DOPPLER_TOKEN ${DOPPLER_TOKEN}
# ENV DOPPLER_PROJECT ${DOPPLER_PROJECT}
# ENV DOPPLER_ENVIRONMENT ${DOPPLER_ENVIRONMENT}
# ENV DOPPLER_CONFIG ${DOPPLER_CONFIG}

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy application code
COPY app ./app

# Expose port
EXPOSE ${PORT}
# Echo port for debugging
RUN echo "Port is set to: ${PORT}"
