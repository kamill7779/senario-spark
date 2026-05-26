FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OUTPUT_ROOT=/app/outputs

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app appuser

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY pipelines ./pipelines
COPY prompts ./prompts
COPY schemas ./schemas
COPY scripts ./scripts

RUN mkdir -p /app/outputs \
    && chown -R appuser:appuser /app

USER appuser

# Equivalent shell form: python -m scripts.docker_entrypoint
ENTRYPOINT ["python", "-m", "scripts.docker_entrypoint"]
