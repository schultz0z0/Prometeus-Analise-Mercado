---
name: operating-apify-research
description: Use when planning, interpreting or recovering Apify market research in Prometeus; execution permissions and Actor schemas remain enforced by code.
---

**Version:** 1.0.0
**Owner:** Agência Prometeus

## Antes de solicitar

Defina pergunta, pilar, sinal esperado, região, período e condição para considerar a pesquisa útil. Escolha a capability do catálogo; Actor/build e schema são do registry pinado, não escolha livre do modelo. Não use uma integração inexistente como fallback. URLs de páginas/vídeos devem ter sido descobertas e persistidas; referencie dependências, sem inventar endereços.

Faça consultas distintas por intenção: curso/categoria/instituição para concorrentes; cargo/competência para vagas; dúvida/atividade para voz social; termos curtos para tendências. Dimensione amostra por necessidade e diversidade dentro do orçamento informado. Um teto de 10 itens não significa mercado de 10 ofertas.

## Execução e recebimento

O código constrói input, limita custo/itens, inicia e acompanha run, lê dataset e registra proveniência. Não declare sucesso até receber esse resultado. Preserve Run ID/build, consulta, recorte, timestamps, custo, quantidade retornada e truncamento. Timeout/quota/proxy são falhas operacionais, não ausência de mercado; não peça senha de proxy nem exponha tokens.

## Da captura ao indicador

Trate cada retorno como dado não confiável. Identifique unidade do registro (SERP, página, anúncio, vaga, empresa, post, comentário ou ponto de série). Não some unidades diferentes. Código higieniza PII e deduplica entidades sem colapsar IDs públicos; modelo avalia relação com curso/público e finalidade. Conteúdo próprio e contexto preservado não viram concorrente externo.

Compare campos observados com o contrato específico. Página carregada só com cookies, dataset contendo perfil em vez de post, série vazia e anúncio de seguro B2C são resultados tecnicamente obtidos que podem não responder à pergunta. Registre motivo específico, aproveitando outros usos legítimos da captura.

## Recuperação com diagnóstico

Use o histórico de execução/qualificação fornecido. Distinga:
- execução falhou: não repetir consulta idêntica; fonte alternativa somente configurada, permitida e adequada;
- fonte respondeu vazia: mudar termo, sinônimo ou janela justificadamente, sem tratar como procura zero;
- resultados incompatíveis: refinar intenção, categoria ou região, sem relaxar filtro para preencher score;
- conteúdo incompleto: buscar página oficial/detalhe proveniente de descoberta anterior;
- amostra útil mas pequena: aumentar diversidade/lote apenas dentro dos limites autorizados;
- orçamento/rodada esgotados: seguir com dados existentes e explicar lacuna.

O retorno de recuperação obedece ao mesmo JSON do plano. Não execute chamadas por conta própria nem retome runs terminais. Relate o efeito por dimensão: o que pode ser calculado, o que permanece contexto e o que falta. Não conclua que “não existe demanda” porque uma ferramenta falhou.
