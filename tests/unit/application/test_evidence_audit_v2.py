from prometeus.application.evidence_audit import summarize_evidence


def test_audit_distinguishes_context_from_excluded_and_explains_each_loss():
    rows = [
        {
            "id": "job1",
            "source_name": "apify_linkedin_jobs",
            "sanitized_data": {
                "_qualification": {"accepted": True, "use_for": ["employability", "curriculum"]}
            },
        },
        {
            "id": "own",
            "source_name": "apify_meta_ads_library",
            "sanitized_data": {
                "_qualification": {
                    "accepted": False,
                    "context_only": True,
                    "reason": "Anúncio da própria instituição",
                    "exclusion_codes": ["own_institution"],
                }
            },
        },
        {
            "id": "wrong",
            "source_name": "apify_linkedin_jobs",
            "sanitized_data": {
                "_qualification": {"accepted": False, "reason": "Localização fora do escopo"}
            },
        },
    ]
    summary = summarize_evidence(rows, used_ids={"job1"})
    assert summary["collected_records"] == 3
    assert summary["used_in_score_records"] == 1
    assert summary["context_records"] == 1
    assert summary["excluded_records"] == 1
    assert summary["sources"]["apify_linkedin_jobs"]["reasons"]["Localização fora do escopo"] == 1
