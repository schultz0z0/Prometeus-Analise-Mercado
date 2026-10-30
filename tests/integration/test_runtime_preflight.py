from prometeus.application.runtime_preflight import validate_runtime_preflight
from prometeus.domain.configuration import AppSettings


def make_settings(**overrides: object) -> AppSettings:

    values: dict[str, object] = {
        "APP_ENV": "development",
        "AI_MODE": "traditional",
        "GEN_LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-live-test",
        "APIFY_TOKEN": "apify-live-test",
        "APIFY_ACTOR_GOOGLE_SEARCH": "owner/google-search@1.0.0",
        "APIFY_ACTOR_WEB_CRAWLER": "owner/web-crawler@1.0.0",
        "APIFY_ACTOR_META_AD_LIBRARY": "owner/meta-ads@1.0.0",
        "APIFY_ACTOR_LINKEDIN": "owner/linkedin@1.0.0",
        "APIFY_ACTOR_LINKEDIN_JOBS": "owner/linkedin-jobs@1.0.0",
        "APIFY_ACTOR_INSTAGRAM": "owner/instagram@1.0.0",
        "APIFY_ACTOR_TIKTOK": "owner/tiktok@1.0.0",
        "APIFY_ACTOR_YOUTUBE_COMMENTS": "owner/youtube@1.0.0",
        "CHATGPT_CREDENTIALS_PATH": "var/test-non-existent-creds.json",
    }

    values.update(overrides)

    return AppSettings(_env_file=None, **values)


def test_preflight_accepts_traditional_llm_and_configured_live_sources() -> None:

    report = validate_runtime_preflight(make_settings())

    assert report.ready is True

    assert report.ai_mode == "traditional"

    assert report.errors == []

    assert "institutional_history" in report.synthetic_sources

    assert report.synthetic_sources == ["institutional_history"]


def test_preflight_rejects_missing_real_llm_credentials() -> None:

    report = validate_runtime_preflight(make_settings(OPENAI_API_KEY="", CHATGPT_ACCESS_TOKEN=""))

    assert report.ready is False

    assert any(issue.code == "llm_credentials_missing" for issue in report.errors)


def test_preflight_rejects_chatgpt_session_token_without_supported_adapter() -> None:

    report = validate_runtime_preflight(
        make_settings(
            GEN_LLM_PROVIDER="chatgpt_oauth",
            OPENAI_API_KEY="",
            CHATGPT_ACCESS_TOKEN="session-token-is-not-an-api-key",
        )
    )

    assert report.ready is False

    assert any(issue.code == "llm_credentials_missing" for issue in report.errors)


def test_preflight_rejects_missing_required_actor_without_revealing_tokens() -> None:

    report = validate_runtime_preflight(make_settings(APIFY_ACTOR_META_AD_LIBRARY=""))

    assert report.ready is False

    issue = next(issue for issue in report.errors if issue.code == "actor_missing")

    assert issue.source == "meta_ads_library"

    assert "apify-live-test" not in issue.message


def test_preflight_auto_mode_uses_traditional_llm_when_jev_is_disabled() -> None:

    report = validate_runtime_preflight(make_settings(AI_MODE="auto", TYPESAFE_API_KEY=""))

    assert report.ready is True

    assert report.ai_mode == "traditional"

    assert report.jev_enabled is False


async def test_settings_reports_effective_traditional_mode_even_with_jev_credentials(monkeypatch):
    import importlib

    rest = importlib.import_module("prometeus.entrypoints.rest.app")
    settings = make_settings(AI_MODE="traditional", TYPESAFE_API_KEY="unused-test-key")
    monkeypatch.setattr(rest, "AppSettings", lambda: settings)
    response = await rest.get_settings()
    assert response["is_jev_configured"] is True
    assert response["mode"].startswith("100% TRADITIONAL")
    assert response["ai_mode"] == "traditional"
    assert response["jev_enabled"] is False
