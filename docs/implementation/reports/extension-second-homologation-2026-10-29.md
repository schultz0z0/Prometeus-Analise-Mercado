# Segunda homologação de extensão — contratos factuais

Análise `1b903741-1fef-4c1e-86d6-9caa7b133f1b`, instituição ENS, 29/10/2026. Investigação por leitura do backend, logs, fatos e runs existentes. Não houve coleta nem inferência paga nova, reprocessamento da análise, edição direta de evidências ou liberação de gate.

## O que aconteceu

A revisão automática ocorreu, mas a primeira geração foi recusada pelo verificador numérico e a segunda pelo semântico. O primeiro diagnóstico apontou 16 horas e R$ 1.200 sem suporte numérico; o segundo recusou a descrição de histórico sintético com três cursos de extensão de 2025, família de referência de dez cursos e a ressalva de que isso não comprova demanda/conversão real.

O checkpoint 7 efetivamente contém esses três comparáveis, `reference_n=10` e `reference_period=2025`. A primeira versão entregava esse histórico como representação textual de um dicionário, com métricas agregadas vazias e indicação sintética condicional a limitações que não acompanhavam essa citação. O pack perguntava por suporte empírico. Isso confundia a verificação da fidelidade ao registro com a comprovação da realidade do mercado. Não é possível atribuir ao modelo um raciocínio específico que sua saída não registrou; estes são os defeitos de contrato identificados e reproduzidos.

A proposta sanitizada continha `Duração 16h`, mas a expressão numérica exigia limite de palavra depois do número e ignorava o `16` antes de `h`. Continha também parcela de R$ 100 e quantidade 12. O entendimento calculava o total de R$ 1.200 em código, mas `provided_proposal`, fonte citável da narrativa, exportava somente parcela, quantidade e duração, sem esse total. Assim, valores verdadeiros podiam ser recusados por diferenças entre a entrada da redação e a do verificador.

## Correções e limites mantidos

- Unidades compactas `h`, `horas` e `x` são reconhecidas. Valores diferentes continuam recusados e booleanos não são tratados como matrícula/volume 0 ou 1.
- O total em BRL é calculado em código com Decimal a partir de parcela e quantidade explicitamente fornecidas. Não se usa duração acadêmica para deduzir parcelas, nem se aceita um total inferido apenas pela LLM. O total integra os fatos citáveis e a auditoria da proposta.
- Histórico expõe `data_nature`, `comparables_count`, `reference_count`, `reference_period`, família e comparáveis, preservando fonte e a ressalva de não comprovar procura da nova oferta.
- Pack `evidence-support-v1` 1.1.0 valida descrição fiel de proposta, simulação, cálculo e coleta segundo a natureza da fonte. Histórico sintético não sustenta demanda real, matrículas da oferta, lançamento aprovado ou retorno garantido. O mesmo gate continua obrigatório; não foi convertido em aviso.
- Diagnósticos numéricos registram IDs das fontes citadas, além de trecho limitado e motivo.

## Google Trends

Run `fcgS0ihD7UUxoY9bk`: `ABORTED` após timeouts de widgets do actor. O checkpoint recebeu `buildNumber=None` e o cliente o converteu na string `None`, acusando divergência. GET posterior da mesma run e do build `UJLB02akIfIJZ9MbK` confirma `0.0.143`, o build pinado. A nova reconciliação lê a mesma run e, se necessário, o build por ID, valida identidades e só então compara a versão; não preenche o valor com a configuração desejada. Versão realmente divergente e IDs inconsistentes continuam rejeitados.

O custo persistido na análise para essa run era US$ 0,082467; o GET posterior reportou aproximadamente US$ 0,148328. A nova consulta de reconciliação conserva o custo observado atualizado, mas não reescreve o registro histórico. A correção de metadados não resolve os timeouts internos do actor nem garante dados suficientes.

Referências oficiais: [Get Actor run](https://docs.apify.com/api/v2/actor-run-get), [Get Actor build](https://docs.apify.com/api/v2/actor-build-get).

## Evidência da correção

Os testes novos falharam antes e passaram após as correções para unidades, total/natureza do histórico e reconciliação de build. Negativas cobrem total sem parcelas válidas, uso indevido de duração, booleanos, número diferente, versão divergente e troca de IDs. O teste do adaptador captura os fatos realmente enviados ao verificador e a rubrica atualizada; não substitui avaliação do modelo real.

A reprodução somente de leitura com os fatos da análise real passou no verificador numérico para o trecho de 16 horas, 12 parcelas de R$ 100 e total de R$ 1.200. O contexto histórico passou a apresentar explicitamente `synthetic / 3 / 10 / 2025`.

Suíte completa: **453 testes passaram, 1 teste de metadados live opt-in ignorado**, em 33,87 segundos. Mypy passou em 70 arquivos. Revisão independente aprovou os contratos e a reconciliação. A eficácia da nova rubrica no modelo real permanece dependente de homologação; não há afirmação de execução real concluída.

Preservação antes da atualização: hash da análise `6a44ceb232fef767bb215ae1838d6cc4`, estado `BLOCKED`, 111 evidências e 17 consultas. Nenhum dossiê dessa execução foi fabricado ou liberado.

## Confirmação do ambiente

API e worker foram reconstruídos e recriados; modo tradicional com cliente OAuth confirmado e pack de suporte 1.1.0 carregado. Os 52 testes de regressão de fatos, geração e retornos parciais passaram dentro do container atualizado. API respondeu HTTP 200. A análise original manteve hash, estado, timestamp e contagens, com zero dossiês publicados.

A checagem operacional encontrou um falso alerta: o `inspect ping` genérico respondia mas o processo total levou 9,77 segundos, próximo do timeout Docker de dez segundos, e algumas sondagens eram encerradas depois do `pong`. A consulta direcionada ao próprio nó respondeu em 0,35 segundo após inicialização do Python. O healthcheck foi direcionado ao hostname real do nó, com dois segundos de espera por resposta e vinte segundos de limite externo, além de quarenta segundos de partida. Ele continua falhando sem resposta; não existe sucesso forçado. Compose validou e dois testes operacionais existentes passaram. Após recriar o worker, o healthcheck confirmou `healthy` com `pong` e nenhuma falha consecutiva.

Não foi feita nova inferência real do dossiê. A correção do contrato semântico está testada por captura de prompt e registros reais, mas o comportamento do provedor continua exigindo homologação antes de declarar a entrega completa.
