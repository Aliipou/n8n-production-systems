"""HTTP health, INTERNAL_API_TOKEN auth, normalize and score endpoints."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

TOKEN = "test-internal-token-p01"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("INTERNAL_API_TOKEN", TOKEN)
    monkeypatch.setenv("MX_CHECK", "false")
    from p01_backend.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_normalize_rejects_missing_token(client: TestClient) -> None:
    response = client.post(
        "/v1/leads/normalize",
        json={"email": "matti@nordic-fabriken.test", "name": "Matti Testinen"},
    )
    assert response.status_code == 401


def test_score_rejects_wrong_token(client: TestClient) -> None:
    response = client.post(
        "/v1/score",
        headers={"INTERNAL_API_TOKEN": "nope"},
        json={"intent": "demo_request"},
    )
    assert response.status_code == 401


def test_normalize_fi_and_plus_358(client: TestClient) -> None:
    response = client.post(
        "/v1/leads/normalize",
        headers={"INTERNAL_API_TOKEN": TOKEN},
        json={
            "name": "Matti Testinen",
            "email": "  Matti.Testinen@Nordic-Fabriken.TEST  ",
            "phone": "+358 40 123 4567",
            "message": "Tämä on kiireellinen pyyntö.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email_normalized"] == "matti.testinen@nordic-fabriken.test"
    assert body["language"] == "fi"
    assert body["phone_e164"] == "+358401234567"
    assert body["is_free_mail"] is False


def test_normalize_sv_and_free_mail(client: TestClient) -> None:
    response = client.post(
        "/v1/leads/normalize",
        headers={"INTERNAL_API_TOKEN": TOKEN},
        json={
            "name": "Åsa Exempelsson",
            "email": "asa@freebox.test",
            "phone": "0401234567",
            "message": "Vi vill boka en demo nästa vecka.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "sv"
    assert body["is_free_mail"] is True
    assert body["phone_e164"] == "+358401234567"
    assert body["company_domain"] is None


def test_score_ignores_route_in_body(client: TestClient) -> None:
    response = client.post(
        "/v1/score",
        headers={"INTERNAL_API_TOKEN": TOKEN},
        json={
            "company_size": "51-200",
            "industry": "saas",
            "budget_range": "50k+",
            "timeline": "now",
            "intent": "spam",
            "route": "sales",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "archive"
    assert body["score"] == 80
    assert body["breakdown"]["ai_qualification"] <= 20
