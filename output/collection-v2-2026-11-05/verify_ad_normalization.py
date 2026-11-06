import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.evidence_projection import build_qualification_context
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.apify.normalizers import normalize_ad
from prometeus.infrastructure.db.models import MarketEvidenceModel


async def main():
    engine = create_async_engine(AppSettings().DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        rows = list((await session.execute(select(MarketEvidenceModel).where(
            MarketEvidenceModel.analysis_id == '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86',
            MarketEvidenceModel.source_name == 'apify_meta_ads_library',
        ))).scalars())
        observed_body = projected_body = carousel = projected_carousel = 0
        for row in rows:
            raw = row.sanitized_data
            snapshot = raw.get('snapshot') or {}
            body = snapshot.get('body') or {}
            ad = normalize_ad(raw, url=row.source_url)
            context = build_qualification_context(raw, 'PAID_COMPETITION', url=row.source_url)
            if isinstance(body, dict) and isinstance(body.get('text'), str) and body['text'].strip():
                observed_body += 1
                assert ad.ad_text.value == body['text'].strip()
                assert context['ad_copy'] and body['text'].strip().startswith(context['ad_copy'].removesuffix('...'))
                projected_body += 1
            if snapshot.get('cards'):
                carousel += 1
                assert context.get('creative_cards')
                projected_carousel += 1
            assert ad.ad_id
            assert len(json.dumps(context, ensure_ascii=False)) <= 14000
        report = {'source_rows': len(rows), 'observed_snapshot_bodies': observed_body, 'projected_snapshot_bodies': projected_body,
                  'observed_carousels': carousel, 'projected_carousels': projected_carousel,
                  'all_ids_present': True, 'all_context_budgets_valid': True, 'no_paid_runs_started': True}
        Path('/app/var/ad-normalization-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    await engine.dispose()


asyncio.run(main())
