# 1. Use the official Python 3.12 slim image
FROM ghcr.io/astral-sh/uv:0.8.4-python3.12-bookworm

SHELL ["/bin/bash", "-c"]
# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Upgrade system packages to address vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 5. Create a non-root user
RUN addgroup --system app && adduser --system --group app

# 6. Create a directory for the app
WORKDIR /app


COPY ./src ./src
COPY pyproject.toml .
COPY ./envs/.env .
COPY prefect.yaml .
COPY prefect.toml .
COPY profiles.toml .

RUN uv venv && \
    . /app/.venv/bin/activate && \
    uv sync --no-dev


# 9. Switch to the non-root user
USER app