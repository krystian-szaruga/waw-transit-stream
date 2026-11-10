FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY waw_transit/requirements.txt waw_transit/requirements.txt
COPY waw_transit_backend/requirements.txt waw_transit_backend/requirements.txt

RUN pip install --no-cache-dir \
        -r waw_transit/requirements.txt \
        -r waw_transit_backend/requirements.txt

COPY waw_transit waw_transit
COPY waw_transit_backend waw_transit_backend

RUN pip install --no-cache-dir ./waw_transit ./waw_transit_backend \
    && useradd --system --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "-m", "waw_transit_backend.main"]
