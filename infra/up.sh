#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v envsubst >/dev/null 2>&1; then
    echo "envsubst is required (install gettext)" >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Missing infra/.env (see infra/.env.example)" >&2
    exit 1
fi

set -a
. ./.env
set +a

vars=(
    DB_NAME DB_USER DB_PASSWORD
    REDIS_PORT REDIS_PASSWORD
    KAFKA_NODE_ID KAFKA_PROCESS_ROLES KAFKA_CONTROLLER_QUORUM_VOTERS
    KAFKA_LISTENERS KAFKA_ADVERTISED_LISTENERS
    KAFKA_LISTENER_SECURITY_PROTOCOL_MAP KAFKA_INTER_BROKER_LISTENER_NAME
    KAFKA_CONTROLLER_LISTENER_NAMES KAFKA_LOG_DIRS CLUSTER_ID
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
    KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
    KAFKA_TRANSACTION_STATE_LOG_MIN_ISR
    KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS
    KAFKA_AUTO_CREATE_TOPICS_ENABLE KAFKA_NUM_PARTITIONS
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

envsubst "$subst" < infrastructure.yaml | podman kube play - "$@"
