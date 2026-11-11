import pytest

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.synthesize_dossier import (
    DossierSynthesisService,
    DossierVerificationError,
)
from prometeus.domain.dossiers import (
    DossierClaim,
    DossierFactItem,
    DossierFacts,
    VerificationStatus,
)
from prometeus.infrastructure.llm.client import OpenAIGenerativeClient
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def test_complete_reading_reaches_writer_and_only_literal_quotes_support_numbers():
    reading = {
        "observations": [
            {
                "pointer": "/syllabus",
                "quotes": ["Curso com 24 horas"],
                "analysis": "Interpretação não verificada com 9999 alunos.",
            },
        ],
        "manifest": {"total_fragments": 555},
    }
    item = DossierFactItem(
        evidence_id="source",
        source_type="OFFER",
        title="Oferta",
        source_reading=reading,
    )
    facts = DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Profissionais",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=0,
        coverage_score=0,
        confidence_score=0,
        items=[item],
    )
    assert item.to_dict()["source_reading"] == reading
    valid = DossierClaim(
        claim_id="valid", statement="A oferta declara 24 horas.", evidence_ids=["source"]
    )
    assert (
        DossierVerifier().verify_claim(valid, facts).verification_status
        == VerificationStatus.VERIFIED
    )
    for number in [9999, 555]:
        invalid = DossierClaim(
            claim_id="invalid",
            statement=f"A oferta possui {number} alunos.",
            evidence_ids=["source"],
        )
        assert (
            DossierVerifier().verify_claim(invalid, facts).verification_status
            != VerificationStatus.VERIFIED
        )


@pytest.mark.asyncio
async def test_orphan_and_failed_dataset_context_reaches_writer_without_market_admission():
    facts = DossierFacts(
        analysis_id="a", course_name="Curso", target_audience="Profissionais",
        recommendation="INSUFFICIENT_EVIDENCE", viability_score=0, coverage_score=0,
        confidence_score=0, collection_reading_context={"records":[{
            "provider_run_id":"failed-run", "run_status":"FAILED",
            "reading":{"observations":[{"quotes":["CAMPO EXCLUSIVO DO ARCHIVE"], "analysis":"Contexto técnico pendente de qualificação."}]},
        }]},
    )
    before = facts.compute_facts_hash()
    assert "failed-run" not in facts.get_all_known_ids()

    class CapturingWriter(OpenAIGenerativeClient):
        async def generate_structured(self, prompt, *, schema, system_prompt=None):
            self.captured = prompt
            raise RuntimeError("stop after input capture")

    writer = CapturingWriter(base_url="https://example.invalid/v1",api_key="test",model="test")
    with pytest.raises(RuntimeError, match="stop after input capture"):
        await writer.synthesize_dossier(facts)
    assert "CAMPO EXCLUSIVO DO ARCHIVE" in writer.captured
    facts.collection_reading_context["records"][0]["run_status"] = "SUCCEEDED"
    assert facts.compute_facts_hash() != before


@pytest.mark.asyncio
@pytest.mark.parametrize("context", [{}, {"complete": True, "records": []}])
async def test_missing_current_archive_blocks_synthesis_even_when_old_records_were_read(context):
    facts = DossierFacts(
        analysis_id="a", course_name="Curso", target_audience="Profissionais",
        recommendation="INSUFFICIENT_EVIDENCE", viability_score=0, coverage_score=0,
        confidence_score=0, collection_reading_context=context,
        analysis_audit={"reading":{"complete":False,"legacy_runs_without_archive":1}},
    )

    class UncalledWriter(FakeGenerativeModel):
        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            raise AssertionError("A pending source must block before contacting the writer")

    service = DossierSynthesisService(None, UncalledWriter())
    async def build_facts(_):
        return facts
    service.build_facts = build_facts
    with pytest.raises(DossierVerificationError) as caught:
        await service.synthesize_and_verify("a")
    assert caught.value.report["gate"] == "collection_reading"
    assert not caught.value.can_revise
