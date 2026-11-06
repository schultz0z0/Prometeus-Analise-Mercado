import asyncio
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.economics_service import CourseEconomicsService
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.configuration import AppSettings
from prometeus.domain.dossiers import DossierClaim
from prometeus.domain.economics import CourseEconomicsInput
from prometeus.infrastructure.db.models import AnalysisModel, DossierModel
from sqlalchemy import select


async def main():
    analysis_id='dffd0359-4a40-4cc4-be00-fc5bb74bf687'
    engine=create_async_engine(AppSettings().DATABASE_URL)
    async with async_sessionmaker(engine,expire_on_commit=False)() as session:
        facts=await DossierSynthesisService(session,None).build_facts(analysis_id)
        observed='O resultado calculado indica evidências insuficientes para recomendar o lançamento e índice de viabilidade experimental de 30,0 em 100, sujeito a calibração; não é aprovação institucional, probabilidade de sucesso ou projeção de retorno.'
        verifier=DossierVerifier()
        checked=verifier.verify_claim(DossierClaim(statement=observed,evidence_ids=['scoring_result']),facts)
        assert checked.verification_status=='verified'
        for statement in ['A confiança é 100%.','O índice é 30 e há 30 em 100 empresas interessadas.','O índice é 30 em 100 milhões de matrículas.']:
            assert verifier.verify_claim(DossierClaim(statement=statement,evidence_ids=['scoring_result']),facts).verification_status=='flagged_hallucination'
        dossier=await session.scalar(select(DossierModel).where(DossierModel.analysis_id==analysis_id))
        analysis=await session.get(AnalysisModel,analysis_id)
        assert analysis.status=='COMPLETED' and dossier.status=='VERIFIED'
        inputs=CourseEconomicsInput.model_validate(analysis.proposal_data['economics'])
        canonical=CourseEconomicsService().evaluate(inputs)
        rendered=dossier.presentation['economics']
        assert rendered['basis']=='simulation_from_explicit_assumptions'
        assert len(rendered['input_sources'])==13
        assert all(s['students']<=inputs.max_capacity for s in rendered['scenarios'])
        base=next(s for s in rendered['scenarios'] if s['name']=='Base')
        assert Decimal(base['net_profit'])==canonical.scenarios['base'].net_result_brl==Decimal('11970.94')
        assert sum(Decimal(x['net_cash_flow_brl']) for x in rendered['monthly_cash_flow'])==canonical.scenarios['base'].net_result_brl
        report={'analysis_id':analysis_id,'dossier_status':dossier.status,'recommendation':analysis.recommendation,'presentation_contract_version':dossier.presentation['contract_version'],'explicit_financial_inputs':13,'scenarios_within_capacity':True,'cash_flow_reconciles':True,'base_simulated_profit_brl':str(canonical.scenarios['base'].net_result_brl),'actual_first_draft_denominator_now_supported':True,'invented_percentages_and_market_denominators_rejected':True,'published_dossier_unchanged':True}
    await engine.dispose()
    print(json.dumps(report))


asyncio.run(main())
