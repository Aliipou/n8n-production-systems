"""Normalize Finnish and Swedish names, +358 phones, free-mail and disposable domains."""

from __future__ import annotations

from p01_backend.normalize import normalize_lead


def test_finnish_name_preserved_and_language_hint() -> None:
    result = normalize_lead(
        {
            "name": "  Matti Testinen  ",
            "email": "matti.testinen@nordic-fabriken.test",
            "company_name": "Nordic Fabriken Oy",
            "message": "Tämä on kiireellinen pyyntö.",
        }
    )
    assert result.name == "Matti Testinen"
    assert result.company_name == "Nordic Fabriken Oy"
    assert result.language == "fi"
    assert result.email_valid is True
    assert result.is_free_mail is False
    assert result.company_domain == "nordic-fabriken.test"


def test_swedish_name_preserved_and_language_hint() -> None:
    result = normalize_lead(
        {
            "name": "Åsa Exempelsson",
            "email": "asa.exempelsson@norrskog-demo.test",
            "message": "Vi vill boka en demo nästa vecka.",
        }
    )
    assert result.name == "Åsa Exempelsson"
    assert result.language == "sv"
    assert result.email_valid is True
    assert result.company_domain == "norrskog-demo.test"


def test_explicit_language_en_wins_over_name() -> None:
    result = normalize_lead(
        {
            "name": "Åsa Exempelsson",
            "email": "asa@norrskog-demo.test",
            "language": "en",
        }
    )
    assert result.language == "en"


def test_plus_358_to_e164() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "phone": "+358 40 123 4567",
        }
    )
    assert result.phone_e164 == "+358401234567"


def test_national_fi_mobile_to_e164() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "phone": "040 123 4567",
        }
    )
    assert result.phone_e164 == "+358401234567"


def test_already_e164_plus_358() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "phone": "+358401234567",
        }
    )
    assert result.phone_e164 == "+358401234567"


def test_email_trim_and_lowercase() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "  Matti.Testinen@Nordic-Fabriken.TEST  ",
        }
    )
    assert result.email_normalized == "matti.testinen@nordic-fabriken.test"
    assert result.email_valid is True


def test_free_mail_invented_domain() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@freebox.test",
        }
    )
    assert result.is_free_mail is True
    assert result.is_disposable is False
    assert result.company_domain is None


def test_post_gratis_is_free_mail() -> None:
    result = normalize_lead({"name": "A", "email": "a@post-gratis.test"})
    assert result.is_free_mail is True


def test_disposable_invented_domain() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "tmp@throwaway-inbox.test",
        }
    )
    assert result.is_disposable is True
    assert result.email_valid is True


def test_invalid_email_syntax() -> None:
    result = normalize_lead({"name": "Matti Testinen", "email": "not-an-email"})
    assert result.email_valid is False
    assert "email_invalid" in result.errors


def test_missing_email() -> None:
    result = normalize_lead({"name": "Matti Testinen", "email": "  "})
    assert result.email_valid is False
    assert "email_missing" in result.errors


def test_invalid_phone() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "phone": "abc",
        }
    )
    assert result.phone_e164 is None
    assert "phone_invalid" in result.errors


def test_empty_phone_is_omitted() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "phone": "  ",
        }
    )
    assert result.phone_e164 is None
    assert "phone_invalid" not in result.errors


def test_website_sets_company_domain() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@freebox.test",
            "website": "https://www.nordic-fabriken.test/contact",
        }
    )
    assert result.is_free_mail is True
    assert result.company_domain == "nordic-fabriken.test"


def test_mx_check_off_accepts_invented_domain() -> None:
    result = normalize_lead(
        {"name": "Matti Testinen", "email": "matti@nordic-fabriken.test"},
        mx_check=False,
    )
    assert result.email_valid is True


def test_finnish_words_without_diacritics() -> None:
    result = normalize_lead(
        {
            "name": "Matti Testinen",
            "email": "matti@nordic-fabriken.test",
            "message": "Tarvitsemme tarjouksen ensi kuussa.",
        }
    )
    assert result.language == "fi"


def test_swedish_national_number_to_e164() -> None:
    result = normalize_lead(
        {
            "name": "Åsa Exempelsson",
            "email": "asa@norrskog-demo.test",
            "phone": "040 123 4567",
        }
    )
    assert result.language == "sv"
    assert result.phone_e164 == "+358401234567"
