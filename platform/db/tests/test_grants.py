"""Grant tests for schema ops.

Skipped when DATABASE_URL is unset (no local Postgres required for unit CI).
When DATABASE_URL points at database app after dbmate up, UPDATE on
ops.audit_log as role app_backend must fail.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from urllib.parse import quote, urlsplit, urlunsplit

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not set",
)

if DATABASE_URL:
    psycopg = pytest.importorskip("psycopg")
    from psycopg.errors import InsufficientPrivilege
else:
    psycopg = None
    InsufficientPrivilege = Exception

_ACTOR_ID = "plt-t04-grants-test"


def _password_for(role: str) -> str:
    env_names = {
        "n8n_app": "N8N_APP_PASSWORD",
        "app_backend": "APP_BACKEND_PASSWORD",
        "readonly": "READONLY_PASSWORD",
    }
    return os.environ.get(env_names[role], "change-me")


def _url_as_role(role: str) -> str:
    parts = urlsplit(DATABASE_URL)
    hostname = parts.hostname or "127.0.0.1"
    port = f":{parts.port}" if parts.port else ""
    user = quote(role, safe="")
    password = quote(_password_for(role), safe="")
    netloc = f"{user}:{password}@{hostname}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _connect(role: str | None = None):
    assert psycopg is not None
    url = DATABASE_URL if role is None else _url_as_role(role)
    return psycopg.connect(url)


def _insert_audit_row(conn) -> int:
    row = conn.execute(
        """
        INSERT INTO ops.audit_log (
          actor_type, actor_id, project, action, subject_type, subject_id
        )
        VALUES ('system', %s, 'platform', 'test.audit_append_only', 'test', 'plt-t04')
        RETURNING id
        """,
        (_ACTOR_ID,),
    ).fetchone()
    assert row is not None
    conn.commit()
    return int(row[0])


@pytest.fixture
def audit_row_id() -> Iterator[int]:
    with _connect("app_backend") as conn:
        row_id = _insert_audit_row(conn)
    try:
        yield row_id
    finally:
        with _connect() as admin:
            admin.execute(
                "DELETE FROM ops.audit_log WHERE actor_id = %s",
                (_ACTOR_ID,),
            )
            admin.commit()


def test_app_backend_insert_audit_log_succeeds(audit_row_id: int) -> None:
    with _connect("app_backend") as conn:
        found = conn.execute(
            "SELECT id FROM ops.audit_log WHERE id = %s",
            (audit_row_id,),
        ).fetchone()
    assert found is not None
    assert found[0] == audit_row_id


def test_app_backend_update_audit_log_fails(audit_row_id: int) -> None:
    with _connect("app_backend") as conn:
        with pytest.raises(InsufficientPrivilege):
            conn.execute(
                "UPDATE ops.audit_log SET reason = %s WHERE id = %s",
                ("should-fail", audit_row_id),
            )


def test_app_backend_delete_audit_log_fails(audit_row_id: int) -> None:
    with _connect("app_backend") as conn:
        with pytest.raises(InsufficientPrivilege):
            conn.execute(
                "DELETE FROM ops.audit_log WHERE id = %s",
                (audit_row_id,),
            )


def test_n8n_app_update_audit_log_fails(audit_row_id: int) -> None:
    with _connect("n8n_app") as conn:
        with pytest.raises(InsufficientPrivilege):
            conn.execute(
                "UPDATE ops.audit_log SET reason = %s WHERE id = %s",
                ("should-fail", audit_row_id),
            )


def test_readonly_cannot_insert_audit_log() -> None:
    with _connect("readonly") as conn:
        with pytest.raises(InsufficientPrivilege):
            conn.execute(
                """
                INSERT INTO ops.audit_log (actor_type, actor_id, action)
                VALUES ('system', %s, 'test.readonly_insert')
                """,
                (_ACTOR_ID,),
            )
