# Lynjax — one image, one process, one port.
#
# NetVault shipped two containers with nginx proxying to the backend, which
# meant a second image to build, a proxy config to keep in sync and CORS between
# two origins. The frontend is compiled here and copied into the Python package,
# so FastAPI serves it directly and there is nothing to proxy.

# ─── Stage 1: compile the frontend ───
FROM node:22-alpine AS web

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ─── Stage 2: the runtime image ───
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="Lynjax"
LABEL org.opencontainers.image.description="Network visibility, audit and traceability"
LABEL org.opencontainers.image.source="https://github.com/Nstalej/lynjax"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LYNJAX_HOST=0.0.0.0 \
    LYNJAX_PORT=8080 \
    LYNJAX_DATA_DIR=/data \
    LYNJAX_LOG_DIR=/data/logs

# iputils-ping and openssh-client are here for operator troubleshooting from
# inside the container; the connectors themselves use pure-Python transports.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        iputils-ping \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/lynjax ./lynjax

# The compiled bundle lands inside the package, so `lynjax serve` finds it the
# same way an installed wheel would.
COPY --from=web /build/dist ./lynjax/web

RUN pip install --no-cache-dir .

# Run as a non-root user. The data directory is a volume, so it is chowned
# rather than baked into the image layer.
RUN useradd --create-home --uid 10001 lynjax \
    && mkdir -p /data \
    && chown -R lynjax:lynjax /data
USER lynjax

VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

# Real network access stays off unless the operator sets
# LYNJAX_NETWORK_POLICY=authorized-targets, the same as every other entry point.
CMD ["lynjax", "serve"]
