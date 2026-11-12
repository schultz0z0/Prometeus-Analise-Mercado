# Contratos planejados: Codex CLI e Scrapling

**Versão de projeto:** 1, 12/11/2026. **Estado:** especificação para CS-01–CS-05, não endpoints ou configurações já disponíveis. Ver [ADR-0012](../architecture/adr/0012-codex-cli-and-provider-neutral-collection.md).

## Vocabulário e identidade

`capability` descreve a operação lógica, como `google_search` ou `web_crawler`. `provider` identifica Apify ou Scrapling. A identidade semântica da tarefa usa análise, capability, consulta/URL canônica, localidade e escopo; tentativa e provider são registros de execução dessa tarefa. Trocar o provider não cria novo orçamento de tentativas. Versões de provider/normalizador alteram compatibilidade de cache, não apagam tentativas anteriores.

Cada operação inclui contexto de autorização imposto pelo servidor: instituição, análise, etapa, proprietário do lease e permissões. Argumentos fornecidos pelo modelo não podem trocar esse contexto. Artefatos usam IDs opacos, jamais caminhos arbitrários escolhidos pelo agente.

## Resultado de aquisição

Contrato mínimo proposto para `domain/collection_results.py`:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True)
class CollectionResult:
    operation_id: str
    task_id: str
    attempt_id: str
    capability: str
    provider: Literal["apify", "scrapling"]
    provider_version: str
    status: Literal["SUCCEEDED", "PARTIAL", "EMPTY", "FAILED", "IN_DOUBT"]
    artifact_ids: tuple[str, ...]
    observed_cost_usd: Decimal | None
    cost_status: Literal["pending", "observed_provisional", "not_billed_by_provider"]
    remote_run_id: str | None = None
    remote_dataset_id: str | None = None
