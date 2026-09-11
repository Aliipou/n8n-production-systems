# P01 failure modes

From `docs/specs/01-lead-qualification.md` section 8. Each row names the test or chaos script that will prove it. A row is not handled until that test exists and passes.

Intake and CRM e2e tests start at P01-T08. They are listed here as the intended evidence, not as passing tests.

Unit tests that exist now:

- Scoring overrides and caps: [`../backend/tests/test_score.py`](../backend/tests/test_score.py) (covers the score and route parts of F07)
- Normalize Finnish/Swedish names, +358, free-mail: [`../backend/tests/test_normalize.py`](../backend/tests/test_normalize.py)
- Internal token on `/v1/leads/normalize` and `/v1/score`: [`../backend/tests/test_api.py`](../backend/tests/test_api.py)

| ID | Scenario | Expected behaviour | Test | Status |
|---|---|---|---|---|
| F01 | Same submission delivered twice concurrently | One lead, one submission, one CRM upsert; second request gets 200 duplicate | [`test_concurrent_duplicate`](../tests/e2e/test_concurrent_duplicate.py) | e2e not written |
| F02 | Same person submits again three days later | Lead updated, submission recorded, no second first-contact email, owner notified | [`test_returning_lead`](../tests/e2e/test_returning_lead.py) | e2e not written |
| F03 | Invalid email syntax | 400, nothing stored | [`test_invalid_email`](../tests/e2e/test_invalid_email.py) | e2e not written; normalize unit test flags `email_invalid` |
| F04 | Disposable email domain | Stored as `invalid`, no email, no CRM | [`test_disposable_domain`](../tests/e2e/test_disposable_domain.py) | e2e not written; normalize unit test sets `is_disposable` |
| F05 | Honeypot filled | 202 returned (no signal to bots), stored as `spam`, nothing else happens | [`test_honeypot`](../tests/e2e/test_honeypot.py) | e2e not written |
| F06 | Enrichment 500 or timeout | Continues with unknown values, warn log | [`test_enrichment_down`](../tests/e2e/test_enrichment_down.py) | e2e not written |
| F07 | LLM timeout or invalid JSON twice | Deterministic score without AI points, route capped at nurture, flagged | [`test_llm_failure_fallback`](../tests/e2e/test_llm_failure_fallback.py) | e2e not written; score unit tests cover `llm_status=failed` |
| F08 | Prompt injection in message | Route and score equal the baseline for the same lead without the injection text; `injection_suspected` stored | [`test_prompt_injection`](../tests/e2e/test_prompt_injection.py) | e2e not written |
| F09 | CRM 500 or timeout | Short retries, then DLQ; recovered by DLQ Retrier after the mock heals; one contact created | [`test_crm_outage_recovery`](../tests/e2e/test_crm_outage_recovery.py) | e2e not written |
| F10 | CRM 429 with Retry-After | Waits as instructed; request count stays within limit | [`test_crm_rate_limit`](../tests/e2e/test_crm_rate_limit.py) | e2e not written |
| F11 | CRM 401 | No retry, alert, leads stay pending | [`test_crm_auth_failure`](../tests/e2e/test_crm_auth_failure.py) | e2e not written |
| F12 | Lead already contacted in CRM | No automated email, owner notified | [`test_already_contacted`](../tests/e2e/test_already_contacted.py) | e2e not written |
| F13 | Bounce signal | Status bounced, suppressed, follow-ups cancelled | [`test_bounce`](../tests/e2e/test_bounce.py) | e2e not written |
| F14 | Unsubscribe link used | Suppressed; next follow-up not sent | [`test_unsubscribe`](../tests/e2e/test_unsubscribe.py) | e2e not written |
| F15 | Reply or booking signal | Follow-ups cancelled, CRM updated | [`test_booking_stops_sequence`](../tests/e2e/test_booking_stops_sequence.py) | e2e not written |
| F16 | Reviewer rejects draft | Nothing sent, audit record | [`test_reject_draft`](../tests/e2e/test_reject_draft.py) | e2e not written |
| F17 | Draft pending over 24 h | Reminder notification; never auto-sent | [`test_review_reminder`](../tests/e2e/test_review_reminder.py) | e2e not written |
| F18 | SMTP down at send time | Message stays unsent, retried via DLQ, never sent twice | [`test_smtp_outage_no_double_send`](../tests/e2e/test_smtp_outage_no_double_send.py) | e2e not written |
| F19 | Worker killed during Qualify Lead | Reconcile job re-runs the lead; idempotent steps mean no duplicates | [`worker-kill-p01`](../scripts/chaos/worker-kill-p01) | chaos script not written |
| F20 | Finnish and Swedish leads | Classification works; email in the lead's language | [`test_multilingual`](../tests/e2e/test_multilingual.py) | e2e not written; normalize unit tests cover fi/sv names and +358 |
