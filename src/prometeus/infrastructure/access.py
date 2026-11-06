"""Identidade de acesso ao Prometeus; independente das credenciais dos provedores."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from fastapi import HTTPException, Request

from prometeus.domain.configuration import AppSettings

COOKIE_NAME = "prometeus_session"
ROLE_SCOPES = {
    "reader": {"read"},
    "analyst": {"read", "analyze", "outcome"},
    "director": {"read", "analyze", "outcome", "decide"},
    "admin": {"read", "analyze", "outcome", "decide", "admin"},
}


@dataclass(frozen=True)
class AccessPrincipal:
    subject: str
    tenant_id: str
    role: str

    def require(self, scope: str) -> None:
        if scope not in ROLE_SCOPES.get(self.role, set()):
            raise HTTPException(403, "Permissão insuficiente para esta operação.")

    def public(self) -> dict[str, str]:
        return {"subject": self.subject, "tenant_id": self.tenant_id, "role": self.role}


def local_admin_key(settings: AppSettings) -> str:
    """Bootstrap local, privado e atômico. O segredo nunca é devolvido via HTTP."""
    path = Path(settings.AUTH_ADMIN_KEY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        value = secrets.token_urlsafe(48)
        output.write(value)
    return value


def access_records(settings: AppSettings) -> list[dict[str, str]]:
    raw = settings.SERVICE_API_KEYS.strip()
    if not raw:
        return [
            {
                "key": local_admin_key(settings),
                "subject": "local-admin",
                "tenant_id": settings.INSTITUTION_ID,
                "role": "admin",
            }
        ]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(
            503, "SERVICE_API_KEYS deve ser uma lista JSON de identidades."
        ) from error
    if not isinstance(parsed, list) or not parsed:
        raise HTTPException(503, "Configuração de acesso inválida.")
    records: list[dict[str, str]] = []
    for entry in parsed:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(field), str) or not entry[field].strip()
            for field in ("key", "subject", "tenant_id", "role")
        ):
            raise HTTPException(503, "Configuração de acesso inválida.")
        if entry["role"] not in ROLE_SCOPES or len(entry["key"]) < 24:
            raise HTTPException(503, "Configuração de acesso inválida.")
        records.append({field: entry[field] for field in ("key", "subject", "tenant_id", "role")})
    return records


def authenticate_key(value: str, settings: AppSettings) -> AccessPrincipal:
    for entry in access_records(settings):
        if hmac.compare_digest(value.encode(), entry["key"].encode()):
            return AccessPrincipal(entry["subject"], entry["tenant_id"], entry["role"])
    raise HTTPException(
        401, "Credencial de acesso inválida.", headers={"WWW-Authenticate": "Bearer"}
    )


def session_signing_key(settings: AppSettings) -> bytes:
    # Rotacionar a chave ou as identidades revoga as sessões existentes.
    return hashlib.sha256(json.dumps(access_records(settings), sort_keys=True).encode()).digest()


def create_browser_session(principal: AccessPrincipal, settings: AppSettings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            **principal.public(),
            "sub": principal.subject,
            "iat": now,
            "exp": now + timedelta(hours=8),
            "iss": "prometeus",
            "aud": "prometeus-browser",
        },
        session_signing_key(settings),
        algorithm="HS256",
    )


def authenticated_principal(
    request: Request, settings: AppSettings
) -> tuple[AccessPrincipal, bool]:
    authorization = request.headers.get("authorization", "")
    if authorization:
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential:
            raise HTTPException(401, "Use uma credencial Bearer válida.")
        return authenticate_key(credential, settings), False
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        try:
            claims: dict[str, Any] = jwt.decode(
                cookie,
                session_signing_key(settings),
                algorithms=["HS256"],
                issuer="prometeus",
                audience="prometeus-browser",
                options={"require": ["exp", "iat", "sub", "tenant_id", "role"]},
            )
            principal = AccessPrincipal(claims["sub"], claims["tenant_id"], claims["role"])
            if not any(
                principal.public()
                == {field: entry[field] for field in ("subject", "tenant_id", "role")}
                for entry in access_records(settings)
            ):
                raise jwt.InvalidTokenError("Identidade revogada")
            return principal, True
        except jwt.InvalidTokenError as error:
            raise HTTPException(401, "Sessão expirada ou inválida.") from error
    raise HTTPException(401, "Autenticação necessária.", headers={"WWW-Authenticate": "Bearer"})


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and origin.rstrip("/") != str(request.base_url).rstrip("/")
    ):
        raise HTTPException(403, "Origem da requisição não autorizada.")


def operation_scope(request: Request) -> str:
    path = request.url.path
    if path.startswith(("/v1/settings", "/v1/auth/", "/v1/institutional/seed")) or path.endswith(
        "/sector-radar/refresh"
    ):
        return "admin"
    if request.method in {"GET", "HEAD", "OPTIONS"} or path.startswith("/v1/session"):
        return "read"
    if path.endswith("/decisions"):
        return "decide"
    if path.endswith("/outcomes"):
        return "outcome"
    return "analyze"
