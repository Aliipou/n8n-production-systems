# Grafana dashboards

This directory is mounted into Grafana as the file-provider path.

It is empty of dashboard JSON on purpose. Spec 04 forbids screenshots or
committed dashboards filled with generated fake metrics. Dashboards are
added here after a real demo run (P04-T05, P04-T13), exported from Grafana
provisioning, with data that came from that run.

Planned dashboards (not in this folder yet):

- Overview: executions per hour, success rate per workflow, p95 duration,
  queue depth, active workers, DLQ, review queue, inbox lag, heartbeat age.
- Per project: P01 leads by route and time to CRM; P02 documents by
  decision; P03 events by source and status.
- Dependencies: calls, errors by class, circuit state per dependency.

Do not invent series, thresholds, or sample values in JSON to make panels
look populated.
