# ADR-0008 — Modos de IA e uso direto do plano ChatGPT

**Status:** decidido em 2026-10-27. **Substitui parcialmente o ADR-0003** quanto à obrigatoriedade do JEV.

## Decisão

O Prometeus opera em dois modos explícitos:

- `traditional`: uma LLM tradicional executa planejamento, julgamentos semânticos delimitados e síntese;
- `hybrid`: o JEV executa decision packs atômicos e a LLM tradicional continua responsável por planejamento e síntese.

JEV não é obrigatório no modo `traditional`. Fórmulas financeiras, scoring, permissões, transições de estado, orçamento de coleta e verificação de evidências permanecem em código nos dois modos.

A LLM tradicional pode ser autenticada por chave da OpenAI API ou pelo fluxo oficial para aplicações locais/open source **Sign in with ChatGPT**, que usa a cota do plano ChatGPT elegível. O fluxo OAuth deve:

1. usar registro dinâmico ou o `client_id` já emitido, host ID estável, PKCE S256, state e nonce;
2. exigir `chatgpt.tokens.use.direct` e validar o ID token;
3. descobrir os modelos disponíveis com `GET /v1/models`;
4. provar a conexão com `POST /v1/responses`, `store=false`, `stream=true`, até `response.completed`;
5. persistir e renovar o par rotativo de tokens fora do Git;
6. bloquear a análise quando credencial, escopo, modelo ou inferência real falhar.

Nenhum endpoint pode fabricar token, modelo, evidência ou resposta para parecer conectado. Fakes ficam restritos a testes automatizados; a única base sintética admitida no runtime de demonstração é o histórico institucional da ENS, identificado como tal.

## Consequências

- testes sem chave JEV continuam completos pelo modo tradicional;
- o worker lê o arquivo de credenciais OAuth compartilhado e renova tokens expirados;
- respostas ChatGPT usam somente a Responses API pública autorizada para esse fluxo, nunca endpoints internos do ChatGPT;
- uma conexão antiga sem o escopo direto é considerada desconectada e exige novo consentimento.

## Referências oficiais

- [Registro e login para aplicações open source](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Tokens e renovação](https://developers.openai.com/siwc/token-sharing-open-source/token-reference)
- [Contas e sessões](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
