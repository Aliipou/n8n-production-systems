# Pin matches platform/services/mock-llm. VERSIONS.md lists CPython 3.12.14 as
# a source-only security release. TODO(verify): Docker Hub python:3.12.x-slim
# patch tag when a 3.12.14 image exists.
FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --home-dir /home/app \
       --shell /usr/sbin/nologin app

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY templates /app/templates

RUN pip install --no-cache-dir . \
    && chown -R app:app /app

USER app

EXPOSE 8092

HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8092/health', timeout=4)"

CMD ["uvicorn", "review_ui.app:app", "--host", "0.0.0.0", "--port", "8092"]
