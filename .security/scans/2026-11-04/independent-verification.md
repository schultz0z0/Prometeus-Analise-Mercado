# Verificação independente de segurança — 04/11/2026

Verificador: agente workflow_audit, diferente do descobridor. Método: leitura adversarial das provas isoladas, rastreio completo de origem/validações/sinks, inspeção das proteções do app e Compose. Nenhuma consulta ao stack ativo, nenhum arquivo .env real aberto, nenhuma produção sondada. Os scripts de prova anteriores foram inspecionados, não executados contra ambiente ativo.

## S1 — API sem autenticação/autorização: VERIFIED

Os três resultados são compatíveis com os caminhos reais:

- GET /v1/analyses usa apenas tenant_id informado pelo caller e Depends(get_db_session), sem principal autenticado (src/prometeus/entrypoints/rest/app.py:345–355). Resposta inclui course_name, proposta derivada e dossiê, quando presente (linhas417–432).
- POST /v1/analyses/{id}/decisions aceita user_id/user_role do corpo e grava modelo diretamente, após verificar apenas existência da análise (app.py:736–760). Nenhum vínculo entre identidade e role é validado. Prova isolada cria uma análise real em SQLite e usa HTTP ASGI sem Authorization:201, consistente com implementação.
- POST /v1/settings recebe corpo sem dependência de autenticação (app.py:1255–1257), permite alterar OPENAI_BASE_URL e orçamento (1299–1308) e chama _persist_env_updates (1320). A prova substitui somente AppSettings e destino da escrita por arquivo temporário:200 e persistência demonstram ausência de gate; não foi necessário acessar segredo real.

Tentativas de refutação: FastAPI não tem dependencies globais de segurança (app.py:95–100); middlewares existentes são correlation_id e headers (104–133), não autenticam. Não há reverse proxy autenticador entregue em compose.yaml; portas da API são publicadas sem bind localhost (compose.yaml:41–43), inclusive1455. Separação de rede do banco e deployment isolado por tenant não autentica o acesso à API. OAuth ChatGPT autentica fornecedor para inferência, não usuários do Prometeus.

**Condição obrigatória do impacto:** atacante precisa alcançar a porta/API. Firewall/VPN/proxy externo administrado fora do repositório pode reduzir alcance; não foi inspecionado. Não afirmar exposição pública da instalação concreta, vazamento de dados de tenants em bancos separados ou extração de chave efetivamente observada. Conclusão válida: qualquer caller com conectividade tem acesso de leitura e poderes administrativos sem autenticação no aplicativo entregue. Remediação deve cobrir principal autenticado, escopos/roles e autorização por tenant, além de proteger rota direta de bypass ao proxy.

## S2 — XSS persistente em diagnósticos: CORRECTED quanto à pré-condição; VERIFIED no sink

Origem: CreateAnalysisRequest.course_name é string sem escape/normalização HTML (app.py:166–183); criação canônica guarda course_name original (application/create_analysis.py:91) e list_analyses devolve row.course_name como name (app.py:419–420). Nome original não é substituído pelo entendimento do curso da LLM.

Sink confirmado: renderPortfolioView interpola course.name diretamente em HTML (web/js/views/portfolio-view.js:240), também area/level/modality sem escape nas linhas241–244. App.render atribui o template a root.innerHTML (web/js/app.js:49); a view é incluída em renderContent. escapeHtml está importado, mas não aplicado ao nome nessa tabela. A política do documento SPA permite script-src unsafe-inline (app.py:125–127), portanto não bloqueia o event handler. A política estrita da resposta JSON não protege execução no documento SPA. browser-xss-output.json registra Chromium executando onerror e marker1 no renderer real. Dossiê usa escapeHtml, o que protege aquela view específica, mas não o portfólio.

**Correção da alegação:** apenas inserir uma análise QUEUED na base NÃO demonstra execução automática no portfólio. loadCompletedAnalyses filtra status COMPLETED e dossier.status VERIFIED antes de popular state.courses (web/js/store.js:130–139); conclusão da análise atual também exige dossiê VERIFIED e scoring (365–388). O teste de navegador injeta um curso diretamente no estado do renderer e comprova o sink, não o pipeline pago inteiro.

**Pré-condição a declarar:** o nome controlado precisa alcançar um diagnóstico COMPLETED com dossiê VERIFIED, ou outro caminho confiável que alimente state.courses. Atacante pode submeter proposta com esse campo e material suficiente; a aceitação pelos gates até conclusão não foi homologada com os provedores reais. Portanto registrar XSS persistente condicionado a diagnóstico aceito/concluído; não afirmar PoC E2E completa de criação maliciosa até execução. Defesa recomendada (escapeHtml/textContent nos campos controlados e CSP sem unsafe-inline) corta o sink sem alterar cálculo/análise.

## Conciliação das evidências

security-probe-output.json comprova armazenamento/recuperação anônima do nome e mutações sem autorização em DB/config temporários; browser-xss-output.json comprova execução do renderer isolado. Juntas evidenciam caminhos conectáveis por código, com a pré-condição de conclusão explicitada acima. Não constituem exploração de produção nem execução integral de workflow com provedores reais.
