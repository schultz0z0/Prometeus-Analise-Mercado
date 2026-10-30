"""Normalização tipada de recorte e identidade; texto da LLM não vira locale de API."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit

_RESTRICTION = re.compile(
    r"\b(?:somente|apenas|restrit[oa] a|exclusivamente|com foco em|limitad[oa] a)\s+(.+)$"
)
_BRAZIL_ALIASES = re.compile(r"\b(?:brasil|brazil|br)\b")

BRAZILIAN_STATES: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

_ALL_UFS_REGEX = "|".join(BRAZILIAN_STATES.keys())
_FOREIGN_INDICATORS = re.compile(
    r"\b(?:usa|united states|uk|united kingdom|portugal|spain|france|germany|argentina|mexico|tx|fl|ny|ca|il|oh|ga|nc|va)\b",
    re.I,
)


def normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", text.encode("ascii", "ignore").decode().lower()).split()
    )


def normalize_geography(value: str | None) -> str | None:
    if not value:
        return value
    parts = value.split(";", 1)
    head = parts[0].strip().rstrip(".")
    if _RESTRICTION.search(normalized_text(value)):
        return value.strip()
    if len(parts) > 1 and not normalized_text(parts[1]).startswith(
        ("participacao online", "online", "aulas online", "ead", "ensino online")
    ):
        return value.strip()
    clean = normalized_text(head)
    if clean in {"brasil", "brazil", "br"}:
        return "Brasil"
    # A delivery/interpretation note after an explicit national scope is not
    # a narrower region. Other strings (e.g. São Paulo, Brasil) remain narrow.
    if re.match(
        r"^(brasil|brazil|br) (como contexto|no contexto|participacao online|mercado nacional|em ambito nacional)\b",
        clean,
    ):
        return "Brasil"
    return value.strip()


def matches_narrow_geography(requested: str, observed: str) -> bool:
    """Compara recorte regional solicitado contra localização observada.

    Reconhece todas as 27 UFs brasileiras, nomes por extenso e cidades,
    resolvendo ambiguidades e rejeitando estritamente localidades estrangeiras.
    """
    target = normalized_text(requested)
    actual = normalized_text(observed)

    # Identifica se há restrição estrita regional
    restriction = _RESTRICTION.search(target)
    narrow_phrase = ""
    if restriction:
        narrow_phrase = restriction.group(1).strip()
    elif ";" in requested:
        narrow_phrase = normalized_text(requested.split(";", 1)[1]).strip()
    else:
        clean_target = _BRAZIL_ALIASES.sub("", target).strip()
        if clean_target and not any(
            clean_target.startswith(prefix)
            for prefix in (
                "como contexto",
                "no contexto",
                "participacao online",
                "mercado nacional",
                "em ambito nacional",
            )
        ):
            narrow_phrase = clean_target

    if narrow_phrase:
        clean_narrow = re.sub(
            r"^(?:estado de|cidade de|municipio de|regiao de|em|no|na)\s+", "", narrow_phrase
        ).strip()
        clean_narrow = _BRAZIL_ALIASES.sub("", clean_narrow).strip()
        if clean_narrow:
            # Encontra UF correspondente se for nome de estado ou sigla
            target_uf = None
            for uf, name in BRAZILIAN_STATES.items():
                if clean_narrow in {uf.lower(), normalized_text(name)}:
                    target_uf = uf
                    break

            if target_uf:
                state_name_norm = normalized_text(BRAZILIAN_STATES[target_uf])
                # Verifica menção à UF ou nome do estado
                has_target_uf = bool(re.search(rf"\b{target_uf.lower()}\b", actual))
                has_target_name = bool(re.search(rf"\b{re.escape(state_name_norm)}\b", actual))
                if not (has_target_uf or has_target_name):
                    return False

                # Se a localização observada mencionar explicitamente outra UF ou estado, rejeita
                for other_uf, other_name in BRAZILIAN_STATES.items():
                    if other_uf != target_uf:
                        other_name_norm = normalized_text(other_name)
                        if (
                            re.search(rf",\s*{other_uf.lower()}\b", actual)
                            or re.search(rf"\b{re.escape(other_name_norm)}\b", actual)
                        ) and not (has_target_uf or has_target_name):
                            return False
                return True
            else:
                # Cidade específica (ex: Campinas, Ribeirão Preto)
                return bool(re.search(rf"\b{re.escape(clean_narrow)}\b", actual))

    # Escopo geral Brasil
    # Se mencionar explicitamente país estrangeiro ou indicador sem mencionar Brasil, rejeita
    if _FOREIGN_INDICATORS.search(observed) and not re.search(r"\b(?:brasil|brazil)\b", actual):
        return False

    # PA isolado nos EUA sem indicador de Pará ou Brasil é rejeitado
    if re.search(r",\s*PA\b", observed) and not re.search(
        r"\b(?:belem|santarem|maraba|para|brasil|brazil)\b", actual
    ):
        return False

    if re.search(r"\bbrasil\b", actual):
        return True

    # Verifica qualquer uma das 27 UFs com pontuação ou por extenso
    if re.search(rf",\s*(?:{_ALL_UFS_REGEX})\b", observed, re.I):
        return True
    for name in BRAZILIAN_STATES.values():
        if re.search(rf"\b{re.escape(normalized_text(name))}\b", actual):
            return True

    return False


def country_code(value: str | None) -> str | None:
    return "BR" if normalize_geography(value) == "Brasil" else None


def normalize_language(value: str) -> str:
    clean = normalized_text(value)
    if clean in {"pt", "pt br", "portugues", "portuguese"} or clean.startswith(
        ("portugues ", "portuguese ")
    ):
        return "pt-BR"
    if clean in {"pt pt"}:
        return "pt-PT"
    if clean in {"ingles", "english"}:
        return "en"
    if clean in {"espanhol", "spanish"}:
        return "es"
    return value.strip().replace("_", "-")


def is_own_institution(
    payload: dict[str, object], source_url: str, context: dict[str, object] | None
) -> bool:
    """Use configured identity, not incidental body mentions of the institution."""
    if not context:
        return False
    names = [context.get(key) for key in ("name", "institution_name", "display_name")]
    aliases = context.get("aliases", [])
    if isinstance(aliases, list):
        names.extend(aliases)
    own_names = {normalized_text(name) for name in names if name}
    observed = [
        payload.get(key)
        for key in (
            "pageName",
            "page_name",
            "institution",
            "institution_name",
            "advertiser",
            "advertiser_name",
            "ownerUsername",
        )
    ]
    snapshot = payload.get("snapshot")
    if isinstance(snapshot, dict):
        observed.extend(snapshot.get(key) for key in ("page_name", "pageName", "ownerUsername"))
    if any(normalized_text(name) in own_names for name in observed if name):
        return True
    domains = context.get("domains", [])
    if not isinstance(domains, list):
        return False
    host = (urlsplit(source_url).hostname or "").lower().removeprefix("www.")
    return any(
        host == str(domain).lower().removeprefix("www.")
        or host.endswith("." + str(domain).lower().removeprefix("www."))
        for domain in domains
        if domain
    )
