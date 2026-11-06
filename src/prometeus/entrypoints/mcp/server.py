"""Servidor MCP (Model Context Protocol) de alto nível para integração com Chatbots e Agentes (Fase 07).

Expõe ferramentas delimitadas e não expõe conectores internos de baixo nível (ADR-0007).
Implementa especificação JSON-RPC 2.0 do Model Context Protocol (MCP).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus import __descriptor__, __product__, __version__
from prometeus.application.analysis_jobs import publish_analysis_job
from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.access import AccessPrincipal
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    CourseOutcomeModel,
    DossierModel,
    HumanDecisionModel,
)

logger = logging.getLogger(__name__)


# Definição canônica das 5 ferramentas MCP de alto nível
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "create_course_analysis",
        "description": "Submete uma nova proposta de curso e enfileira a análise de viabilidade de mercado no Prometeus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "idempotency_key": {
                    "type": "string",
                    "description": "Chave estável do pedido para recuperar a mesma análise em retries",
                },
                "course_name": {
                    "type": "string",
                    "description": "Nome proposto do curso (ex: 'MBA em Inteligência de Dados em Seguros')",
                },
                "tenant_id": {
                    "type": "string",
                    "default": "ens",
                    "description": "Identificador do tenant/instituição educacional",
                },
                "proposal_data": {
                    "type": "object",
                    "description": "Dados opcionais da proposta (ementa, público-alvo, preço proposto)",
                },
            },
            "required": ["course_name", "idempotency_key"],
        },
    },
    {
        "name": "check_analysis_progress",
        "description": "Consulta o ciclo de vida atual, recomendação determinística e progresso de etapas de uma análise.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_id": {
                    "type": "string",
                    "description": "Identificador único da análise",
                }
            },
            "required": ["analysis_id"],
        },
    },
    {
        "name": "retrieve_course_dossier",
        "description": "Recupera o dossiê executivo completo, claims verificadas e justificativas estratégicas aprovadas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_id": {
                    "type": "string",
                    "description": "Identificador da análise concluída",
                },
                "target_audience": {
                    "type": "string",
                    "enum": ["all", "executive", "academic", "marketing"],
                    "default": "all",
                    "description": "Filtrar seções por público decisor",
                },
            },
            "required": ["analysis_id"],
        },
    },
    {
        "name": "submit_decision",
        "description": "Registra a decisão humana institucional (diretoria, coordenação) sobre a recomendação do Prometeus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_id": {"type": "string", "description": "ID da análise"},
                "user_id": {"type": "string", "description": "Identificador do decisor"},
                "user_role": {
                    "type": "string",
                    "description": "Papel do decisor (ex: director, coordinator)",
                },
                "decision": {
                    "type": "string",
                    "enum": ["APPROVED", "APPROVED_WITH_ADJUSTMENTS", "REJECTED"],
                    "description": "Decisão formal tomada",
                },
                "rationale": {"type": "string", "description": "Justificativa da decisão"},
                "adjustments": {"type": "object", "description": "Ajustes acordados"},
            },
            "required": ["analysis_id", "user_id", "user_role", "decision", "rationale"],
        },
    },
    {
        "name": "record_course_outcome",
        "description": "Registra desfechos reais de captação pós-lançamento (alunos matriculados, inscritos, receita) para calibração.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_id": {"type": "string", "description": "ID da análise de origem"},
                "external_course_id": {"type": "string", "description": "ID do curso no LMS/CRM"},
                "launch_date": {
                    "type": "string",
                    "description": "Data de início da captação (AAAA-MM-DD)",
                },
                "enrolled_count": {
                    "type": "integer",
                    "description": "Total de matrículas efetivadas",
                },
                "leads_count": {"type": "integer", "default": 0, "description": "Total de leads"},
                "applicants_count": {
                    "type": "integer",
                    "default": 0,
                    "description": "Total de inscritos",
                },
                "revenue_brl": {"type": "number", "description": "Receita bruta gerada em BRL"},
                "notes": {
                    "type": "string",
                    "description": "Observações qualitativas de desempenho",
                },
            },
            "required": ["analysis_id", "external_course_id", "launch_date", "enrolled_count"],
        },
    },
]


class PrometeusMCPServer:
    """Servidor MCP JSON-RPC 2.0 integrado ao domínio do Prometeus."""

    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        *,
        publisher: Callable[[str, str], Any] | None = None,
        settings: AppSettings | None = None,
        principal: AccessPrincipal | None = None,
    ) -> None:
        self.session_factory = db_session_factory
        self.settings = settings or AppSettings()
        self.principal = principal or AccessPrincipal(
            "local-mcp", self.settings.INSTITUTION_ID, "admin"
        )
        self.publisher = publisher

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Processa requisição JSON-RPC 2.0 do protocolo MCP."""
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not isinstance(params, dict):
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": "params deve ser objeto"},
            }
        if "id" not in request:
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion")
                    if params.get("protocolVersion")
                    in {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
                    else "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": __product__,
                        "version": __version__,
                        "description": __descriptor__,
                    },
                },
            }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": MCP_TOOLS},
            }

        elif method == "tools/call":
            tool_name = str(params.get("name") or "")
            arguments = params.get("arguments", {})
            try:
                content = await self.execute_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(content, ensure_ascii=False, indent=2),
                            }
                        ]
                    },
                }
            except Exception as exc:
                logger.error(f"Erro na execução da tool MCP '{tool_name}': {exc}")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32000, "message": str(exc)},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Método MCP não encontrado: {method}"},
            }

    async def execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Despacho determinístico para as 5 ferramentas suportadas."""
        if not isinstance(args, dict):
            raise ValueError("Os argumentos devem ser um objeto.")
        scope = {
            "create_course_analysis": "analyze",
            "submit_decision": "decide",
            "record_course_outcome": "outcome",
        }.get(name, "read")
        self.principal.require(scope)
        if args.get("tenant_id", self.principal.tenant_id) != self.principal.tenant_id:
            raise ValueError("Acesso a outra instituição não autorizado.")
        async with self.session_factory() as session:
            repo = AnalysisRepository(session)
            if name != "create_course_analysis" and args.get("analysis_id"):
                target = await repo.get_by_id(str(args["analysis_id"]))
                if target and target.tenant_id != self.principal.tenant_id:
                    raise ValueError("Acesso a outra instituição não autorizado.")

            if name == "create_course_analysis":
                course_name = args["course_name"]
                tenant_id = args.get("tenant_id", self.principal.tenant_id)
                proposal_data = args.get("proposal_data", {})
                corr_id = f"mcp-corr-{uuid.uuid4().hex[:8]}"

                key = str(args.get("idempotency_key", "")).strip()
                if not key:
                    raise ValueError("idempotency_key é obrigatório.")
                if self.settings.KILL_SWITCH_ACTIVE:
                    raise ValueError("Submissão suspensa pelo kill switch.")
                if (
                    not isinstance(course_name, str)
                    or not course_name.strip()
                    or not isinstance(proposal_data, dict)
                ):
                    raise ValueError("Proposta inválida.")
                result = await CreateAnalysisUseCase(session, self.settings).execute(
                    CreateAnalysisCommand(
                        tenant_id=tenant_id,
                        course_name=course_name,
                        correlation_id=corr_id,
                        proposal_data=proposal_data,
                        idempotency_key=key,
                    )
                )
                await session.commit()
                if not result.is_existing:
                    publisher = self.publisher
                    if publisher is None:
                        from prometeus.workers.tasks import run_analysis_workflow

                        publisher = run_analysis_workflow.delay
                    await publish_analysis_job(session, result.analysis_id, publisher)

                return {
                    "analysis_id": result.analysis_id,
                    "status": result.status.value,
                    "course_name": course_name,
                    "message": "Análise iniciada com sucesso via MCP.",
                }

            elif name == "check_analysis_progress":
                analysis_id = args["analysis_id"]
                target_analysis = await repo.get_by_id(analysis_id)
                if not target_analysis:
                    raise ValueError(f"Análise não encontrada: {analysis_id}")

                return {
                    "analysis_id": target_analysis.id,
                    "status": target_analysis.status.value,
                    "recommendation": target_analysis.recommendation.value
                    if target_analysis.recommendation
                    else None,
                    "steps_completed": len(target_analysis.steps),
                    "updated_at": target_analysis.updated_at.isoformat(),
                }

            elif name == "retrieve_course_dossier":
                analysis_id = args["analysis_id"]
                target_audience = args.get("target_audience", "all")

                stmt = select(DossierModel).where(DossierModel.analysis_id == analysis_id)
                dossier = (await session.execute(stmt)).scalar_one_or_none()
                if not dossier:
                    raise ValueError(f"Dossiê não encontrado para a análise: {analysis_id}")

                sections = dossier.sections
                if target_audience != "all":
                    sections = [s for s in sections if s.get("target_audience") == target_audience]

                return {
                    "analysis_id": dossier.analysis_id,
                    "status": dossier.status,
                    "executive_summary": dossier.executive_summary,
                    "sections": sections,
                    "claims_count": len(dossier.claims),
                    "facts_hash": dossier.facts_hash,
                }

            elif name == "submit_decision":
                if args.get("decision") not in {
                    "APPROVED",
                    "APPROVED_WITH_ADJUSTMENTS",
                    "REJECTED",
                }:
                    raise ValueError("Decisão institucional inválida.")
                analysis_id = args["analysis_id"]
                target_analysis = await repo.get_by_id(analysis_id)
                if not target_analysis:
                    raise ValueError(f"Análise não encontrada: {analysis_id}")

                decision_model = HumanDecisionModel(
                    id=f"dec_{uuid.uuid4().hex[:12]}",
                    analysis_id=analysis_id,
                    user_id=self.principal.subject,
                    user_role=self.principal.role,
                    decision=args["decision"].upper(),
                    rationale=args["rationale"],
                    adjustments=args.get("adjustments", {}),
                    created_at=datetime.now(UTC),
                )
                session.add(decision_model)
                await session.commit()

                return {
                    "decision_id": decision_model.id,
                    "analysis_id": analysis_id,
                    "status": "RECORDED",
                    "decision": decision_model.decision,
                }

            elif name == "record_course_outcome":
                from prometeus.entrypoints.rest.app import RecordOutcomeRequest

                outcome_input = RecordOutcomeRequest.model_validate(
                    {key: value for key, value in args.items() if key != "analysis_id"}
                )
                args = {**args, **outcome_input.model_dump()}
                analysis_id = args["analysis_id"]
                target_analysis = await repo.get_by_id(analysis_id)
                if not target_analysis:
                    raise ValueError(f"Análise não encontrada: {analysis_id}")

                outcome_model = CourseOutcomeModel(
                    id=f"out_{uuid.uuid4().hex[:12]}",
                    analysis_id=analysis_id,
                    external_course_id=args["external_course_id"],
                    launch_date=args["launch_date"],
                    enrolled_count=int(args["enrolled_count"]),
                    leads_count=int(args.get("leads_count", 0)),
                    applicants_count=int(args.get("applicants_count", 0)),
                    revenue_brl=float(args["revenue_brl"])
                    if args.get("revenue_brl") is not None
                    else None,
                    notes=args.get("notes"),
                    created_at=datetime.now(UTC),
                )
                session.add(outcome_model)
                await session.commit()

                return {
                    "outcome_id": outcome_model.id,
                    "analysis_id": analysis_id,
                    "enrolled_count": outcome_model.enrolled_count,
                    "status": "RECORDED",
                }

            else:
                raise ValueError(f"Ferramenta MCP desconhecida: {name}")
