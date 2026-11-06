"""Generate audit artifacts from the persisted scan database, without application changes."""
import argparse
import hashlib
import html
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCAN_ID = "981589ba-cdbd-43a6-84ab-0c624203f2f1"
HERE = Path(__file__).parent
ROOT = HERE.parents[2]
API = "src/prometeus/entrypoints/rest/app.py"


def finding(title, description, root_cause, intended, trace, conditions, payloads, steps, result, fix, level, likelihood, impact, confidence):
    return {
        "verdict": "confirmed", "title": title, "description": description,
        "root_cause": root_cause, "intended_behavior": intended,
        "trace": [dict(zip(("kind", "file", "line", "scope", "description"), item)) for item in trace],
        "conditions": [dict(zip(("kind", "description"), item)) for item in conditions],
        "execution": {
            "attacker_perspective": "Solicitante que alcança a API da instituição; no XSS, um proponente capaz de introduzir metadado HTML em uma análise posteriormente concluída.",
            "payloads": payloads, "instructions": steps, "expected_result": result,
        },
        "remediation": {"strategy": fix},
        "severity": {
            "likelihood": {"score": likelihood, "reason": "Acesso depende da exposição da API; o compose não restringe as portas ao loopback. XSS exige dossiê concluído e abertura do portfólio."},
            "impact": {"score": impact, "reason": "Configurações e decisões institucionais podem ser alteradas sem principal; XSS executa código na origem do portal, sem sessão autenticada existente a roubar."},
            "overall_severity": level,
        },
        "confidence": {"score": "high", "reason": confidence},
    }


