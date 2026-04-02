FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=codex-collaboration-coordinator \
    DEPLOYMENT_PROFILE=small-team \
    APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_RELOAD=false \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:///./data/codex_coordinator.db \
    CODEX_BRIDGE_MODE=local \
    RUNTIME_RECOVERY_ENABLED=true \
    RUNTIME_RECOVERY_INTERVAL_SECONDS=15 \
    RUNTIME_STALE_AFTER_MINUTES=10 \
    REQUEST_ID_HEADER=X-Request-ID

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY docs ./docs
COPY scripts ./scripts

RUN pip install .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/readinessz', timeout=4)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
