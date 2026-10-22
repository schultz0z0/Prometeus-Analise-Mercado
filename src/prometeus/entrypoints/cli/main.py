"""Interface de linha de comando (CLI) operacional do Prometeus."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from prometeus import __descriptor__, __product__, __version__
from prometeus.application.create_analysis import (
    CreateAnalysisCommand,
    CreateAnalysisUseCase,
)
from prometeus.domain.configuration import (
    AppSettings,
    ConfigurationError,
    load_scoring_profile,
    load_tenant_config,
    validate_environment_and_models,
)
from prometeus.infrastructure.db.session import get_session

app = typer.Typer(
    name="prometeus",
    help=f"{__product__} — {__descriptor__}",
    no_args_is_help=True,
)
config_app = typer.Typer(name="config", help="Comandos de governança e validação de configurações")
analyses_app = typer.Typer(name="analyses", help="Comandos operacionais de análises")

app.add_typer(config_app, name="config")
app.add_typer(analyses_app, name="analyses")

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold gold1]{__product__}[/bold gold1] v{__version__} — {__descriptor__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Exibe a versão do Prometeus e encerra.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    pass


@config_app.command("validate")
def validate_config(
    tenant_config_path: Annotated[
        str,
        typer.Option(
            "--tenant",
            "-t",
            help="Caminho do arquivo de configuração do tenant",
        ),
    ] = "config/tenants/ens.example.yaml",
    scoring_profile_path: Annotated[
        str,
        typer.Option(
            "--scoring",
            "-s",
            help="Caminho do arquivo de perfil de scoring",
        ),
    ] = "config/scoring/default-v1.example.yaml",
) -> None:
    """Valida configurações de tenant, scoring profile e variáveis de ambiente."""
    console.print(f"[bold cyan]Validando configurações do {__product__}...[/bold cyan]\n")

    settings = AppSettings()
    errors: list[str] = []

    # 1. Validação de ambiente e modelo JEV
    try:
        validate_environment_and_models(settings)
        console.print(
            f"[green][OK][/green] Ambiente e modelo: [bold]{settings.APP_ENV}[/bold] (JEV: [bold]{settings.JEV_MODEL}[/bold])"
        )
    except ConfigurationError as exc:
        errors.append(f"Ambiente/JEV: {exc}")
        console.print(f"[red][FALHA][/red] Ambiente/JEV: {exc}")

    # 2. Validação do Tenant YAML
    try:
        tenant = load_tenant_config(tenant_config_path)
        console.print(
            f"[green][OK][/green] Tenant Config ({tenant_config_path}): [bold]{tenant.institution.display_name}[/bold] ({tenant.institution.id})"
        )
    except ConfigurationError as exc:
        errors.append(f"Tenant: {exc}")
        console.print(f"[red][FALHA][/red] Tenant Config: {exc}")

    # 3. Validação do Scoring Profile YAML
    try:
        scoring = load_scoring_profile(scoring_profile_path)
        console.print(
            f"[green][OK][/green] Scoring Profile ({scoring_profile_path}): [bold]{scoring.profile_id}[/bold] ({len(scoring.weights)} pilares, soma={sum(scoring.weights.values()):.2f})"
        )
    except ConfigurationError as exc:
        errors.append(f"Scoring: {exc}")
        console.print(f"[red][FALHA][/red] Scoring Profile: {exc}")

    if errors:
        console.print(
            f"\n[bold red]Falha na validação! Encontrados {len(errors)} erro(s).[/bold red]"
        )
        raise typer.Exit(code=1)

    console.print(
        "\n[bold green][OK] Todas as configurações foram validadas com sucesso![/bold green]"
    )


@analyses_app.command("create")
def create_analysis_cli(
    file_path: Annotated[
        Path,
        typer.Option(
            "--file",
            "-f",
            help="Caminho para arquivo JSON com dados da proposta",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    idempotency_key: Annotated[
        str | None,
        typer.Option(
            "--idempotency-key",
            "-k",
            help="Chave de idempotência (gerada automaticamente se omitida)",
        ),
    ] = None,
) -> None:
    """Cria uma nova análise a partir de um arquivo JSON de proposta."""
    try:
        content = file_path.read_text(encoding="utf-8")
        payload = json.loads(content)
    except Exception as exc:
        console.print(f"[bold red]Erro ao ler arquivo JSON {file_path}:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    course_name = payload.get("course_name")
    if not course_name:
        console.print(
            "[bold red]O campo 'course_name' é obrigatório no JSON da proposta.[/bold red]"
        )
        raise typer.Exit(code=1)

    tenant_id = payload.get("tenant_id", "ens")
    proposal_data = payload.get("proposal_data", {})
    idemp_key = idempotency_key or payload.get("idempotency_key") or str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    async def _run() -> None:
        async with get_session() as session:
            use_case = CreateAnalysisUseCase(session)
            cmd = CreateAnalysisCommand(
                tenant_id=tenant_id,
                course_name=course_name,
                proposal_data=proposal_data,
                idempotency_key=idemp_key,
                correlation_id=correlation_id,
            )
            res = await use_case.execute(cmd)

            table = Table(title=f"Resultado da Criação de Análise — {__product__}")
            table.add_column("Propriedade", style="cyan", no_wrap=True)
            table.add_column("Valor", style="magenta")

            table.add_row("ID da Análise", res.analysis_id)
            table.add_row("Curso", course_name)
            table.add_row("Instituição", tenant_id)
            table.add_row("Status", res.status.value)
            table.add_row("Idempotency Key", idemp_key)
            table.add_row("Correlation ID", correlation_id)
            table.add_row("Criado em", res.created_at)
            table.add_row(
                "Existente (Idempotente)", "Sim" if res.is_existing else "Não (Nova Análise)"
            )

            console.print(table)

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[bold red]Erro ao processar criação de análise:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
