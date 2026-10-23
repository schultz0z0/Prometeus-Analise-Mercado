"""Implementação do fluxo OAuth PKCE canônico do OpenAI Codex / ChatGPT.

Baseado na arquitetura de conexão direta do Prometeus-Aion (aionui.com):
- Client ID canônico: app_EMoamEEZ73f0CkXaXp7hrann
- Endpoints oficiais auth.openai.com
- PKCE com S256 e extração de claims JWT (account_id e email)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

OPENAI_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OPENAI_OAUTH_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
OPENAI_OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost:1455/auth/callback"


@dataclass
class PkceEntry:
    code_verifier: str
    redirect_uri: str
    created_at: float


@dataclass
class OAuthTokenResult:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    account_id: str | None = None
    email: str | None = None


# Armazenamento em memória de estados PKCE pendentes (expiração de 10 min)
_pending_states: dict[str, PkceEntry] = {}


def _cleanup_pending_states() -> None:
    now = time.time()
    expired = [k for k, v in _pending_states.items() if now - v.created_at > 600]
    for k in expired:
        _pending_states.pop(k, None)


def generate_pkce_pair() -> tuple[str, str]:
    """Gera code_verifier seguro e code_challenge em base64url com SHA256."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def build_chatgpt_auth_url(
    redirect_uri: str | None = None,
    custom_state: str | None = None,
) -> dict[str, str]:
    """Constrói a URL oficial de autorização do ChatGPT/Codex com PKCE."""
    _cleanup_pending_states()
    state = custom_state or secrets.token_hex(16)
    code_verifier, code_challenge = generate_pkce_pair()
    effective_redirect = redirect_uri or DEFAULT_REDIRECT_URI

    _pending_states[state] = PkceEntry(
        code_verifier=code_verifier,
        redirect_uri=effective_redirect,
        created_at=time.time(),
    )

    params = {
        "response_type": "code",
        "client_id": OPENAI_OAUTH_CLIENT_ID,
        "redirect_uri": effective_redirect,
        "scope": "openid profile email offline_access model.request",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "codex_cli_simplified_flow": "true",
    }

    auth_url = f"{OPENAI_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return {
        "auth_url": auth_url,
        "state": state,
        "code_verifier": code_verifier,
        "redirect_uri": effective_redirect,
    }


def get_verifier_for_state(state: str) -> PkceEntry | None:
    return _pending_states.pop(state, None)


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Decodifica as claims do JWT sem validação criptográfica (apenas leitura)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


def extract_account_id_from_token(token: str) -> str | None:
    payload = decode_jwt_payload(token)
    if not payload:
        return None

    if "chatgpt_account_id" in payload:
        return str(payload["chatgpt_account_id"])

    auth_claim = payload.get("https://api.openai.com/auth")
    if isinstance(auth_claim, dict):
        if "chatgpt_account_id" in auth_claim:
            return str(auth_claim["chatgpt_account_id"])
        if "organization_id" in auth_claim:
            return str(auth_claim["organization_id"])

    return None


def extract_email_from_token(token: str) -> str | None:
    payload = decode_jwt_payload(token)
    if not payload:
        return None

    if "email" in payload:
        return str(payload["email"])

    auth_claim = payload.get("https://api.openai.com/auth")
    if isinstance(auth_claim, dict) and "email" in auth_claim:
        return str(auth_claim["email"])

    return None


async def exchange_chatgpt_code(
    code: str,
    code_verifier: str,
    redirect_uri: str | None = None,
) -> OAuthTokenResult:
    """Troca o authorization code pelo access token e refresh token junto à OpenAI."""
    effective_redirect = redirect_uri or DEFAULT_REDIRECT_URI

    payload = {
        "grant_type": "authorization_code",
        "client_id": OPENAI_OAUTH_CLIENT_ID,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": effective_redirect,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(OPENAI_OAUTH_TOKEN_URL, data=payload, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(f"Falha na troca de token OAuth ({res.status_code}): {res.text}")

        data = res.json()
        access_token = data.get("access_token", "")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        id_token = data.get("id_token")

        account_id = (
            extract_account_id_from_token(access_token)
            or (extract_account_id_from_token(id_token) if id_token else None)
        )
        email = (
            (extract_email_from_token(id_token) if id_token else None)
            or extract_email_from_token(access_token)
        )

        return OAuthTokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            account_id=account_id,
            email=email,
        )
