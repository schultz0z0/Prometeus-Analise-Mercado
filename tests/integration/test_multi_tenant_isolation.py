"""Testes de integração para isolamento estrito de dados entre tenants e resolução white-label (Fase 09)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import load_tenant_config
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import AnalysisModel, Base
from prometeus.infrastructure.institutional.ens.client import ENSInstitutionalAdapter
from prometeus.infrastructure.institutional.factory import create_institutional_adapter
from prometeus.infrastructure.institutional.infnet.client import InfnetInstitutionalAdapter
from prometeus.infrastructure.institutional.mock import MockInstitutionalAdapter


@pytest.fixture
async def multi_tenant_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_data_isolation(multi_tenant_session: AsyncSession) -> None:
    repo = AnalysisRepository(multi_tenant_session)

    # Cria análises para a ENS
    ens_1 = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Gestão de Seguros",
        correlation_id="corr-ens-1",
    )
    ens_2 = Analysis.create(
        tenant_id="ens",
        course_name="Certificação em Subscrição de Riscos",
        correlation_id="corr-ens-2",
    )

    # Cria análises para o Infnet
    inf_1 = Analysis.create(
        tenant_id="infnet",
        course_name="Bootcamp em Engenharia de Software e IA",
        correlation_id="corr-inf-1",
    )

    await repo.save(ens_1)
    await repo.save(ens_2)
    await repo.save(inf_1)
    await multi_tenant_session.commit()

    # Validação 1: Busca apenas análises do tenant 'ens'
    stmt_ens = select(AnalysisModel).where(AnalysisModel.tenant_id == "ens")
    res_ens = (await multi_tenant_session.execute(stmt_ens)).scalars().all()
    assert len(res_ens) == 2
    for r in res_ens:
        assert r.tenant_id == "ens"
        assert "Bootcamp" not in r.course_name

    # Validação 2: Busca apenas análises do tenant 'infnet'
    stmt_inf = select(AnalysisModel).where(AnalysisModel.tenant_id == "infnet")
    res_inf = (await multi_tenant_session.execute(stmt_inf)).scalars().all()
    assert len(res_inf) == 1
    assert res_inf[0].tenant_id == "infnet"
    assert res_inf[0].course_name == "Bootcamp em Engenharia de Software e IA"


def test_adapter_factory_resolution() -> None:
    ens_adapter = create_institutional_adapter("ens")
    assert isinstance(ens_adapter, ENSInstitutionalAdapter)

    infnet_adapter = create_institutional_adapter("infnet")
    assert isinstance(infnet_adapter, InfnetInstitutionalAdapter)

    mock_adapter = create_institutional_adapter("mock")
    assert isinstance(mock_adapter, MockInstitutionalAdapter)

    with pytest.raises(ValueError, match="Adaptador institucional desconhecido"):
        create_institutional_adapter("desconhecido_xyz")


def test_white_label_branding_and_configs() -> None:
    ens_config = load_tenant_config("config/tenants/ens.example.yaml")
    assert ens_config.institution.id == "ens"
    assert ens_config.branding.product_name == "Prometeus"
    assert ens_config.adapters.institutional == "ens"

    infnet_config = load_tenant_config("config/tenants/infnet.example.yaml")
    assert infnet_config.institution.id == "infnet"
    assert infnet_config.branding.product_name == "Infnet Market Insights"
    assert infnet_config.adapters.institutional == "infnet"
