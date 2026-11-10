#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v podman >/dev/null 2>&1; then
    echo "podman is required" >&2
    exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
    echo "envsubst is required (install gettext)" >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Missing infra/.env (see infra/.env.example)" >&2
    exit 1
fi

if podman pod exists waw-transit-deps; then
    echo "waw-transit-deps is running. Stop it first: podman kube down pods/dependencies.yaml" >&2
    exit 1
fi

set -a
. ./.env
set +a

: "${FETCH_INTERVAL_SECONDS:=15}"
: "${TIMEZONE:=Europe/Warsaw}"
: "${PROCESSING_STATS_ENABLED:=false}"
: "${REDIS_DB:=0}"
: "${KAFKA_CLIENT_ID:=warsaw-transit}"
: "${KAFKA_TOPIC_BUSES:=warsaw_transit_buses_raw}"
: "${KAFKA_TOPIC_TRAMS:=warsaw_transit_trams_raw}"
: "${KAFKA_TOPIC_GTFS_VERSION:=warsaw_transit_gtfs_versions}"
: "${KAFKA_STARTING_OFFSETS:=latest}"

vars=(
    DB_NAME DB_USER DB_PASSWORD
    REDIS_PASSWORD REDIS_DB CLUSTER_ID
    WARSAW_API_TOKEN FETCH_INTERVAL_SECONDS TIMEZONE
    PROCESSING_STATS_ENABLED
    KAFKA_CLIENT_ID KAFKA_TOPIC_BUSES KAFKA_TOPIC_TRAMS
    KAFKA_TOPIC_GTFS_VERSION KAFKA_STARTING_OFFSETS
)

for name in "${vars[@]}"; do
    if [[ -z "${!name:-}" ]]; then
        echo "Environment variable $name is not set in infra/.env" >&2
        exit 1
    fi
done

subst=""
for name in "${vars[@]}"; do
    subst+="\${$name} "
done

echo "Building images..."
podman build -f images/pipeline.Dockerfile -t localhost/waw-transit-pipeline:latest ..
podman build -f images/backend.Dockerfile -t localhost/waw-transit-backend:latest ..
podman build -f images/web.Dockerfile -t localhost/waw-transit-web:latest ..

podman network exists waw-pipeline || podman network create waw-pipeline
podman network exists waw-api || podman network create waw-api

echo "Stopping the previous stack..."
for file in pods/app.yaml pods/pipeline.yaml pods/infra.yaml; do
    podman kube down "$file" >/dev/null 2>&1 || true
done

wait_for() {
    local description=$1
    shift
    local attempts=${WAIT_ATTEMPTS:-60}
    for ((attempt = 1; attempt <= attempts; attempt++)); do
        if "$@" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo "Timed out waiting for $description" >&2
    return 1
}

echo "Starting shared infrastructure..."
envsubst "$subst" < pods/infra.yaml \
    | podman kube play --network waw-pipeline --network waw-api -

wait_for "PostgreSQL" \
    podman exec waw-transit-infra-postgres pg_isready -U "$DB_USER" -d "$DB_NAME"
wait_for "Redis" \
    podman exec -e REDISCLI_AUTH="$REDIS_PASSWORD" waw-transit-infra-redis redis-cli ping

echo "Starting Kafka and the pipeline..."
envsubst "$subst" < pods/pipeline.yaml \
    | podman kube play --network waw-pipeline -

wait_for "Kafka" \
    podman exec waw-transit-pipeline-kafka \
        kafka-topics --bootstrap-server 127.0.0.1:9092 --list

echo "Starting the backend and web..."
envsubst "$subst" < pods/app.yaml \
    | podman kube play --network waw-api -

cat <<'EOF'

Full stack started. The first GTFS load can take a few minutes.

  Frontend  http://localhost:8080
  Logs      podman logs -f waw-transit-pipeline-pipeline
  Stop      ./down.sh

EOF
