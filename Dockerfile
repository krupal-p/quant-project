FROM prefecthq/prefect:3.4.11-python3.12

# Install uv and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for ADBC PostgreSQL
ENV ADBC_POSTGRESQL_LIBRARY=/usr/lib/x86_64-linux-gnu/libpq.so.5

# Copy the project into the image
COPY . /app

# Set working directory
WORKDIR /app

# Create virtual environment and install dependencies
RUN uv venv
RUN uv sync --no-dev

# Set environment to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"