# 0003. At-least-once delivery, not exactly-once

## Context

After insert, something still has to run handlers. Processes crash after a side effect and before `status = processed`. Visibility timeout will dispatch again.

## Decision

Say "at-least-once delivery with idempotent handlers". Never "exactly-once". Handlers insert `p03.processed_effects` (`effect_key` primary key) before emails, fulfilment rows, or CRM writes. A second delivery sees the key and skips.

## Alternatives

Exactly-once by holding a lock until the handler finishes. Rejected: locks die with the process; providers still retry; it invites false claims.

Dedup only at the inbox and assume one dispatch. Rejected: dispatcher kill (F12) re-delivers on purpose.

## Consequences

Duplicate HTTP 200 from ingress is success. Duplicate handler runs must be harmless. Tests cover concurrent inbox inserts now; effect-key tests land with the handlers.
