"""Testes unitários do modelo canônico de ecossistema competitivo e Radar Setorial por tenant."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.domain.configuration import (
    AppSettings,
    ConfigurationError,
    TenantConfig,
    load_tenant_config,
)


def test_ens_tenant_config_loads_ten_competitors_and_ten_sector_insurers() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    assert len(cfg.ecosystem.competitors) == 10
    assert len(cfg.ecosystem.sector_radar) == 10

    comp_ids = {c.id for c in cfg.ecosystem.competitors}
    assert comp_ids == {
        "conhecer-seguros",
        "fgv",
        "ibmec",
        "fipecafi",
        "fia",
        "insper",
        "estacio",
        "esa-oab",
        "fiap",
        "alura",
    }

    primary_insurers = {s.id for s in cfg.ecosystem.sector_radar if s.priority == "primary"}
    assert primary_insurers == {
        "porto-seguro",
        "bradesco-seguros",
        "tokio-marine",
        "allianz-seguros",
        "hdi-seguros",
    }

    by_id = {s.id: s for s in cfg.ecosystem.sector_radar}
    assert by_id["mapfre"].social.linkedin_scope == "global"
    assert by_id["zurich-seguros"].social.linkedin_scope == "global"
    assert by_id["itau-seguros"].social.instagram_handle is None
    assert by_id["brasilseg-bb"].social.instagram_handle is None
    assert by_id["yelum-seguros"].social.instagram_handle is None
    assert by_id["hdi-seguros"].social.instagram_handle is None


def test_infnet_tenant_without_ecosystem_remains_backward_compatible() -> None:
    cfg = load_tenant_config(Path("config/tenants/infnet.example.yaml"))
    assert cfg.ecosystem.competitors == []
    assert cfg.ecosystem.sector_radar == []
    assert cfg.ecosystem.radar_ttl_hours == 168


def test_rejects_domain_collision_between_own_competitors_and_sector_radar() -> None:
    with pytest.raises((ConfigurationError, ValueError)):
        TenantConfig.model_validate(
            {
                "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
                "ecosystem": {
                    "competitors": [
                        {
                            "id": "c1",
                            "name": "C1",
                            "category": "direct_specialist",
                            "domains": ["portoseguro.com.br"],
                        }
                    ],
                    "sector_radar": [
                        {"id": "s1", "name": "Porto", "domains": ["www.portoseguro.com.br"]}
                    ],
                },
            }
        )

    with pytest.raises((ConfigurationError, ValueError)):
        TenantConfig.model_validate(
            {
                "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
                "ecosystem": {
                    "competitors": [
                        {
                            "id": "c1",
                            "name": "ENS Clone",
                            "category": "direct_specialist",
                            "domains": ["ens.edu.br"],
                        }
                    ],
                },
            }
        )


def test_rejects_non_https_social_or_portal_urls() -> None:
    with pytest.raises((ConfigurationError, ValueError)):
        TenantConfig.model_validate(
            {
                "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
                "ecosystem": {
                    "competitors": [
                        {
                            "id": "c1",
                            "name": "C1",
                            "category": "direct_specialist",
                            "domains": ["exemplo.edu.br"],
                            "portal_url": "http://exemplo.edu.br/pos",
                        }
                    ],
                },
            }
        )


@pytest.mark.asyncio
async def test_create_analysis_freezes_ecosystem_into_institution_context() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    settings = AppSettings(
        INSTITUTION_CONFIG_PATH="config/tenants/ens.example.yaml",
        SCORING_PROFILE_PATH="config/scoring/portfolio-v2.yaml",
    )
    use_case = CreateAnalysisUseCase(session=session, settings=settings)
    use_case.repository = AsyncMock()

    await use_case.execute(
        CreateAnalysisCommand(
            tenant_id="ens",
            course_name="MBA em IA Aplicada a Seguros",
            proposal_data={"level": "MBA Executivo"},
            idempotency_key="idem-eco-1",
            correlation_id="corr-eco-1",
        )
    )

    saved_analysis = use_case.repository.save.call_args.args[0]
    inst_ctx = saved_analysis.proposal_data["_institution_context"]
    assert len(inst_ctx["competitors"]) == 10
    assert len(inst_ctx["sector_radar"]) == 10



@pytest.mark.asyncio
async def test_create_analysis_isolates_infnet_from_ens_ecosystem() -> None:
    from prometeus.application.run_course_analysis import RunCourseAnalysis
    from prometeus.domain.analyses import Analysis

    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    settings = AppSettings(
        INSTITUTION_CONFIG_PATH="config/tenants/ens.example.yaml",
        SCORING_PROFILE_PATH="config/scoring/portfolio-v2.yaml",
    )
    use_case = CreateAnalysisUseCase(session=session, settings=settings)
    use_case.repository = AsyncMock()

    await use_case.execute(
        CreateAnalysisCommand(
            tenant_id="infnet",
            course_name="Bootcamp de Engenharia de Dados",
            proposal_data={"level": "Extensão"},
            idempotency_key="idem-infnet-1",
            correlation_id="corr-infnet-1",
        )
    )

    saved_analysis = use_case.repository.save.call_args.args[0]
    inst_ctx = saved_analysis.proposal_data["_institution_context"]
    assert inst_ctx["id"] == "infnet"
    assert inst_ctx["name"] == "Instituto Infnet de Tecnologia"
    assert "ens.edu.br" not in inst_ctx["domains"]
    assert inst_ctx["competitors"] == []
    assert inst_ctx["sector_radar"] == []

    snap_kwargs = use_case.repository.save_config_snapshot.call_args.kwargs
    assert snap_kwargs["tenant_config_snapshot"]["institution"]["id"] == "infnet"

    # Guard against mismatched snapshot in RunCourseAnalysisUseCase
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    mismatched_snapshot = MagicMock()
    mismatched_snapshot.tenant_config_snapshot = ens_cfg.model_dump(mode="json")
    infnet_analysis = Analysis.create(
        tenant_id="infnet",
        course_name="Bootcamp de Engenharia de Dados",
        proposal_data={"_institution_context": inst_ctx},
        correlation_id="corr-infnet-2",
    )
    runner = RunCourseAnalysis.__new__(RunCourseAnalysis)
    runner.settings = settings
    eco, resolved_ctx = runner._resolve_ecosystem_and_context(infnet_analysis, mismatched_snapshot)
    assert eco.competitors == []
    assert eco.sector_radar == []
    assert resolved_ctx["id"] == "infnet"


def test_domains_preserve_primary_yaml_declaration_order_and_reject_duplicate_sector_radar_domains() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    fgv = next(c for c in cfg.ecosystem.competitors if c.id == "fgv")
    assert fgv.domains[0] == "fgv.br"

    with pytest.raises((ConfigurationError, ValueError), match="duplica domínio"):
        TenantConfig.model_validate(
            {
                "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
                "ecosystem": {
                    "sector_radar": [
                        {"id": "s1", "name": "Seg 1", "domains": ["seguradora-x.com.br"]},
                        {"id": "s2", "name": "Seg 2", "domains": ["www.seguradora-x.com.br"]},
                    ]
                },
            }
        )
