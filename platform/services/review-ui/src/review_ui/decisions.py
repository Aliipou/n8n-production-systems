from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

PENDING_STATUS = "pending"

CLAIM_DECISION_SQL = """
UPDATE ops.review_queue
SET
    status = %(status)s,
    decided_at = now(),
    decided_by = %(decided_by)s,
    decision = %(decision)s::jsonb
WHERE id = %(id)s
  AND status = 'pending'
RETURNING
    id,
    project,
    kind,
    subject_id,
    payload,
    status,
    created_at,
    decided_at,
    decided_by,
    decision,
    callback_workflow_id
"""

LIST_PENDING_SQL = """
SELECT
    id,
    project,
    kind,
    subject_id,
    payload,
    status,
    created_at,
    callback_workflow_id
FROM ops.review_queue
WHERE status = 'pending'
ORDER BY kind ASC, created_at ASC
"""

GET_ITEM_SQL = """
SELECT
    id,
    project,
    kind,
    subject_id,
    payload,
    status,
    created_at,
    decided_at,
    decided_by,
    decision,
    callback_workflow_id
FROM ops.review_queue
WHERE id = %(id)s
"""

INSERT_AUDIT_SQL = """
INSERT INTO ops.audit_log (
    actor_type,
    actor_id,
    project,
    action,
    subject_type,
    subject_id,
    before,
    after,
    reason
) VALUES (
    'human',
    %(actor_id)s,
    %(project)s,
    %(action)s,
    'review_queue',
    %(subject_id)s,
    %(before)s::jsonb,
    %(after)s::jsonb,
    %(reason)s
)
"""


def already_decided(returning_rowcount: int) -> bool:
    """True when UPDATE ... WHERE status='pending' RETURNING matched no row."""
    return returning_rowcount == 0


def rowcount_for_claim(current_status: str | None) -> int:
    """Rowcount of UPDATE ... WHERE status='pending' for a single id."""
    if current_status == PENDING_STATUS:
        return 1
    return 0


def decision_body(
    *,
    review_id: UUID,
    status: str,
    decided_by: str,
    reason: str | None,
    project: str | None,
    kind: str | None,
    subject_id: str | None,
    callback_workflow_id: str | None,
) -> dict[str, Any]:
    return {
        "callback_workflow_id": callback_workflow_id,
        "decided_by": decided_by,
        "id": str(review_id),
        "kind": kind,
        "project": project,
        "reason": reason,
        "status": status,
        "subject_id": subject_id,
    }


def audit_action(status: str) -> str:
    if status == "approved":
        return "review.approve"
    if status == "rejected":
        return "review.reject"
    raise ValueError(f"unsupported decision status: {status}")


def audit_payloads(
    *,
    status: str,
    decided_by: str,
    reason: str | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    before: dict[str, Any] = {"status": PENDING_STATUS}
    after: dict[str, Any] = {
        "decided_by": decided_by,
        "reason": reason,
        "status": status,
    }
    return before, after
