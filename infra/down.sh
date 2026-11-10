#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

for file in pods/app.yaml pods/pipeline.yaml pods/infra.yaml; do
    podman kube down "$file" >/dev/null 2>&1 || true
done

echo "Stack stopped. The postgres data and Spark checkpoints were kept."
