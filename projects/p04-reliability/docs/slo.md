# Example SLOs (reference system, not measured)

Every target in this file is an **example** copied from
`docs/specs/04-reliability.md` for a reference system. None of these
figures come from a script run in this repository. They are not promises,
production SLOs, or results.

When a measurement exists, record it in the project README Results
section with value, date, hardware, model, dataset, and script path.
Until then, write "not measured yet". Do not copy the example percentages
into Results.

## Example targets

### P01 lead flow (example)

99% of valid leads reach the CRM within 5 minutes, measured over 28 days.

Valid means the lead passed intake checks (not invalid, not spam). Reach
the CRM means `crm_sync_status = synced` on `p01.leads` (or the P05
tenant copy, when that path is used). The 5 minute clock starts at intake
accept and ends at a successful CRM upsert.

This is an example. Actual time-to-CRM is not measured yet.

### P03 webhook gateway (example)

99.9% of authentic events acknowledged.

99% processed within 2 minutes.

Authentic means signature verification passed. Acknowledged means the
ingress stored the event and returned 2xx only after durable write.
Processed means the dispatcher completed the handler for that event.

These are examples. Acknowledgement rate and processing latency are not
measured yet.

## Error budget (example explanation)

An SLO of 99% over 28 days leaves a 1% error budget in that window: up to
1% of valid items may miss the target before the SLO is considered
exhausted. An SLO of 99.9% leaves a 0.1% error budget.

This paragraph explains the idea. It does not report remaining budget.
Remaining budget is not measured yet.

Alerts below are mapped to these example SLOs so operators know which
page protects which target. Thresholds are spec defaults to tune after
real runs. They are not derived from production traffic.

## Which alerts protect which example SLO

| Example SLO | Alerts that protect it (planned, P04-T06) |
|---|---|
| P01: 99% of valid leads reach CRM within 5 minutes | `WorkflowFailureRateHigh`, `DLQGrowing`, `CircuitOpen`, `WorkersMissing`, `ExporterDown` |
| P03: 99.9% authentic events acknowledged | `HeartbeatStale` (dead man's switch), `WorkersMissing`, `ExporterDown` |
| P03: 99% processed within 2 minutes | `InboxLagHigh`, `DLQGrowing`, `CircuitOpen`, `n8n` restart chaos coverage |

Related planned alerts that do not map 1:1 to the two example SLOs:

- `ReviewQueueStale`: human-queue age, not the P01 CRM timer.
- `HeartbeatStale`: dead man's switch if the monitoring path itself is silent.

Minimum volume belongs on every rate-based alert so one failure at night
does not page anyone. That guard is not written in PromQL yet.
