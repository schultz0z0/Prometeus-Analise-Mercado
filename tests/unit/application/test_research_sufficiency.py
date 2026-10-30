from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature


def test_missing_critical_signals_trigger_gaps_but_zero_observed_is_not_missing():
    from prometeus.application.research_sufficiency import research_gaps

    features = EvidenceFeatureSet(
        features={
            "open_jobs_count": VerifiedFeature(
                "open_jobs_count", 0, ["query-observation"], "observed_empty"
            )
        }
    )
    gaps = research_gaps(features)
    assert any("preço" in gap.lower() for gap in gaps)
    assert any("busca" in gap.lower() for gap in gaps)
    assert not any("vaga" in gap.lower() for gap in gaps)
