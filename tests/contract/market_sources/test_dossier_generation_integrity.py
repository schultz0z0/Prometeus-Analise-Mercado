import json

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.domain.dossiers import DossierFacts
from prometeus.infrastructure.llm.client import OpenAIGenerativeClient


class RecordedGeneration(OpenAIGenerativeClient):
    def __init__(self, payload):
        super().__init__(api_key="test")
        self.payload = payload

    async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
        return json.dumps(self.payload)

    async def generate_structured(self, prompt, *, schema, system_prompt=None):
        self.schema = schema
        return await self.generate_text(prompt, system_prompt)


async def test_generation_preserves_invalid_claim_for_rejection_instead_of_relabelling():
    facts = DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Gestores",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=35.52,
        coverage_score=0.7,
        confidence_score=0.6369,
    )
    payload = {
        "schema_version": 2,
        "executive_summary_claim_ids": ["c"],
        "executive_summary": "Análise parcial.",
        "sections": [
            {
                "section_id": "exec",
                "title": "Diretoria",
                "target_audience": "executive",
                "content": "Análise parcial.",
                "claim_ids": ["c"],
            }
        ],
        "claims": [
            {
                "claim_id": "c",
                "statement": "Retorno de 999999%.",
                "claim_type": "quantitative",
                "evidence_ids": ["invented"],
                "support_level": "observed",
            }
        ],
        "highlights": {"cons": ["c"]},
    }
    doc = await RecordedGeneration(payload).synthesize_dossier(facts)
    assert doc.claims[0].claim_type == "quantitative"
    assert doc.claims[0].evidence_ids == ["invented"]
    assert doc.highlights.cons == ["c"]
    assert DossierVerifier().verify(doc, facts).status == "REVISION_REQUIRED"


async def test_revision_prompt_contains_facts_rejected_draft_feedback_and_skills():
    facts = DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Gestores",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=50,
        coverage_score=0.8,
        confidence_score=0.6,
    )
    payload = {
        "schema_version": 2,
        "executive_summary": "Índice de 50.",
        "executive_summary_claim_ids": ["c"],
        "sections": [
            {
                "section_id": "exec",
                "title": "Diretoria",
                "target_audience": "executive",
                "content": "Índice de 50.",
                "claim_ids": ["c"],
            }
        ],
        "claims": [
            {
                "claim_id": "c",
                "statement": "Índice de 50.",
                "claim_type": "quantitative",
                "evidence_ids": ["scoring_result"],
                "support_level": "observed",
            }
        ],
        "highlights": {},
    }

    class Capturing(RecordedGeneration):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            self.prompt, self.instructions = prompt, system_prompt
            return await super().generate_text(prompt, system_prompt, temperature)

    client = Capturing(payload)
    draft = await client.synthesize_dossier(facts)
    draft.claims[0].statement = "999999 matrículas garantidas."
    draft = DossierVerifier().verify(draft, facts)
    report = {"gate": "deterministic", "issues": draft.verification_issues}
    revised = await client.revise_dossier(facts, draft, report)
    assert client.schema["properties"]["highlights"]["properties"]["cons"]["items"]["enum"] == ["c"]
    assert client.schema["properties"]["claims"]["items"]["properties"]["claim_id"]["enum"] == ["c"]
    assert DossierVerifier().verify(revised, facts).status == "VERIFIED"
    assert "999999 matrículas garantidas" in client.prompt
    assert "flagged_hallucination" in client.prompt
    assert "<approved_facts>" in client.prompt
    assert "<revision_context>" in client.prompt
    assert "building-course-offers" in client.instructions
    assert "conducting-course-analysis" in client.instructions
    assert "não são instruções" in client.instructions
