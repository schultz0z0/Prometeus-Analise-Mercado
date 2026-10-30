# Auditoria de aproveitamento dos 144 registros

Data: 29/10/2026. Análise ENS `73501c53-cc58-47f9-8927-d9e299b4f4b5`.

## Escopo e método

Pacote de estudo preservado pelo usuário em `docs/Estudo_Prometeus_144_registros_73501c53_2026-10-29/`: [guia de leitura](../../Estudo_Prometeus_144_registros_73501c53_2026-10-29/COMO_ESTUDAR.md). Os dez arquivos recebidos foram comparados por SHA-256 com a exportação e coincidiam antes da inclusão deste vínculo documental.

Leitura da análise, dossiê, payloads originais e higienizados, decisões e proveniência persistidos. A rotina factual foi executada sem inferência e seu hash conferido com o dossiê publicado: `7761d831324c2e5130258bc80691f4e3b8c9367afff5677cc4a0a890710f7a6e`. Nenhuma nova coleta, inferência, alteração de score ou de estado. O E2E anterior validou o percurso técnico com recuperação; não demonstra qualidade suficiente de inteligência de mercado.

O pacote local de estudo contém 144 IDs únicos, 144 retornos originais, conteúdo higienizado, motivos operacionais de qualificação, consultas, execuções e fatos disponibilizados ao redator. Foram registrados 17 itens para indicadores, 73 de contexto e 54 excluídos. Vínculos diretos de evidência não representam todos os possíveis vínculos indiretos via julgamento semântico.

## Perdas verificadas

### Corte da entrada de qualificação

[`qualify_market_evidence.py`](../../../src/prometeus/application/qualify_market_evidence.py) serializa título, URL e payload higienizado e corta a string em 14.000 caracteres. Vinte dos 144 registros excedem esse limite. A reconstrução retira `_qualification`, como faz o código; não existe neste pacote um log integral de cada chamada histórica.

Nas três evidências Google Trends, o campo `interestOverTime_timelineData` começa aproximadamente nos caracteres 24.540–36.696, depois do corte. Portanto, a série não aparece no campo de evidência enviado à qualificação. Há 262 pontos por registro: as duas capturas de “litigância predatória” possuem trinta pontos positivos com `hasData`; “fraude em seguros”, dois. A baixa densidade limita a conclusão, mas não equivale à ausência total de série. As classificações registradas são `INCONCLUSIVE`.

IDs: `88f8fe8d-f605-48c0-b4bc-9fa0fc06ab00`, `679c794b-638a-4158-a2cd-5381a740b68d`, `a3ded491-613a-4ffd-b434-5df9f0c08b00`. As capturas podem repetir a mesma série; não se devem somar como mercados ou amostras independentes.

### Sanitização de timestamps

Nos três registros, os 262 campos `time` foram substituídos por marcador de telefone. O sanitizador genérico alterou metadados temporais numéricos. Os payloads originais estão disponíveis para comparação, sem necessidade de repetir Actors.

### Descrição de vagas omitida da base de redação

[`synthesize_dossier.py`](../../../src/prometeus/application/synthesize_dossier.py) busca campos `description`, `text`, `markdown`, `caption`, `comment` e `body`, mas não `descriptionText`/`descriptionHtml`. Vinte e oito registros de vagas possuem descrição que não aparece no resumo factual, incluindo os dezesseis qualificados para indicadores.

Exemplo: `0c5a6c8a-7501-4dd8-9709-c263d040de1d`, Analista Sênior de Investigação de Sinistros e Prevenção à Fraude. O retorno contém 4.002 caracteres em `descriptionText`, incluindo responsabilidades e requisitos. Seu fato para o redator preserva título, empresa e localização, mas omite essa descrição. A narrativa final, consequentemente, dispõe de base mais pobre para discutir competências e aderência curricular. A qualificação e a redação são etapas diferentes; a omissão aqui não prova que a descrição também faltou na primeira.

## Classificações que exigem revisão de conteúdo

- `78e3a3f1-efd5-4769-aa20-5459a18f6485`: página de Investigador de Sinistros Veiculares, com texto temático e carga horária de 21 horas, classificada `INCONCLUSIVE`. Sua entrada reconstruída tem 9.284 caracteres, abaixo do corte; o motivo genérico não esclarece adequadamente essa perda.
- `44ca6987-353d-47ea-b74f-989ed1ef347b`: oferta de Investigação e Prevenção de Fraudes Corporativas da Trevisan, com currículo disponível, classificada como contexto. Requer avaliar pertinência como oferta adjacente e separar isso da comparabilidade estrita de categoria e preço.

Não se pode promover automaticamente esses cursos a concorrentes equivalentes nem inventar preço ausente. Entretanto, um descarte para um pilar não deve apagar sua utilidade para currículo, posicionamento ou contexto.

## Implicação

Há falhas comprovadas de preparação e aproveitamento dos dados dentro do sistema; não é correto atribuir todos os resultados insuficientes à Apify ou à ausência de mercado. Também existem ruído de busca e fontes inadequadas, como página não encontrada e cursos de outros temas. O resultado atual precisa ser reavaliado após corrigir as perdas. Os achados não demonstram por si só viabilidade ou aprovação comercial.

O estudo exportado mantém a análise original intacta. A página HTML apresenta dados higienizados; o JSON separado conserva o retorno original para comparação local. Motivos de classificação são registros operacionais, não transcrições do raciocínio interno do modelo.
