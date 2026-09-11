from __future__ import annotations

from review_ui.decisions import (
    CLAIM_DECISION_SQL,
    INSERT_AUDIT_SQL,
    PENDING_STATUS,
    already_decided,
    rowcount_for_claim,
)


def test_claim_sql_updates_only_pending_and_returns() -> None:
    sql = " ".join(CLAIM_DECISION_SQL.split())
    assert "UPDATE ops.review_queue" in sql
    assert "AND status = 'pending'" in sql
    assert "RETURNING" in sql
    assert "WHERE id = %(id)s" in sql


def test_audit_sql_inserts_human_actor() -> None:
    sql = " ".join(INSERT_AUDIT_SQL.split())
    assert sql.startswith("INSERT INTO ops.audit_log")
    assert "'human'" in sql
    assert "UPDATE" not in sql


def test_already_decided_from_returning_rowcount() -> None:
    assert already_decided(0) is True
    assert already_decided(1) is False


def test_pending_claim_then_second_decision_is_noop() -> None:
    status = PENDING_STATUS
    first = rowcount_for_claim(status)
    assert already_decided(first) is False
    status = "approved"
    second = rowcount_for_claim(status)
    assert second == 0
    assert already_decided(second) is True


def test_rowcount_for_missing_or_non_pending() -> None:
    assert rowcount_for_claim(None) == 0
    assert rowcount_for_claim("rejected") == 0
    assert rowcount_for_claim("expired") == 0
    assert rowcount_for_claim("pending") == 1


def test_in_memory_queue_second_update_keeps_first_status() -> None:
    queue = {"item-1": "pending"}
    first = rowcount_for_claim(queue["item-1"])
    assert first == 1
    queue["item-1"] = "approved"
    second = rowcount_for_claim(queue["item-1"])
    assert already_decided(second) is True
    assert queue["item-1"] == "approved"
