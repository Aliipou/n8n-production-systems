# Failure modes (P03 ingress slice)

Only rows with a test in this folder are listed as handled.

| ID | Scenario | Expected | Test |
|---|---|---|---|
| F01 | Provider retries an event | 200, one row | `ingress/server_test.go` `TestHookDuplicateOnConflict` |
| F02 | Concurrent duplicates | One row | `TestConcurrentDuplicates`, `TestMemoryStoreConcurrentDuplicates` |
| F03 | Bad signature | 401, nothing stored | `TestHooksTable` `*_bad_signature` |
| F04 | Timestamp outside tolerance | 401 | `TestHooksTable` stripe and custom stale cases |
| F05 | Body over 1 MB | 413 | `TestHooksTable/oversize_body` |
| F06 | Unknown source | 404 | `TestHooksTable/unknown_source` |
| F11 | Inbox unavailable | 503 | `TestStoreErrorReturns503` |

Not handled here (need dispatcher, n8n, or chaos): F07 unknown type, F08 n8n down drain, F09 handler failure replay, F10 out-of-order upsert, F12 dispatcher kill, F13 replay processed, F14 three dispatcher replicas.