```

O exemplo define a fronteira, não substitui validação Pydantic/código. Obrigatório rejeitar custo negativo/não finito, ID sem proprietário e combinações inválidas de provider e identidade. Custo local de CPU/RAM/proxy é telemetria separada; `not_billed_by_provider` não implica execução sem custo.

Para Apify: Actor/build, run, dataset, contagem remota e paginação continuam registrados. Para Scrapling: versão da biblioteca/browser, modo HTTP/browser, operação local e desfecho por URL. Retomada do browser usa novo processo quando necessário, com estado compatível permitido; um objeto de sessão em memória não é checkpoint durável.

## Arquivo de evidências

Cada artefato registra:

- IDs de proprietário, tarefa, tentativa e provider; horários UTC e versões.
- URL pedida/final e proveniência da descoberta; status HTTP/desfecho por URL.
- Conteúdo original disponível, conteúdo higienizado, tipo MIME, charset e hashes de ambos; `sanitization_changed` e motivos.
- Contagens de registros, paginação/cursores, origem da contagem e condição que demonstra término.
- Campos/bytes não capturados e motivo: tamanho, falha de rede, formato binário, documento não baixado, conteúdo dinâmico inacessível ou interrupção.
- Manifesto de partes analisadas e referências por registro/campo/trecho; admissão factual separada da leitura.

Completude é relativa ao escopo adquirido: não significa todo o site ou toda a internet. No provider local, fim de paginação, fila de URLs e documentos pertinentes deve ser demonstrado; não reutilizar falsamente `provider_pagination` da Apify. Preservar a compatibilidade de `dataset_archive` v1 por adaptador de leitura, sem reescrever arquivos de análises antigas. Hash de artefato não muda para aparentar nova versão.

O histórico de rede do browser não substitui essa retenção. A documentação Scrapling descreve corpos não capturados e limites; HTML renderizado, documento e respostas de rede são artefatos distintos. [Limites do MCP](https://scrapling.readthedocs.io/en/latest/ai/mcp-server.html#network-history).

## Porta de execução e recuperação

Substituir dependência de classe concreta por interface que declare `execute`, `inspect` e `resume`/reconciliação, com callback de operação iniciada persistido antes de aguardar resultado. `inspect` nunca inicia compra. `resume` recebe ID explícito autorizado; se não houver identidade inequívoca, mantém `IN_DOUBT`.

Inicial + até três retentativas diagnosticadas por tarefa. Releituras da mesma execução têm contador separado, também limitado e persistido; nenhuma nova compra é autorizada apenas porque o GET falhou. Mudança de ferramenta precisa de motivo e relação com a mesma tarefa. Cancelamento/perda de lease prevalece sobre qualquer repetição. Worker redelivered reutiliza operações persistidas.

## Ferramentas internas propostas

Nomes abaixo são contratos candidatos, não ferramentas existentes:

| Ferramenta | Entrada lógica | Saída | Restrição |
|---|---|---|---|
| `request_collection` | Capability, consulta ou URLs descobertas, finalidade | ID da tarefa/operação e estado | Provider permitido pelo snapshot; execução pelo gateway |
| `inspect_collection` | ID de operação | Estado, diagnóstico e manifesto | Não compra nem altera provider |
| `read_evidence_parts` | IDs de artefato/partes | Conteúdo higienizado, referências e cursor | Acesso somente ao corpus da análise |
| `open_course_page` | URL de evidência ou descoberta validada | Sessão vinculada e artefato | Validação de destino e redirecionamentos |
| `inspect_course_page` | Sessão e formato de inspeção | Conteúdo/snapshot com IDs | Conteúdo preservado antes de projeção |
| `interact_course_page` | Sessão, referência observada, ação permitida | Novo estado e artefato | Ações de pesquisa, sem submissão de matrícula, compra ou revisão humana |
| `close_course_page` | Sessão | Estado fechado | Limpeza idempotente de recursos |
| `submit_dossier_draft` | Rascunho estruturado, facts hash e IDs de evidência | ID/revisão ou diagnóstico | Opcional; não publica nem aprova parecer humano |

A mesma aquisição chamada pelo workflow e pelo MCP recebe a mesma identidade. Autorizar destino inicial, redirecionamento e subrequisições relevantes; preservar proteção contra endereços privados e sessões de outra instituição. A disponibilidade de JavaScript genérico no Scrapling não exige expô-lo sem restrição ao agente.

## Invocação e sessão Codex

Envelope do runner: `tenant_id`, `analysis_id`, checkpoint, `invocation_id`, ID de sessão quando houver, hashes da entrada, schemas, versões do CLI/modelo/prompts/skills e configuração das ferramentas. IDs e hashes são atribuídos pelo backend, sem confiar na saída do modelo.

Executar sem shell construído por concatenação; prompt por stdin e argumentos explícitos. Registrar JSONL de eventos e mensagem final separadamente. Sucesso de processo exige também evento de conclusão, saída parseável e validação de domínio; exit code zero não equivale a dossiê aprovado. Quota, expiração de autenticação, encerramento abrupto e saída inválida são diagnósticos distintos. [Contrato de execução oficial](https://learn.chatgpt.com/docs/non-interactive-mode).

Contexto de pesquisa pode retomar a sessão autorizada. Julgamentos delimitados recebem somente dados necessários e não herdam ferramentas de pesquisa ou decisões anteriores sem necessidade. A identidade do modelo usada no cache não pode ser apenas o nome da classe do adaptador. Compaction preserva continuidade operacional, mas não substitui a leitura integral por partes.

## Dossiê e CMS

Manter `DossierFacts` e `DossierOutput` como entrada/saída canônicas. Enum de evidências, hash dos fatos, verificadores numéricos/semânticos e construtor `build_cms_dossier_pages` continuam no fluxo. O contrato é persistido antes da apresentação, e `_hydrate_dossier_presentation` deve reproduzir o conteúdo verificado após reload.

KPIs, scores, confiança, cobertura e cenários financeiros vêm dos motores. Textos, síntese, SWOT/TOWS e comparações usam fatos/citações verificados. Rascunho incremental, se adotado, usa controle otimista de revisão e mesma fonte de verdade da hidratação. Uma revisão humana existente nunca vira aprovação automática por saída do CLI.
