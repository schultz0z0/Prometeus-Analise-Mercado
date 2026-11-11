# Retenção integral, leitura e validação do CMS — 11/11/2026

## Escopo e resultado

Esta entrega integra a coleta integral e a leitura retomável ao dossiê CMS de nove páginas, preservando as alterações de interface recebidas no commit `a5efacc`. Não representa certificação de acurácia de toda análise nem homologação de suficiência dos cinco pilares externos. Nota, confiança, disponibilidade de dados, leitura do corpus e recomendação são verificações distintas.

## Correções

- O cliente recupera todo o dataset produzido, sem novo corte pelo limite de entrada do Actor. Originais, versões higienizadas, campos desconhecidos, filhos, duplicatas e diagnósticos ficam preservados e conciliados por run/dataset/índice/hash.
- `FAILED`, `TIMED-OUT` e aborto por timeout também preservam seus datasets. Falha no GET reconcilia a mesma execução antes de autorizar outra compra. Uma releitura curta compatível conserva o maior prefixo já recuperado; divergência de conteúdo mantém as versões e exige revisão de integridade.
- O leitor entrega todos os campos em partes, valida referências e citações, salva progresso e retoma somente partes compatíveis pendentes. Datas em chaves JSON, números equivalentes e identificadores que parecem expoentes não causam rejeições indevidas.
- Qualificação recebe a leitura normalizada e o contexto do arquivo de origem, com atribuição explícita de linhagem. A síntese recebe também as interpretações de arquivos sem evidência normalizada, em `collection_reading_context`, separado dos fatos admitidos. Leitura não promove diagnóstico técnico a prova de mercado.
- Síntese bloqueia antes de chamar a redação quando há arquivo remoto atual ausente ou leitura incompleta. As contagens públicas não incluem payload privado nem checkpoints completos.
- Módulos estruturados e textos curriculares entram juntos no julgamento e na comparação histórica. Não se reduzem os limiares de confiança para preencher um card.
- Pesquisa complementar deixa de parar após uma rodada. Cada rodada usa histórico de todas as consultas, diagnósticos e custo atualizados, com plano estável e deduplicação de consultas equivalentes. O teste de ponta a ponta exige duas expansões sucessivas e retomada sem nova compra; esgotar consultas continua sendo lacuna explícita.
- A referência de preço aceita categoria explícita em metadados da própria oferta, com campo e valor rastreáveis. Conflitos de categoria são excluídos e cursos relacionados não suprem a classificação.
- O CMS usa os pesos persistidos e distingue pilar ausente de nota zero. Variação temporal exige série observada; referências de mercado, percentuais temáticos, posições de concorrentes e metas de retenção não são inventados.
- As páginas financeiras consomem o contrato canônico (`calculable`, `net_profit`) e preservam resultados negativos e custos zero. Valores ausentes não ganham classificação favorável.
- O merge de migrações `0015_merge_cms_collection` une as revisões departamentais à recuperação de coleta, sem reescrever as migrações existentes. Consultas de revisões não criam tabelas durante GET.

## Canário real de Trends em 10/11

O build fixado `data_xplorer/google-trends-fast-scraper@2.10.2` executou quatro consultas sequenciais no Brasil, janela de doze meses, com 256 MB. As quatro terminaram `SUCCEEDED`, cada uma retornando 53 pontos semanais, incluindo um ponto parcial final. Todos os datasets foram preservados; 20 partes e 452 fragmentos tiveram respostas validadas da LLM real configurada via OAuth. A conferência de retomada reutilizou as partes já concluídas.

O custo observado das quatro execuções foi US$ 0,108. Houve também uma execução anterior do build antigo `0.0.33`, que falhou por proxy e ficou preservada como diagnóstico; seu custo observado foi US$ 0,027. Não se contabiliza a cota OAuth como preço de API estimado.

Índices relativos não medem pessoas, matrículas ou volume absoluto; consultas independentes possuem normalizações próprias. Zeros e pontos parciais são mantidos no acervo, e parciais não entram nas métricas de comparação.

## Preservação e operação

Antes da atualização de 10/11 foi criado backup privado do PostgreSQL, e a migração foi aplicada no Docker local. A conferência antes/depois preservou os 33 cursos, 66 funis sintéticos e os 12 dossiês então existentes. Em 11/11, o baseline recebido contém 13 dossiês, incluindo a vitrine do CMS adicionada pelo usuário; a vitrine não é usada como canário real de mercado. Esta auditoria não executa o seeder de vitrine nem redefine o histórico ENS.

Datasets, logs, credenciais, cópias do banco e capturas de navegador ficam em diretórios privados ignorados pelo Git. A configuração local fixa o novo Actor, preservando os demais provedores e a ausência de JEV obrigatório no modo tradicional.

## Validação e limites

Os testes cobrem extração completa, falhas e retomadas, preservação de prefixo, identidade de arquivos atuais, citações, entrada da redação, ausência de promoção factual, pesquisa em várias rodadas, categoria de preço, contrato financeiro real, renderização e isolamento institucional. Em 11/11, a suíte completa passou no Windows e no Linux: **943 aprovados, 5 pulados** em cada ambiente. Os cinco pulados dependem de opt-in para verificações reais Apify/LLM; não equivalem a testes reais executados nesta rodada. Ruff passou e mypy validou 102 arquivos. Há um aviso de depreciação de configuração do Alembic.

As nove subpáginas foram percorridas no navegador sem erros de console. Após reiniciar API, worker e scheduler, os serviços ficaram saudáveis e o baseline de 11/11 confirmou hashes idênticos dos 33 cursos, 66 funis e 13 dossiês existentes. A navegação da vitrine valida a interface, não seus números como evidência de mercado.

Continuam pendentes de validação específica: suficiência dos cinco pilares externos em uma nova execução real completa, categorias disponíveis somente em texto livre não atribuído à oferta e calibração da rubrica experimental de publicidade. O mecanismo agora permite várias rodadas, mas isso não garante que toda consulta tenha evidência pública disponível. A síntese recebe todas as interpretações e não as recorta silenciosamente; corpora grandes ainda exigem validar a capacidade de contexto do provedor. Esses pontos não podem ser declarados resolvidos pelo sucesso do canário de Trends ou pelo novo layout.
