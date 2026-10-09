# Deployment em VPS com Docker

## Modelo escolhido

Cada instituição recebe uma stack isolada e um arquivo de configuração próprio. O código e as imagens são os mesmos.

```text
VPS
└── institution-ens/
    ├── reverse-proxy
    ├── api
    ├── mcp
    ├── worker
    ├── scheduler
    ├── postgres
    ├── redis
    └── evidence-volume
```

## Requisitos mínimos de produção

- Linux com Docker Engine e Compose.
- TLS no reverse proxy.
- Firewall permitindo somente portas necessárias.
- Volumes persistentes para PostgreSQL e evidências.
- Backups enviados para destino separado da VPS.
- Segredos fornecidos fora da imagem e do Git.
- Health checks, limites de memória e restart policies.
- Usuários de container sem privilégios sempre que possível.

## Ambientes

- `local`: mocks e dados sintéticos.
- `staging-ens`: credenciais e dados controlados da ENS.
- `production-ens`: deployment aprovado, isolado e auditado.

## Capacidade inicial

Uma equipe de dois desenvolvedores operará o produto. Por isso, Kubernetes, service mesh e microserviços independentes ficam fora da primeira versão. Escala vertical, workers concorrentes e filas por prioridade devem ser medidos antes de qualquer decomposição.

## SLOs iniciais propostos

- Aceite de job: P95 < 1 s.
- Disponibilidade mensal da API: 99,5% durante o piloto.
- Entrega de webhook: 99% em até 15 minutos após conclusão.
- RPO: 24 h no piloto; objetivo de 1 h após estabilização.
- RTO: 8 h no piloto; objetivo de 2 h após estabilização.

SLOs devem ser confirmados com a ENS antes do go-live.
