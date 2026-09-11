# mock-llm fixtures

Project LLM fixtures live in the calling project's `fixtures/llm/` directory.
This service directory does not store project responses.

Example path: `projects/p01-lead-qualification/fixtures/llm/*.json`.

Set `MOCK_LLM_FIXTURES_DIR` to that folder. Compose should bind-mount it at
`/fixtures/llm` inside the mock-llm container.

## Lookup

The mock hashes a normalized JSON object of `(model, messages)`:

- UTF-8 SHA-256 of compact JSON with sorted keys
- Payload shape: `{"messages":[{"content":...,"role":...}],"model":"<name>"}`
- Only `role` and `content` are taken from each message

Lookup order:

1. A file named `<hex>.json` in `MOCK_LLM_FIXTURES_DIR`
2. Any other `*.json` file whose `hash` field equals the digest
3. Any other `*.json` file whose `model` and `messages` hash to the digest

The assistant `content` is the JSON value of the file, unless the file is an
object with a `content` or `response` field (those keys are unwrapped).

If nothing matches, the service returns a deterministic object that satisfies
the request `response_format.json_schema.schema` when one is provided.

Do not put secrets or real personal data in fixtures.
