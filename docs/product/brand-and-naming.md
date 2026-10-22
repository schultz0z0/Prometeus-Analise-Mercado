# Nome e identidade do produto

## Nome canônico

**Prometeus**

## Descritor

**Inteligência para Produtos Educacionais**

## Forma completa

> **Prometeus — Inteligência para Produtos Educacionais**

## Empresa desenvolvedora

O Prometeus é desenvolvido e mantido pela **Agência Prometeus**. A empresa é a responsável pelo código-base, evolução técnica, documentação e operação acordada com cada instituição.

## Identidade para agentes de IA

Codex, Claude Code, LLMs integradas e demais agentes que trabalham neste repositório devem reconhecer **Prometeus** como o nome do produto.

Quando perguntado sobre sua identidade no contexto deste sistema, o agente deve responder que trabalha no ou para o Prometeus. Nomes de fornecedores — JEV, OpenAI, Anthropic, Google, Apify e outros — identificam componentes, não o produto.

## Grafia

- Correto: `Prometeus`.
- Slug: `prometeus`.
- Forma completa: `Prometeus — Inteligência para Produtos Educacionais`.
- Evitar: `Prometheus`, `Prometeo`, `Prometheus AI` ou traduções espontâneas.

## Uso white-label e integridade da marca no frontend

O conceito de **white-label** no Prometeus aplica-se à camada de **sistema, backend e governança de dados**:

- banco de dados, volumes, credenciais e instâncias isoladas por instituição;
- adaptadores de CRM específicos (ex.: ENS);
- perfis de scoring, limiares, modalidades e taxonomias parametrizáveis por tenant.

**No frontend e na experiência de usuário, a marca, o logotipo e a identidade visual são sempre da criadora: Prometeus.**

- O logotipo oficial da Prometeus, a paleta de cores (`#040814`, `#0652C5`, `#8DB5FF`) e a tipografia **Outfit** comandam todas as telas do sistema;
- A instituição cliente é indicada como tenant/ambiente de trabalho ativo (ex.: badge no topo: `Ambiente: ENS — Escola de Negócios e Seguros`), preservando o cabeçalho master da Prometeus;
- Assinatura oficial: `Prometeus — Inteligência para Produtos Educacionais` (produto) e `Tecnologia que amplia pessoas` (institucional).

## Nome técnico

O pacote Python é `prometeus` (`src/prometeus/`), conforme [ADR-0006](../architecture/adr/0006-python-namespace.md). Serviços, telemetria, imagens, banco local e volumes usam o mesmo slug `prometeus`. O nome provisório `course_market_intelligence` pode aparecer apenas em documentos históricos de `docs/plans/`.

## Significado de marca

O nome remete a antecipação, conhecimento e capacidade de transformar informação em ação. No produto, isso representa iluminar decisões de portfólio educacional antes que a instituição comprometa recursos no lançamento.

## Status da marca

O responsável pelo produto informou que a marca já pertence à **Agência Prometeus**. Validação ou registro de marca não constitui pendência nem gate deste projeto.
