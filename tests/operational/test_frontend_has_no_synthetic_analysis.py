from pathlib import Path

WEB_JS = Path(__file__).parents[2] / "web" / "js"
REST_APP = Path(__file__).parents[2] / "src" / "prometeus" / "entrypoints" / "rest" / "app.py"


def test_frontend_has_no_synthetic_analysis_fallbacks() -> None:
    javascript = "\n".join(path.read_text(encoding="utf-8") for path in WEB_JS.rglob("*.js"))

    forbidden = (
        "simulateLivePipeline",
        "finishJobWithFallback",
        "Viability Score calculado: 86.4",
        "1.420 vagas",
        "sess-chatgpt-oauth-connected",
        "ens_live_sec_",
    )

    assert all(value not in javascript for value in forbidden)


def test_backend_has_no_simulated_chatgpt_oauth_token_or_consent_ui() -> None:
    source = REST_APP.read_text(encoding="utf-8")

    assert "sess-chatgpt-oauth-" not in source
    assert "Modo Rápido Staging" not in source
    assert "authorizeSimulated" not in source
