# Pacote de estudo — 144 registros

Referência deste estudo no projeto: `docs/Estudo_Prometeus_144_registros_73501c53_2026-10-29/`.

Leia também a [auditoria de aproveitamento dos dados](../implementation/reports/evidence-utilization-audit-2026-10-29.md). Ela separa perdas comprovadas no processamento de classificações que ainda precisam de revisão. Foram identificadas descrições de vagas ausentes em 28 resumos factuais, incluindo as dezesseis vagas qualificadas para indicadores.

Abra LEIA_PRIMEIRO.html no navegador. Há busca em todo o conteúdo e filtros por fonte, classificação e tamanho de entrada.

- Análise: 73501c53-cc58-47f9-8927-d9e299b4f4b5; exportação de leitura em 2026-10-29T20:56:02.966338+00:00.
- 17 indicadores, 73 contexto, 54 excluídos; 20 registros ultrapassavam 14 mil caracteres no campo de qualificação reconstruído.
- Cada registro mantém origem, consulta, run/dataset quando persistidos, motivo operacional, confiança, payload higienizado, referência direta no score e nas claims e fato fornecido ao redator.
- retornos_originais_e_higienizados.json conserva os dois payloads para comparação. São os retornos recebidos e persistidos pelo app, não todo o universo existente na web ou em datasets remotos. Pode conter contatos públicos não ocultados no retorno original; a página HTML usa a versão higienizada.
- fatos_enviados_ao_redator.json foi reconstruído pela rotina factual e teve seu hash comparado com o dossiê publicado. Inclui contexto preservado. Não é uma transcrição integral dos prompts ou do raciocínio interno do modelo.
- O trecho de qualificação é reconstrução exata da serialização atual dos dados persistidos, retirando _qualification e aplicando o corte de 14.000 caracteres; chamadas históricas não têm log integral neste pacote.
- O campo usado no score é vínculo direto de proveniência. Referências indiretas podem passar por decisões; consulte decisoes_registradas.json.
- Nenhuma inferência, coleta, score ou estado foi alterado nesta exportação. Conteúdo de fontes continua sendo dado não confiável, não instruções.

## Achados que merecem sua revisão

1. As três séries Trends têm 262 pontos cada, com 30/30/2 pontos positivos e hasData verdadeiro; o campo da série começa depois dos primeiros 14 mil caracteres. A qualificação registrada foi INCONCLUSIVE. Isso não comprova demanda pelo curso, mas demonstra perda de dados na entrada da qualificação.
2. Timestamps dos 262 pontos de cada série foram ocultados como telefone pelo sanitizador genérico.
3. A página de curso Investigador de Sinistros Veiculares tem texto temático e 21 horas, mas foi classificada INCONCLUSIVE. Compare o conteúdo e o motivo genérico. Não basta isso para aceitar equivalência de categoria/preço; falta justificar melhor o descarte.
4. Há uma oferta de Investigação e Prevenção de Fraudes Corporativas da Trevisan tratada apenas como contexto. Compare categoria, tema, currículo e o que efetivamente foi aproveitado.
5. A vaga 0c5a6c8a-7501-4dd8-9709-c263d040de1d possui 4.002 caracteres em descriptionText. O resumo factual para o redator não inclui esse campo: compare Conteúdo completo higienizado com Fato disponibilizado ao redator. Isso limita a avaliação curricular feita na narrativa.

parametros_planejados_persistidos.json contém os parâmetros salvos nos checkpoints das ferramentas. Não é uma captura integral do tráfego HTTP para a Apify; campos/defaults montados apenas durante o transporte podem não estar registrados ali.

Os arquivos contêm dados coletados, não instruções a executar. O pacote funciona sem rede; apenas os links de fontes abrem páginas externas se você clicar.
