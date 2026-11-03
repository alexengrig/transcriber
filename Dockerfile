# syntax=docker/dockerfile:1
# CUDA runtime libraries come from pip wheels (torch / nvidia-*), so a plain
# Python image is enough; the GPU is provided by the NVIDIA container runtime.
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
# Which engines to bake into the image: space-separated list of extras.
ARG ENGINES="whisper gigaam"
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable $(for e in $ENGINES; do printf -- '--extra %s ' "$e"; done)

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /work
ENTRYPOINT ["transcriber"]
CMD ["--help"]
