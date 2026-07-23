#!/bin/bash
# Bootstraps a local Envoy instance for development, without the full
# docker-compose stack (useful for iterating on envoy.yaml).
set -e

ENVOY_VERSION="v1.28-latest"
CONFIG_PATH="$(dirname "$0")/../envoy/envoy.yaml"

echo "Validating Envoy config: ${CONFIG_PATH}"
docker run --rm -v "$(cd "$(dirname "${CONFIG_PATH}")" && pwd)":/etc/envoy \
    envoyproxy/envoy:${ENVOY_VERSION} \
    --mode validate -c /etc/envoy/envoy.yaml

echo "Starting Envoy on :8080 (admin on :9901)"
docker run --rm -it \
    -p 8080:8080 -p 9901:9901 \
    -v "$(cd "$(dirname "${CONFIG_PATH}")" && pwd)":/etc/envoy \
    envoyproxy/envoy:${ENVOY_VERSION} \
    -c /etc/envoy/envoy.yaml --log-level info
