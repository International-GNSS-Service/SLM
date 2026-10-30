# Base and helper images are pinned by digest so a build cannot be changed out
# from under us by a tag being moved. Bump the tag and its digest together.
FROM python:3.11-slim@sha256:673719e071ecf27434fd2635bbd8d00f49f4fdd81f243143438a42ced8bedf60

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /slm

# Install system dependencies for SLM (PostGIS, GDAL, XML processing)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql-client \
    gdal-bin libgdal-dev \
    libxml2-dev libxslt1-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Node.js and npm are needed at runtime: asset compression runs esbuild through
# npx (see COMPRESS_PRECOMPILERS in slm.settings.assets, which pins the esbuild
# version). Copy them from the official node image instead of piping the
# nodesource installer into bash.
COPY --from=node:22-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da \
    /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da \
    /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Install uv from its official image rather than through an unpinned pip install
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 \
    /uv /uvx /usr/local/bin/

# Copy dependency files and source for building
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Install Python dependencies and build/install the package as a regular (non
# editable) install so the source tree can be removed afterwards.
RUN uv sync --frozen --no-editable --extra gunicorn && rm -rf src/

# The environment is complete; stop `uv run` from re-syncing it on every
# invocation, which would try to rebuild the package from the removed source.
ENV UV_NO_SYNC=1

# Create non-root user for security
RUN adduser --disabled-password --gecos '' slm && \
    chown -R slm:slm /slm
USER slm

# Package is now properly installed - source code removed for security

# Create directories for static and media files
RUN mkdir -p static media

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Run Gunicorn as WSGI server
CMD ["uv", "run", "gunicorn", "slm.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
