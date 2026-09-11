"""Lead field normalization: email, phone E.164, free-mail and disposable checks."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Literal

import phonenumbers
from email_validator import EmailNotValidError, validate_email
from phonenumbers import NumberParseException, PhoneNumberFormat
from pydantic import BaseModel, ConfigDict, Field

Language = Literal["fi", "sv", "en", "other"]
DEFAULT_PHONE_REGION = "FI"


class NormalizeInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = ""
    name: str = ""
    company_name: str | None = None
    phone: str | None = None
    language: str | None = None
    country: str | None = None
    website: str | None = None
    message: str | None = None


class NormalizeResult(BaseModel):
    email_normalized: str
    email_valid: bool
    name: str
    company_name: str | None
    company_domain: str | None
    is_free_mail: bool
    is_disposable: bool
    phone_e164: str | None
    language: Language
    country: str | None
    errors: list[str] = Field(default_factory=list)


def normalize_lead(
    payload: NormalizeInput | dict[str, object], *, mx_check: bool = False
) -> NormalizeResult:
    inp = payload if isinstance(payload, NormalizeInput) else NormalizeInput.model_validate(payload)
    errors: list[str] = []

    name = inp.name.strip()
    company_name = inp.company_name.strip() if inp.company_name else None
    country = inp.country.strip() if inp.country else None

    email_normalized, email_valid, email_domain = _normalize_email(
        inp.email, mx_check=mx_check, errors=errors
    )
    is_free_mail = bool(email_domain and email_domain in _free_mail_domains())
    is_disposable = bool(email_domain and email_domain in _disposable_domains())

    company_domain = _company_domain(inp.website, email_domain, is_free_mail)
    phone_e164 = _to_e164(inp.phone, errors=errors)
    language = _language_hint(inp.language, name, inp.message)

    return NormalizeResult(
        email_normalized=email_normalized,
        email_valid=email_valid,
        name=name,
        company_name=company_name,
        company_domain=company_domain,
        is_free_mail=is_free_mail,
        is_disposable=is_disposable,
        phone_e164=phone_e164,
        language=language,
        country=country,
        errors=errors,
    )


def _normalize_email(
    raw: str, *, mx_check: bool, errors: list[str]
) -> tuple[str, bool, str | None]:
    candidate = raw.strip()
    if not candidate:
        errors.append("email_missing")
        return "", False, None
    try:
        info = validate_email(
            candidate,
            check_deliverability=mx_check,
            test_environment=not mx_check,
        )
    except EmailNotValidError:
        errors.append("email_invalid")
        lowered = candidate.lower()
        domain = lowered.rsplit("@", 1)[-1] if "@" in lowered else None
        return lowered, False, domain
    normalized = info.normalized.lower()
    domain = normalized.rsplit("@", 1)[-1].lower()
    return normalized, True, domain


def _company_domain(
    website: str | None, email_domain: str | None, is_free_mail: bool
) -> str | None:
    if website:
        host = website.strip().lower()
        for prefix in ("https://", "http://"):
            if host.startswith(prefix):
                host = host[len(prefix) :]
        host = host.split("/", 1)[0].split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        if host:
            return host
    if email_domain and not is_free_mail:
        return email_domain
    return None


def _to_e164(raw: str | None, *, errors: list[str]) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        parsed = phonenumbers.parse(str(raw).strip(), DEFAULT_PHONE_REGION)
    except NumberParseException:
        errors.append("phone_invalid")
        return None
    if not phonenumbers.is_possible_number(parsed):
        errors.append("phone_invalid")
        return None
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


_SV_WORDS = (" vill ", " boka ", " nästa ", " och ", " vecka ")
_FI_WORDS = (" tarvitsemme ", " tarjouksen ", " kiitos ", " haluan ", " tämä ")


def _language_hint(explicit: str | None, name: str, message: str | None) -> Language:
    allowed: set[str] = {"fi", "sv", "en", "other"}
    if explicit:
        value = explicit.strip().lower()
        if value in allowed:
            return value  # type: ignore[return-value]
    blob = f"{name} {message or ''}".lower()
    padded = f" {blob} "
    if "å" in blob or any(word in padded for word in _SV_WORDS):
        return "sv"
    if any(char in blob for char in "äö") or any(word in padded for word in _FI_WORDS):
        return "fi"
    return "other"


def _load_domain_list(filename: str) -> frozenset[str]:
    text = files("p01_backend").joinpath(filename).read_text(encoding="utf-8")
    domains: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        domains.add(stripped)
    return frozenset(domains)


@lru_cache(maxsize=1)
def _free_mail_domains() -> frozenset[str]:
    return _load_domain_list("free_mail.txt")


@lru_cache(maxsize=1)
def _disposable_domains() -> frozenset[str]:
    return _load_domain_list("disposable.txt")
