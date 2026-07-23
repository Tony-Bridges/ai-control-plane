# AI Control Plane with Envoy Gateway

Enterprise AI gateway that fronts LLM traffic with an Envoy proxy, classifies
and detects PII (with South-Africa-specific detectors for ID numbers, phone
numbers, company registrations, bank accounts, SARS references and medical
aid numbers), enforces OPA-based policy decisions, routes requests to the
appropriate upstream model, and writes a full audit trail.

## Architecture

```
Client -> Envoy Gateway (rate limiting, ext_authz/OPA) -> Control Plane (FastAPI)
                                                              |
                             +--------------------------------+--------------------------------+
                             |                |                |                |               |
                      Classification      Policy Engine     Routing Engine   Anonymizer      Audit Logger
                      (Presidio + SA        (OPA)            (OpenAI/Azure/    (mask/          (Postgres/
                       detectors)                             Anthropic/Local) anonymize)       ClickHouse)
```

## Project Structure

See the full tree in the repository; key directories:

- `src/` — FastAPI control plane application (API, detectors, policy, routing, transformers, audit, utils)
- `envoy/` — Envoy gateway configuration (rate limiting, ext_authz, routing)
- `config/` — Environment configs and OPA Rego policies
- `docker/` — Dockerfiles and docker-compose stack
- `k8s/` — Kubernetes manifests (Deployments, Services, HPA, Ingress)
- `scripts/` — Deployment, migration, and load-testing scripts
- `tests/` — Unit and integration tests

## Quick Start (Docker Compose)

```bash
make build
make up
```

This starts Envoy (`:8080`), the control plane (`:8000`), OPA (`:8181`),
Redis, Postgres, ClickHouse, Prometheus (`:9090`), and Grafana (`:3000`).

## Quick Start (Kubernetes)

```bash
export OPENAI_API_KEY=...
export AZURE_OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
make deploy
```

## Development

```bash
make install   # install deps + spaCy model
make dev       # run the control plane locally with reload
make test      # run the test suite
make lint      # flake8 + black --check + isort --check-only
make format    # black + isort
```

## Sending a Request

```bash
curl -X POST http://localhost:8080/v1/ai/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u123",
    "department": "hr",
    "prompt": "Please update employee ID 8001015009087 leave balance."
  }'
```

## Notes

This is a reference implementation intended as a starting point. Several
components (transformer-based NER, ClickHouse/Elasticsearch audit sinks,
`k8s/opa`, `k8s/redis`, `k8s/postgres` manifests, `seed_policies.py`) are
stubbed or referenced but not fully built out, and should be completed to
match your production requirements before deploying with real traffic or
secrets.
