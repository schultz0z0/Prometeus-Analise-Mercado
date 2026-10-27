"""OAuth oficial para uso direto do plano ChatGPT em uma aplicação local."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

OPENAI_OAUTH_AUTHORIZE_URL = "https://auth.openai.com/api/accounts/authorize"
OPENAI_OAUTH_TOKEN_URL = "https://auth.openai.com/api/accounts/oauth/token"
OPENAI_OAUTH_JWKS_URL = "https://auth.openai.com/.well-known/jwks.json"
OPENAI_OAUTH_ISSUER = "https://auth.openai.com"
OPENAI_RESOURCE = "https://api.openai.com/v1"
DIRECT_USAGE_SCOPE = "chatgpt.tokens.use.direct"
DYNAMIC_CLIENT_ID = "dynamic_agent_client"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:1455/auth/callback"
DEFAULT_HOST_ID_PATH = Path("var/chatgpt/host-id")


@dataclass(frozen=True)
class PkceEntry:
    code_verifier: str
    redirect_uri: str
    nonce: str
    requested_client_id: str
    created_at: float


@dataclass(frozen=True)
class OAuthTokenResult:
    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int
    scopes: tuple[str, ...]
    client_id: str
    subject: str
    email: str | None = None


@dataclass(frozen=True)
class ChatGPTCredentials:
    """Conjunto indivisível de credenciais de uma autorização ChatGPT."""

    access_token: str
    refresh_token: str
    id_token: str
    expires_at: float
    scopes: tuple[str, ...]
    client_id: str
    subject: str
    email: str | None
    selected_model: str

    @property
    def has_direct_usage(self) -> bool:
        return DIRECT_USAGE_SCOPE in self.scopes


class ChatGPTCredentialStore:
    """Persistência local atômica; o arquivo deve permanecer fora do Git."""

    def __init__(self, path: Path | str = "var/chatgpt/credentials.json") -> None:
        self.path = Path(path)

    def load(self) -> ChatGPTCredentials | None:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            scopes = raw.get("scopes", [])
            if not isinstance(scopes, list):
                return None
            credentials = ChatGPTCredentials(
                access_token=str(raw["access_token"]),
                refresh_token=str(raw["refresh_token"]),
                id_token=str(raw["id_token"]),
                expires_at=float(raw["expires_at"]),
                scopes=tuple(str(scope) for scope in scopes),
                client_id=str(raw["client_id"]),
                subject=str(raw["subject"]),
                email=str(raw["email"]) if raw.get("email") else None,
                selected_model=str(raw["selected_model"]),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if not all(
            (
                credentials.access_token,
                credentials.refresh_token,
                credentials.id_token,
                credentials.client_id,
                credentials.subject,
                credentials.selected_model,
            )
        ):
            return None
        return credentials

    def save(self, credentials: ChatGPTCredentials) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access_token": credentials.access_token,
            "refresh_token": credentials.refresh_token,
            "id_token": credentials.id_token,
            "expires_at": credentials.expires_at,
            "scopes": list(credentials.scopes),
            "client_id": credentials.client_id,
            "subject": credentials.subject,
            "email": credentials.email,
            "selected_model": credentials.selected_model,
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        temporary = self.path.with_suffix(f".tmp.{os.getpid()}")
        written = False
        try:
            temporary.write_text(content, encoding="utf-8")
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            temporary.replace(self.path)
            written = True
        except OSError:
            pass
        finally:
            if not written and temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

        if not written:
            self.path.write_text(content, encoding="utf-8")
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def clear(self) -> None:
        if self.path.is_file():
            self.path.unlink()


_pending_states: dict[str, PkceEntry] = {}


def _cleanup_pending_states() -> None:
    now = time.time()
    for key in [key for key, value in _pending_states.items() if now - value.created_at > 600]:
        _pending_states.pop(key, None)


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def get_or_create_host_id(path: Path | str = DEFAULT_HOST_ID_PATH) -> str:
    host_path = Path(path)
    if host_path.is_file():
        value = host_path.read_text(encoding="utf-8").strip()
        if value.startswith("urn:uuid:"):
            return value
    host_path.parent.mkdir(parents=True, exist_ok=True)
    value = f"urn:uuid:{uuid.uuid4()}"
    temporary = host_path.with_suffix(f".tmp.{os.getpid()}")
    written = False
    try:
        temporary.write_text(value, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        temporary.replace(host_path)
        written = True
    except OSError:
        pass
    finally:
        if not written and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass

    if not written:
        host_path.write_text(value, encoding="utf-8")
        try:
            os.chmod(host_path, 0o600)
        except OSError:
            pass
    return value


def build_chatgpt_auth_url(
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    custom_state: str | None = None,
    *,
    client_id: str = DYNAMIC_CLIENT_ID,
    host_id: str | None = None,
) -> dict[str, str]:
    """Inicia registro dinâmico ou reautorização com PKCE e token sharing."""
    _cleanup_pending_states()
    state = custom_state or secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    effective_host_id = host_id or get_or_create_host_id()
    _pending_states[state] = PkceEntry(
        code_verifier=verifier,
        redirect_uri=redirect_uri,
        nonce=nonce,
        requested_client_id=client_id,
        created_at=time.time(),
    )
    parameters = {
        "client_id": client_id,
        "ext_agent_host_id": effective_host_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": (f"openid profile email offline_access resource.invoke {DIRECT_USAGE_SCOPE}"),
        "resource": OPENAI_RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if client_id == DYNAMIC_CLIENT_ID:
        parameters["agent_name_hint"] = "Prometeus"
    return {
        "auth_url": f"{OPENAI_OAUTH_AUTHORIZE_URL}?{urlencode(parameters)}",
        "state": state,
        "redirect_uri": redirect_uri,
    }


def get_verifier_for_state(state: str) -> PkceEntry | None:
    _cleanup_pending_states()
    return _pending_states.pop(state, None)


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Decodifica claims apenas para diagnóstico; não substitui validação de assinatura."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        value = json.loads(decoded)
        return value if isinstance(value, dict) else None
    except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _verify_id_token(token: str, *, client_id: str, nonce: str) -> dict[str, Any]:
    signing_key = jwt.PyJWKClient(OPENAI_OAUTH_JWKS_URL).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=client_id,
        issuer=OPENAI_OAUTH_ISSUER,
        leeway=5,
        options={"require": ["sub", "exp", "iat"]},
    )
    if claims.get("nonce") != nonce:
        raise RuntimeError("O nonce do ID token não corresponde à autorização iniciada.")
    return claims


async def exchange_chatgpt_code(
    *,
    code: str,
    code_verifier: str,
    client_id: str,
    nonce: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> OAuthTokenResult:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "resource": OPENAI_RESOURCE,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OPENAI_OAUTH_TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()

    access_token = str(data.get("access_token", ""))
    refresh_token = str(data.get("refresh_token", ""))
    id_token = str(data.get("id_token", ""))
    scopes = tuple(str(data.get("scope", "")).split())
    if not access_token or not refresh_token or not id_token:
        raise RuntimeError("A troca OAuth não retornou o conjunto completo de credenciais.")
    if DIRECT_USAGE_SCOPE not in scopes:
        raise RuntimeError("A conta foi conectada sem permissão para usar o plano ChatGPT.")
    claims = _verify_id_token(id_token, client_id=client_id, nonce=nonce)
    subject = str(claims.get("sub", ""))
    if not subject:
        raise RuntimeError("O ID token validado não contém subject.")
    return OAuthTokenResult(
        access_token=access_token,
        refresh_token=refresh_token,
        id_token=id_token,
        expires_in=int(data.get("expires_in", 3600)),
        scopes=scopes,
        client_id=client_id,
        subject=subject,
        email=str(claims["email"]) if claims.get("email") else None,
    )


async def refresh_chatgpt_tokens(
    credentials: ChatGPTCredentials,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> ChatGPTCredentials:
    """Renova o par rotativo de tokens sem ampliar os escopos concedidos."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": credentials.client_id,
        "refresh_token": credentials.refresh_token,
        "resource": OPENAI_RESOURCE,
    }
    client = http_client or httpx.AsyncClient(timeout=30.0)
    close_client = http_client is None
    try:
        response = await client.post(OPENAI_OAUTH_TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()
    finally:
        if close_client:
            await client.aclose()

    access_token = str(data.get("access_token", ""))
    refresh_token = str(data.get("refresh_token", ""))
    if not access_token or not refresh_token:
        raise RuntimeError("A renovação OAuth não retornou os tokens rotativos completos.")
    scopes = tuple(str(data.get("scope", "")).split()) or credentials.scopes
    if DIRECT_USAGE_SCOPE not in scopes:
        raise RuntimeError("A renovação removeu a permissão de uso direto do plano ChatGPT.")
    return ChatGPTCredentials(
        access_token=access_token,
        refresh_token=refresh_token,
        id_token=str(data.get("id_token") or credentials.id_token),
        expires_at=time.time() + int(data.get("expires_in", 3600)),
        scopes=scopes,
        client_id=credentials.client_id,
        subject=credentials.subject,
        email=credentials.email,
        selected_model=credentials.selected_model,
    )


async def list_chatgpt_models(
    access_token: str,
    *,
    base_url: str = OPENAI_RESOURCE,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, str]]:
    """Obtém o catálogo real da conta e mantém apenas modelos exibíveis."""
    client = http_client or httpx.AsyncClient(timeout=30.0)
    close_client = http_client is None
    try:
        response = await client.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
    finally:
        if close_client:
            await client.aclose()

    models = data.get("models", []) if isinstance(data, dict) else []
    return [
        {"slug": str(item["slug"]), "display_name": str(item.get("display_name") or item["slug"])}
        for item in models
        if isinstance(item, dict)
        and item.get("visibility") == "list"
        and isinstance(item.get("slug"), str)
        and item["slug"]
    ]
