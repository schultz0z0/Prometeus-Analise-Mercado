# Prometeus — arquitetura e fronteiras de confiança

Data: 04/11/2026. Escopo: fonte atual e provas locais isoladas, sem testar produção ou usar credenciais reais.

Aplicação Python/FastAPI com frontend SPA JavaScript, PostgreSQL, Celery/Redis e adaptadores de IA/Apify. O serviço executa um workflow de pesquisa e análise de viabilidade de cursos para ENS. A arquitetura canônica é monólito modular com deployment, banco, segredos e volumes separados por instituição (ADR-0002). Não se presume multi-tenancy compartilhado como modelo de produção. O baseline relevante é uma aplicação administrativa interna com API máquina a máquina; usuários da rede e páginas externas não devem receber implicitamente acesso administrativo.

## Fluxo e ativos

Usuário/chatbot -> REST/MCP -> aplicação -> banco/fila -> worker -> histórico institucional, LLM/JEV e Apify -> qualificação e scoring determinísticos -> verificação de dossiê -> persistência e entrega. Os ativos sensíveis são propostas, evidências e decisões institucionais, histórico, credenciais de provedores e orçamento de pesquisa.

## Superfícies verificadas

- `src/prometeus/entrypoints/rest/app.py`: criação, listagem, detalhes, reanálise, cancelamento, dossiê, registro de decisão humana e outcomes, importação de documentos, configuração de provedores, OAuth e radar setorial.
- `src/prometeus/entrypoints/mcp/server.py`: ferramentas de criação, consulta, decisão e outcome; servidor não está publicado por rota REST no entrypoint inspecionado. Problemas funcionais/transporte pertencem à auditoria de fluxo.
- `web/js/app.js` e `web/js/views/portfolio-view.js`: respostas REST são usadas para renderização via `innerHTML`.
- `src/prometeus/infrastructure/llm/client.py`: base URL configurável recebe o cabeçalho Bearer e prompts; uma mudança administrativa exige autorização.
- `src/prometeus/infrastructure/llm/codex_oauth.py`: PKCE, nonce/state, JWKS e persistência de tokens; arquivo local ignorado pelo Git em `/var`.
- `src/prometeus/infrastructure/webhooks/dispatcher.py`: HMAC-SHA256 no envio; URL vem do chamador do dispatcher e não foi estabelecida uma cadeia de entrada não confiável até envio em produção.
- `src/prometeus/application/collect_market_evidence.py`: rejeita endereços literais não globais, sufixos internos, userinfo e URLs inválidas antes de crawlers externos.
- `compose.yaml`: API publicada em `${API_PORT:-8000}:8000` e `1455:8000`, sem restrição ao endereço de loopback e sem proxy de autenticação no arquivo entregue. PostgreSQL e Redis ficam em rede interna. O firewall/proxy real não foi testado.

## Controles e lacunas

REST não possui dependência global de autenticação nem validação de escopo por rota; `SERVICE_API_KEYS` está somente declarado em configuração. Os middlewares tratam headers de segurança e correlação. Filtragem por tenant enviada no próprio request não substitui principal autenticado. O schema aceita `user_id` e `user_role` do próprio solicitante para registrar decisões. A ausência de autenticação e autorização é demonstrada com chamadas ASGI sem cabeçalho Authorization.

A SPA possui escape e validação de links nos componentes de dossiê, live e settings. O portfólio, porém, insere nome, área, nível e modalidade sem escape. O conteúdo bruto sobrevive à persistência e à resposta de listagem. A política CSP permite handlers inline na SPA. A execução do handler foi demonstrada num Chromium isolado sobre o renderer real; a prova HTTP de armazenamento/recuperação foi separada em banco em memória.

## Limites

Não houve pentest em produção, consulta a segredos, gasto em fornecedores nem mutação dos containers em execução. Dependências não foram auditadas por advisory/CVE nesta subauditoria. SSRF por DNS/redirect, zip bomb de DOCX e falhas de autenticação OAuth adicionais não foram confirmadas e não são achados. Não há atribuição de garantia de ausência de outras vulnerabilidades.
