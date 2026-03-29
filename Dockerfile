# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Install Rich from the local source (so the service uses our fork's version)
COPY rich/ /build/rich/
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --prefix=/install --no-deps .

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Rich Render Service" \
      org.opencontainers.image.description="MGL842 TP2 — HTTP wrapper around the Rich Python library" \
      org.opencontainers.image.source="https://github.com/michelzzw/rich"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY service/app.py .

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000

# Liveness check: hits the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
