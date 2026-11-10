FROM eclipse-temurin:25-jdk AS java

FROM python:3.13-slim-bookworm

COPY --from=java /opt/java/openjdk /opt/java/openjdk

ENV JAVA_HOME=/opt/java/openjdk \
    PATH="/opt/java/openjdk/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY waw_transit/requirements.txt waw_transit/requirements.txt
COPY waw_transit_pipeline/requirements.txt waw_transit_pipeline/requirements.txt

RUN pip install --no-cache-dir \
        -r waw_transit/requirements.txt \
        -r waw_transit_pipeline/requirements.txt

COPY waw_transit waw_transit
COPY waw_transit_pipeline waw_transit_pipeline

RUN pip install --no-cache-dir ./waw_transit ./waw_transit_pipeline \
    && useradd --system --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

RUN python -c "from pyspark.sql import SparkSession; from waw_transit_pipeline.adapters.spark import required_packages; s = SparkSession.builder.master('local[1]').config('spark.jars.packages', ','.join(required_packages)).config('spark.ui.enabled', 'false').getOrCreate(); s.stop()"

CMD ["python", "-m", "waw_transit_pipeline.main"]
