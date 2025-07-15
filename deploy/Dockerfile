FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /slm

# Install system dependencies for SLM (PostGIS, GDAL, XML processing)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql-client \
    gdal-bin libgdal-dev \
    libxml2-dev libxslt1-dev \
    curl \
    && pip install --upgrade pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for esbuild
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g esbuild@latest \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy dependency files and source for building
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Install Python dependencies and build/install the package
RUN uv sync --frozen --extra gunicorn && uv pip install --no-deps . && rm -rf src/

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