FINDINGS = [
    finding(
        "API permite decisões institucionais e configuração administrativa sem autenticação",
        "As rotas REST não verificam identidade ou escopo. Em banco SQLite em memória, GET /v1/analyses sem Authorization retornou 200 e dados da proposta; POST /decisions com user_id='forged-director' e user_role='director' retornou 201. POST /v1/settings anônimo gravou OPENAI_BASE_URL=http://127.0.0.1:19999/capture e APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS=99999.0 em arquivo temporário e retornou 200. Isso permite falsificar deliberação, ler propostas e alterar provedores/orçamento. Mudar a base URL ainda direciona prompts e o cabeçalho Bearer do cliente LLM ao destino configurado, dependendo do provedor/modo ativo. Nenhum segredo real foi lido ou transmitido.",
        "submit_human_decision em src/prometeus/entrypoints/rest/app.py confia em user_id/user_role fornecidos pelo solicitante e não exige autenticação/autorização, permitindo registrar decisões institucionais forjadas.",
        "RNF-004 exige autenticação máquina-a-máquina e autorização por escopo; mudanças administrativas e decisões humanas devem ter principal e permissão verificáveis.",
        [("entrypoint", API, 736, "submit_human_decision", "Recebe análise e identidade/decisão declaradas pelo solicitante sem dependência de autenticação."),
         ("propagation", API, 752, "submit_human_decision", "Copia user_id e user_role do payload para o registro de decisão."),
         ("sink", API, 760, "submit_human_decision", "Faz commit do registro institucional sem validar principal ou escopo.")],
        [("network_routing", "O atacante precisa alcançar uma porta da API; firewall/proxy externo pode restringir acesso, mas não foi testado. compose.yaml publica 8000 e 1455 sem binding ao loopback."),
         ("data_state", "Para falsificar decisão, uma análise deve existir. A listagem também está sem autenticação."),
         ("system_configuration", "Para exfiltração de chave por troca de base URL, a execução posterior deve usar um provedor que envie o Bearer à base configurada. Esta cadeia não foi exercitada com credenciais reais.")],
        ["GET /v1/analyses?tenant_id=ens", "POST /v1/analyses/{id}/decisions {\"user_id\":\"forged-director\",\"user_role\":\"director\",\"decision\":\"APPROVED\",\"rationale\":\"Isolated audit proof\"}", "POST /v1/settings {\"openai_base_url\":\"http://127.0.0.1:19999/capture\",\"apify_max_charge\":99999}"],
        ["Execute security_probe.py com o Python do ambiente virtual.", "Inspecione anonymous_list, anonymous_forged_decision e anonymous_settings_write em security-probe-output.json.", "Nenhum request usa Authorization. O banco e o arquivo de configuração são isolados e temporários."],
        "Listagem 200, decisão forjada 201 e alteração de configuração 200 com os novos valores persistidos.",
        "Exigir principal autenticado e escopos em todas as rotas de negócio; restringir settings/OAuth/seed a administradores; derivar ator de decisão do principal. Vincular recursos ao tenant do deployment e do principal. Restringir portas publicadas e validar destinos de provedores conforme política operacional.",
        "high", "high", "high", "Código e chamadas ASGI isoladas confirmam leitura/gravação sem credencial. Exposição pública não foi testada e depende da rede real.",
    ),
    finding(
        "Portfólio executa HTML armazenado nos metadados de diagnósticos verificados",
        "O portfólio interpola name, area, level e modality sem escape antes de atribuir o template a innerHTML. A listagem REST preserva course_name bruto e a CSP da SPA permite handlers inline. Um Chromium isolado com o renderer real e payload <img src=x onerror=window.__audit_xss=1> retornou marker=1. A fixture SQLite em memória com transições válidas COMPLETED, scoring e dossiê VERIFIED mantém o payload e passa o filtro de loadCompletedAnalyses. A prova não executa LLM/Actors reais: o atacante precisa que metadado malicioso alcance uma análise concluída e verificada. Uma análise apenas QUEUED não é exibida nessa lista.",
        "renderPortfolioView em web/js/views/portfolio-view.js não escapa metadados de cursos antes de interpolá-los em HTML, permitindo execução de handlers na origem do portal.",
        "Metadados de propostas devem aparecer como texto, inclusive quando contêm HTML; verificação factual do dossiê não autoriza tratar os metadados como código HTML.",
        [("entrypoint", API, 233, "create_analysis", "Encaminha course_name recebido no corpo à criação da análise."),
         ("propagation", "src/prometeus/application/create_analysis.py", 91, "CreateAnalysisUseCase.execute", "Preserva o nome no agregado a persistir."),
         ("propagation", API, 420, "list_analyses", "Devolve o course_name persistido como name sem sanitização HTML."),
         ("propagation", "web/js/views/portfolio-view.js", 240, "renderPortfolioView", "Interpola course.name em conteúdo HTML sem escapeHtml."),
         ("sink", "web/js/app.js", 49, "PrometeusApp.render", "Atribui template das views a root.innerHTML, interpretando handlers HTML.")],
        [("data_state", "Uma análise com metadado HTML deve estar COMPLETED e ter dossiê VERIFIED; store.js filtra ambos antes de inserir no portfólio. A prova usou fixture isolada, sem provar que uma LLM real aprovará um título malicioso."),
         ("user_interaction", "Um usuário abre a aba Novos Diagnósticos do portfólio."),
         ("system_configuration", "A CSP entregue pela aplicação permite script-src 'unsafe-inline'.")],
        ["course_name=<img src=x onerror=window.__audit_xss=1>"],
        ["Execute security_probe.py para confirmar que uma fixture completed/verified preserva o payload e passa o filtro do store.", "Sirva somente a pasta web em loopback e abra-a em um Chromium isolado.", "Passe o payload a renderPortfolioView e atribua o resultado a app-root.innerHTML, como faz PrometeusApp.render.", "Inspecione window.__audit_xss; o valor observado é 1."],
        "O handler do elemento img é interpretado e altera window.__audit_xss para 1 na origem do portal.",
        "Aplicar escapeHtml a todos os metadados interpolados no portfólio, inclusive atributos, ou renderizar textos com textContent. Validar URLs separadamente e remover handlers inline/unsafe-inline após adequar a SPA. Acrescentar regressão de renderização com dados retornados por loadCompletedAnalyses.",
        "medium", "medium", "medium", "Execução no Chromium confirmada; persistência/listagem/filtro confirmados em fixture válida. A conclusão pelo workflow real não foi executada e é pré-condição explícita.",
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    conn = sqlite3.connect(ROOT / ".security" / "scan.db")
    conn.row_factory = sqlite3.Row
    if conn.execute("SELECT status FROM scans WHERE id=?", (SCAN_ID,)).fetchone()["status"] == "sealed":
        raise SystemExit("Scan already sealed; immutable artifacts must not be overwritten.")
    for item in FINDINGS:
        if not conn.execute("SELECT id FROM findings WHERE scan_id=? AND title=?", (SCAN_ID, item["title"])).fetchone():
            conn.execute("INSERT INTO findings (id,scan_id,title,severity,category,status,file_path,line_number,description,evidence,created_at,notes) VALUES (?,?,?,?,?,'open',?,?,?,?,?,?)", (
                str(uuid.uuid4()), SCAN_ID, item["title"], item["severity"]["overall_severity"], "access-control" if "API permite" in item["title"] else "stored-xss",
                item["trace"][-1]["file"], item["trace"][-1]["line"], item["description"],
                "security-probe-output.json; browser-xss-output.json", datetime.now(timezone.utc).isoformat(), json.dumps(item, ensure_ascii=False),
            ))
        else:
            conn.execute("UPDATE findings SET notes=?,line_number=? WHERE scan_id=? AND title=?", (json.dumps(item, ensure_ascii=False), item["trace"][-1]["line"], SCAN_ID, item["title"]))
    conn.commit()
    rows = conn.execute("SELECT notes FROM findings WHERE scan_id=? ORDER BY CASE severity WHEN 'high' THEN 1 ELSE 2 END", (SCAN_ID,)).fetchall()
    findings = [json.loads(row["notes"]) for row in rows]
    if args.seal:
        conn.execute("UPDATE scans SET sealed_at=?,status='sealed' WHERE id=?", (datetime.now(timezone.utc).isoformat(), SCAN_ID))
        conn.commit()
    filename = "findings.json" if args.seal else "findings-draft.json"
    target = HERE / filename
    target.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.seal:
        print(f"Draft: {target}; pending independent verification")
        return
    summary = {"scan_id": SCAN_ID, "date": "2026-11-04", "counts": {"high": 1, "medium": 1}, "method": "SAST + ASGI isolado + Chromium loopback; sem produção", "findings": findings}
    (HERE / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    cards = []
    for item in findings:
        sev = item["severity"]["overall_severity"]
        trace = "\n".join(f"{t['file']}:{t['line']} ({t['scope']}) — {t['description']}" for t in item["trace"])
        cards.append(f"<article class='finding {sev}' data-severity='{sev}'><h3><span class='badge'>{sev.upper()}</span> {html.escape(item['title'])}</h3><p>{html.escape(item['description'])}</p><p>Confiança: {item['confidence']['score']}. {html.escape(item['confidence']['reason'])}</p><details><summary>Evidência e rastreio</summary><pre>{html.escape(trace)}</pre><pre>{html.escape(json.dumps(item['execution'], ensure_ascii=False, indent=2))}</pre></details><details><summary>Pré-condições</summary><ul>{''.join('<li>'+html.escape(c['description'])+'</li>' for c in item['conditions'])}</ul></details><details><summary>Remediação</summary><p>{html.escape(item['remediation']['strategy'])}</p></details></article>")
    evidence = json.loads((HERE / "security-probe-output.json").read_text(encoding="utf-8"))
    browser = json.loads((HERE / "browser-xss-output.json").read_text(encoding="utf-8"))
    doc = """<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Auditoria de segurança — Prometeus</title><style>body{font:16px system-ui;background:#0f172a;color:#f1f5f9;max-width:1150px;margin:auto;padding:2rem;line-height:1.6}p,li,dd{color:#cbd5e1}h2{border-bottom:1px solid #475569;margin-top:2rem}article,.card{background:#1e293b;border-radius:8px;padding:1rem;margin:1rem 0;border-left:4px solid #64748b}.high{border-color:#ea580c}.medium{border-color:#ca8a04}.summary{display:flex;flex-wrap:wrap;gap:1rem}.card{min-width:110px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#020617;padding:1rem;border-radius:6px}button{background:#334155;color:white;border:1px solid #64748b;padding:.6rem;cursor:pointer}summary{cursor:pointer;font-weight:600}table{width:100%;border-collapse:collapse}th,td{border:1px solid #475569;padding:.6rem;text-align:left}.badge{font-size:.8rem}footer{margin-top:3rem;border-top:1px solid #475569;padding-top:1rem}a{color:#93c5fd}</style><h1>Auditoria de segurança — Prometeus</h1><dl><dt>Repositório</dt><dd>Prometeus — Inteligência para Produtos Educacionais</dd><dt>Data</dt><dd>04/11/2026</dd><dt>Alvo</dt><dd>Fonte local; banco e configuração temporários; web em 127.0.0.1:18777</dd><dt>Metodologia</dt><dd>SAST + chamadas ASGI isoladas + Chromium em loopback; validação adversarial root e verificação independente. Produção não testada.</dd></dl><h2>Resumo</h2><div class='summary'><div class='card'>Critical: 0</div><div class='card high'>High: 1</div><div class='card medium'>Medium: 1</div><div class='card'>Low: 0</div><div class='card'>Info: 0</div></div><p>Não há base para considerar o sistema seguro para exposição sem restrição. A API permite leitura e alterações administrativas sem principal, e o portfólio interpreta metadados como HTML. Os testes não acessaram segredos reais, fornecedores pagos ou o stack ativo. Firewall/proxy real e conclusão de análise maliciosa por LLM são limitações explícitas.</p><h2>Achados</h2><nav>FILTERS</nav>CARDS<h2>Testes ativos locais</h2><p>security_probe.py usa SQLite em memória e arquivo temporário. Resultado real:</p><pre>EVIDENCE</pre><p>Browser isolado, renderer real:</p><pre>BROWSER</pre><h2>Resultados negativos e controles identificados</h2><table><tr><th>Controle</th><th>Resultado e limite</th></tr><tr><td>Banco/cache no Compose</td><td>PostgreSQL e Redis sem porta publicada, em rede internal; não garante proteção da API.</td></tr><tr><td>Links e texto de dossiê</td><td>safeUrl/escapeHtml usados em dossier-view e evidence-drawer; o achado refere-se ao portfólio.</td></tr><tr><td>Injeção de novas linhas em configuração</td><td>_persist_env_updates rejeita CR/LF antes de gravar. Não remove necessidade de autorização.</td></tr><tr><td>URLs de coleta</td><td>Validação rejeita IPs literais não globais, userinfo e sufixos internos. DNS rebinding/redirect não testados.</td></tr><tr><td>OAuth e webhook</td><td>PKCE/nonce/state/JWKS e HMAC estão presentes; não foi comprovado bypass próprio desses mecanismos.</td></tr><tr><td>Segredos no repositório</td><td>.env, /var, *.pem e *.key são ignorados; nenhum segredo real foi consultado nesta auditoria.</td></tr></table><h2>Cobertura e hipóteses não promovidas a achado</h2><p>Inspecionados: REST/MCP, controle de acesso, tenant, destinos LLM, OAuth, webhook, upload, sanitização, frontend e deployment. Não confirmados: SSRF por DNS/redirect, zip bomb e falhas adicionais de OAuth. Multi-tenancy compartilhado não é o deployment inicial; idempotência cross-tenant permanece na auditoria de confiabilidade. Sem análise de CVEs/advisories; não se afirma ausência de dependências vulneráveis.</p><h2>Remediação prioritária</h2><table><tr><th>Ordem</th><th>Ação</th><th>Esforço</th><th>Impacto</th></tr><tr><td>1</td><td>Autenticação, escopos e principal para decisões/configuração; restringir portas</td><td>Médio</td><td>Impede leitura e gravações não autorizadas</td></tr><tr><td>2</td><td>Escape completo no portfólio e regressão de renderização com fixture completed/verified</td><td>Baixo</td><td>Impede execução de HTML persistido</td></tr></table><script>function filterFindings(s){document.querySelectorAll('.finding').forEach(x=>x.hidden=s!=='all'&&x.dataset.severity!==s)}</script><footer>Generated by <strong>security-specialist</strong> skill by <a href='https://github.com/fabricioctelles/skills'>github.com/fabricioctelles/skills</a></footer></html>"""
    filters = " ".join(f"<button onclick=\"filterFindings('{s}')\">{label}</button>" for s, label in (("all", "Todos"), ("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low"), ("info", "Info")))
    doc = doc.replace("FILTERS", filters).replace("CARDS", "".join(cards)).replace("EVIDENCE", html.escape(json.dumps(evidence, ensure_ascii=False, indent=2))).replace("BROWSER", html.escape(json.dumps(browser, ensure_ascii=False, indent=2)))
    (HERE / "security-report.html").write_text(doc, encoding="utf-8")
    hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("findings.json", "report.json", "security-report.html", "architecture.md", "security-probe-output.json", "browser-xss-output.json", "independent-verification.md")}
    (HERE / "manifest.json").write_text(json.dumps({"scan_id": SCAN_ID, "sealed_at": datetime.now(timezone.utc).isoformat(), "sha256": hashes}, indent=2), encoding="utf-8")
    print(f"Sealed scan {SCAN_ID}: 1 high, 1 medium; {HERE}")


if __name__ == "__main__":
    main()
