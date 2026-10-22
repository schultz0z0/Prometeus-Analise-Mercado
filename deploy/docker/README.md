# Docker e Infraestrutura de Deployment

Este diretório contém os artefatos de containerização de produção do **Prometeus**:

- [`Dockerfile`](Dockerfile): Imagem multi-stage endurecida com usuário não-root `prometeus` (UID 10001), separação estrita de build tools e healthcheck nativo.
- [`docker-entrypoint.sh`](docker-entrypoint.sh): Ponto de entrada com automigração condicional via Alembic (`AUTO_MIGRATE=true`).
- [`../../compose.yaml`](../../compose.yaml): Orquestração local, staging e piloto com isolamento de rede interna (`prometeus_internal`), Redis 7 e PostgreSQL 16.
- [Guia de Implantação e Operação](../../docs/operations/staging-and-pilot-deployment.md): Passo a passo detalhado para staging, shadow mode e piloto com a ENS.
