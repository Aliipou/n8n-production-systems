from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from review_ui.app import create_app
from review_ui.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(
        review_ui_user="reviewer",
        review_ui_password="change-me",
        review_hmac_secret="change-me",
        review_receiver_url="http://n8n-main:5678/webhook/plt/review-decision",
        database_url="",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_without_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "review-ui"}


def test_healthz_without_database(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_redirects_to_reviews(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/reviews"


def test_reviews_requires_basic_auth(client: TestClient) -> None:
    response = client.get("/reviews")
    assert response.status_code == 401


def test_approve_requires_basic_auth(client: TestClient) -> None:
    review_id = UUID("00000000-0000-0000-0000-000000000001")
    response = client.post(f"/reviews/{review_id}/approve")
    assert response.status_code == 401


def test_reject_requires_basic_auth(client: TestClient) -> None:
    review_id = UUID("00000000-0000-0000-0000-000000000001")
    response = client.post(f"/reviews/{review_id}/reject")
    assert response.status_code == 401


def test_reviews_list_shows_error_when_db_missing(client: TestClient) -> None:
    response = client.get("/reviews", auth=("reviewer", "change-me"))
    assert response.status_code == 200
    assert "Could not load the review queue" in response.text
    assert "DATABASE_URL is not set" in response.text
