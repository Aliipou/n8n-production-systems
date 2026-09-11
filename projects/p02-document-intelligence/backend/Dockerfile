# python 3.12.14-slim-bookworm looked up 2026-09-11 from Docker Hub / official-images.
FROM python:3.12.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    P02_VAT_RATES=/app/config/vat_rates.yaml \
    P02_DECISION=/app/config/decision.yaml \
    P02_STORAGE_DIR=/data/documents

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --home-dir /home/app app \
    && mkdir -p /data/documents \
    && chown app:app /data/documents

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY config /app/config

RUN pip install --no-cache-dir . \
    && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"

CMD ["uvicorn", "p02_doc_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
