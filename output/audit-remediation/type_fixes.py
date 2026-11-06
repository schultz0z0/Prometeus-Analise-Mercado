from pathlib import Path

for name in ['src/prometeus/application/research_scope.py', 'src/prometeus/application/sector_radar.py']:
    path=Path(name)
    source=path.read_text(encoding='utf-8')
    source=source.replace('social = entry.get("social") if isinstance(entry.get("social"), dict) else {}', 'raw_social = entry.get("social")\n        social = raw_social if isinstance(raw_social, dict) else {}')
    source=source.replace('social = actor.get("social") if isinstance(actor.get("social"), dict) else {}', 'raw_social = actor.get("social")\n    social = raw_social if isinstance(raw_social, dict) else {}')
    source=source.replace('ctx = {', 'ctx: dict[str, object] = {')
    path.write_text(source,encoding='utf-8')
path=Path('src/prometeus/application/ecosystem_presentation.py')
source=path.read_text(encoding='utf-8').replace('    institution_ctx = (\n        dict(proposal.get("_institution_context"))\n        if isinstance(proposal.get("_institution_context"), dict)\n        else {}\n    )', '    raw_ctx = proposal.get("_institution_context")\n    institution_ctx = dict(raw_ctx) if isinstance(raw_ctx, dict) else {}')
path.write_text(source,encoding='utf-8')
path=Path('src/prometeus/application/run_course_analysis.py')
source=path.read_text(encoding='utf-8').replace('        raw_ctx = (\n            dict(analysis.proposal_data.get("_institution_context"))\n            if isinstance((analysis.proposal_data or {}).get("_institution_context"), dict)\n            else {}\n        )', '        raw_value = (analysis.proposal_data or {}).get("_institution_context")\n        raw_ctx = dict(raw_value) if isinstance(raw_value, dict) else {}')
path.write_text(source,encoding='utf-8')
