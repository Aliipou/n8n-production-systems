# Grafana provisioning

`datasources/` and `dashboards/` are loaded from this tree at container
start (`GF_PATHS_PROVISIONING`). Nothing here is created by clicking in
the Grafana UI.

Alert rules for P04 live in Prometheus (`prometheus/alerts.yml`), not in
Grafana unified alerting. The `[P04] Incident Handler` workflow (not in
this skeleton) is the Alertmanager webhook receiver.
