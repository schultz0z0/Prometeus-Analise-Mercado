# Changelog

## Não lançado — runtime factual em tempo real (2026-10-27)

- substituído o fluxo demonstrativo por um workflow real de 15 etapas com preflight, checkpoints, `tool_runs` e bloqueio explícito;
- integrada coleta Apify real para busca, crawling, Meta Ads Library, LinkedIn, LinkedIn Jobs e redes sociais, com Actors/builds pinados, orçamento e proveniência;
- removidos fallbacks, scores, dossiês e tokens OAuth fabricados do runtime e da interface;
- implementado modo tradicional completo sem JEV e preservado o modo híbrido opcional;
- implementado Sign in with ChatGPT para aplicações locais/open source, incluindo PKCE, state, nonce, validação de ID token e escopo, catálogo real de modelos, prova de inferência, armazenamento protegido e refresh rotativo;
- corrigida persistência de configurações de ambiente (.env) para suportar containers Docker com bind mounts e usuários não-root, eliminando falhas de permissão no callback ChatGPT OAuth e nos ajustes da API;
- mantida como única fonte sintética autorizada a base histórica da ENS, claramente identificada e restrita à comparação;
- dossiê passou a exigir evidência persistida, scoring determinístico e verificação de claims antes da entrega.

