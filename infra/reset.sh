#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

for file in pods/app.yaml pods/pipeline.yaml pods/infra.yaml pods/dependencies.yaml; do
    podman kube down "$file" >/dev/null 2>&1 || true
done

for volume in waw-transit-postgres-data waw-transit-kafka-data waw-transit-checkpoints; do
    if podman volume exists "$volume"; then
        podman volume rm "$volume" >/dev/null
        echo "Removed $volume"
    fi
done

echo "All project volumes removed."
