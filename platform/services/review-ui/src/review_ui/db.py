from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from review_ui.decisions import (
    CLAIM_DECISION_SQL,
    GET_ITEM_SQL,
    INSERT_AUDIT_SQL,
    LIST_PENDING_SQL,
    already_decided,
    audit_action,
    audit_payloads,
)

LOGGER = logging.getLogger("review_ui")


class DatabaseUnavailable(Exception):
    """Postgres is not configured or not reachable. The process still runs."""


def _connect(database_url: str) -> psycopg.Connection[Any]:
    if not database_url:
        raise DatabaseUnavailable("DATABASE_URL is not set")
    try:
        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=3,
        )
    except psycopg.Error as exc:
        raise DatabaseUnavailable(f"database connection failed: {exc}") from exc


def list_pending(database_url: str) -> list[dict[str, Any]]:
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(LIST_PENDING_SQL)
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_item(database_url: str, review_id: UUID) -> dict[str, Any] | None:
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(GET_ITEM_SQL, {"id": review_id})
            row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def apply_decision(
    database_url: str,
    *,
    review_id: UUID,
    status: str,
    decided_by: str,
    reason: str | None,
) -> dict[str, Any] | None:
    """Claim a pending row, write audit, return the claimed row.

    Returns None when already_decided (0 rows from RETURNING).
    """
    decision = {"reason": reason, "status": status}
    before, after = audit_payloads(
        status=status,
        decided_by=decided_by,
        reason=reason,
    )
    claimed: dict[str, Any] = {}
    with _connect(database_url) as conn:
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        CLAIM_DECISION_SQL,
                        {
                            "status": status,
                            "decided_by": decided_by,
                            "decision": json.dumps(decision),
                            "id": review_id,
                        },
                    )
                    row = cur.fetchone()
                    if already_decided(cur.rowcount):
                        LOGGER.info(
                            json.dumps(
                                {
                                    "event": "review_already_decided",
                                    "id": str(review_id),
                                }
                            )
                        )
                        return None
                    claimed = dict(row) if row is not None else {}
                    cur.execute(
                        INSERT_AUDIT_SQL,
                        {
                            "actor_id": decided_by,
                            "project": claimed.get("project"),
                            "action": audit_action(status),
                            "subject_id": str(review_id),
                            "before": json.dumps(before),
                            "after": json.dumps(after),
                            "reason": reason,
                        },
                    )
            LOGGER.info(
                json.dumps(
                    {
                        "event": "review_decided",
                        "id": str(review_id),
                        "status": status,
                    }
                )
            )
            return claimed
        except psycopg.Error as exc:
            raise DatabaseUnavailable(f"database write failed: {exc}") from exc


def iter_kinds(
    items: list[Mapping[str, Any]],
) -> Iterator[tuple[str, list[Mapping[str, Any]]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        kind = str(item.get("kind") or "unknown")
        grouped.setdefault(kind, []).append(item)
    for kind in grouped:
        yield kind, grouped[kind]
