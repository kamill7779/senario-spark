# SenarioSpark

SenarioSpark is a short-drama interaction project. The repo is organized as a monorepo so the mobile client, Go backend services, Python AI understanding service, shared contracts, and deployment assets can evolve together during the MVP stage.

## Repository Layout

```text
frontend/
  mobile-app/                 Mobile client.

backend/
  services/                   Go microservices, to be defined as boundaries settle.
  pkg/                        Shared Go packages used by backend services only.

ai-services/
  understanding-service/      Python service for video understanding outputs.

contracts/
  openapi/                    HTTP API contracts.
  protobuf/                   RPC/event contracts.
  schemas/                    Shared JSON schemas for scripts, segments, highlights, and frontend manifests.

deploy/
  docker/                     Docker assets.
  k8s/                        Kubernetes manifests.
  local/                      Local development orchestration.

docs/
  architecture/               Architecture notes and diagrams.
  adr/                        Architecture decision records.

scripts/                      Developer automation scripts.
tools/                        Local tooling and one-off utilities.
```

## Current Boundary

This initial structure only defines ownership boundaries. It does not choose the final mobile framework, Go web framework, message queue, database, vector database, or deployment platform yet.
