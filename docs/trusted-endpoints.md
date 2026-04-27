# Trusted endpoints

The `trusted_endpoints` registry is the SDK's policy edge: which URLs an agent
is allowed to talk to at all. Everything else in the SDK is observation; this
is enforcement.

## Schema

The DDL is embedded and applied lazily on first use:

```sql
CREATE TABLE IF NOT EXISTS trusted_endpoints (
  id              SERIAL PRIMARY KEY,
  org_id          TEXT NOT NULL,
  entry_type      TEXT NOT NULL DEFAULT 'endpoint',
  normalized_url  TEXT NOT NULL,
  display_label   TEXT,
  policy_version  TEXT DEFAULT 'v1',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  revoked_at      TIMESTAMPTZ,
  created_by      TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS trusted_endpoints_org_url
  ON trusted_endpoints(org_id, normalized_url)
  WHERE revoked_at IS NULL;
```

A row is a non-revoked URL trusted for one org. Revocation is soft (set
`revoked_at`); the unique index excludes revoked rows so the same URL can be
re-added later.

`ensure_trusted_endpoints_table(conn)` runs the DDL idempotently. It is also
called automatically by `is_trusted_endpoint`, `list_trusted_endpoints`, and
`check_claim_endpoints_are_trusted` so callers usually do not need to invoke it.

## URL normalization

Every URL is normalized **before** it is read or written:

```python
from provably import normalize_url_for_trust

normalize_url_for_trust("HTTPS://API.Example.COM/v1/data/")
# -> "https://api.example.com/v1/data"
```

Rules:

- Empty / whitespace input -> `""`.
- Scheme and host lowercased.
- Default ports collapsed (`:80` for `http`, `:443` for `https`).
- Path's trailing slash stripped (path-less URLs end up with empty path).
- Query strings and fragments are kept as-is (case-preserving).

Two URLs that normalize to the same string collide on the same row. This is
deliberate — agents should not be able to evade the registry by varying case
or trailing slashes.

## API

```python
from provably import (
    is_trusted_endpoint,
    list_trusted_endpoints,
    check_claim_endpoints_are_trusted,
    ensure_trusted_endpoints_table,
    normalize_url_for_trust,
)
```

### `is_trusted_endpoint(url, org_id, conn) -> bool`

The hot path. Used by the interceptor before every `GET`. Returns `False` for
empty URLs, empty orgs, or URLs that normalize to empty. Otherwise checks for
a non-revoked row matching `(org_id, normalized_url, entry_type='endpoint')`.

### `list_trusted_endpoints(conn, org_id, *, excluded_urls=None, metadata_seeds=None)`

Enumerates the registry for an org. Returns a list of dicts with `url`,
`label`, and (when seed metadata matches) `category`, `risk_level`,
`description`, `expected_response`. `excluded_urls` is a normalized-URL set
the caller wants hidden — typically internal service URLs auto-allowed by the
deployment.

### `check_claim_endpoints_are_trusted(payload, *, postgres_url, org_id_fallback="")`

Used by verifiers (e.g. `agents/cluster_b` in the demo). For every claim that
has a `request_payload.url`, normalizes it and:

1. If `payload.trusted_endpoint_registry` is non-empty, the URL must appear
   in that snapshot. Missing entries raise `ValueError`.
2. The URL must be present in the live `trusted_endpoints` table for the
   payload's `provably_org_id` (or `org_id_fallback` if the payload is
   unattributed). Missing entries raise `ValueError`.

Configuration errors (`postgres_url` empty, org id missing) raise
`RuntimeError`. The function opens its own Postgres connection via
`psycopg2.connect(postgres_url)` and closes it before raising.

This is the only entry point that opens a connection. Everything else takes a
caller-provided `conn`. Issue
[#1](https://github.com/ProvablyAI/provably-python-sdk/issues/1) tracks
unifying the contract so all functions accept an injected connection.

## Enforcement vs warning

v0.1 enforces only on `GET`. The interceptor blocks unknown URLs before any
row reaches `provably_intercepts`. `POST` is recorded but not policed.

There is no soft / warning tier — a missing entry is a hard block. Issue
[#6](https://github.com/ProvablyAI/provably-python-sdk/issues/6) tracks the
policy-tier design (warn vs block, plus cross-org sharing semantics).

## Cross-org sharing

There is none in v0.1. Each org carries its own list. The schema has
`org_id` and `created_by` so a future shared / replica model is possible
without a migration; the API will need additional surface (a "global"
`org_id` value, or a separate read path) before any agent can see another
org's entries.
