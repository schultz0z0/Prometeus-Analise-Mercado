from pathlib import Path


def test_worker_contains_no_synthetic_market_or_dossier_fallbacks() -> None:
    source = Path("src/prometeus/workers/tasks.py").read_text(encoding="utf-8")

    forbidden_fragments = {
        "viability_score = 86.4",
        '"open_jobs_count": 1420',
        '"active_ads": 22',
        '"trend_yoy": "+88%"',
        "Gerando Dossiê Executivo Estruturado determinístico",
        "Continuando com dados de mercado calibrados",
        'model_name="prometeus-factual-v1"',
    }

    found = sorted(fragment for fragment in forbidden_fragments if fragment in source)
    assert found == [], f"Fallbacks sintéticos encontrados no runtime: {found}"
