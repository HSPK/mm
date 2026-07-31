# Organizer control-plane API

Organizer operates only on configured `organizer.media_sources`.  Paths are
resolved before reads or writes; `/organizer/scan` is ad-hoc discovery and
never marks unrelated projection rows missing.  Full reconciliation is
`POST /api/jobs/sync`, which accepts configured roots only.

`GET /api/organizer/items` is paginated (`offset`, `limit`, `query`, `order`,
and optional `kind`) and returns `{items, offset, limit, total}`.  Items expose
an opaque `item_uid` and `revision`.  Use
`PATCH /api/organizer/items/{item_uid}` with the current revision to store a
metadata draft; it does not write NFO unless `write_nfo` is true.

Job creation deduplicates active equivalent payloads and accepts the optional
`Idempotency-Key` header. Terminal statuses include `completed_with_errors`;
cancel requests win races with worker completion. Capabilities and supported
scraper adapters are available from `GET /api/organizer/capabilities`.

## Architectural invariants

### Facts and projections

- Media files and explicitly written sidecars are external facts.
- `organizer_media` is a materialized projection, not a second independent
  source of truth.
- Projection writes use opaque `item_uid` plus optimistic `revision`.
- Scan writes may not overwrite a projection revision committed after that
  scan began.

### Query and command separation

- GET and detail endpoints are pure queries.
- A route whose name suggests reading must never scan, persist, rename, or
  write sidecars.
- Filesystem discovery and every output mutation are explicit commands.
- Normal application catalogs never depend on `organizerRepo`.

### Scan commit protocol

- Ad-hoc scans only discover/update observed paths.
- Missing reconciliation requires a complete configured-root scan.
- A failed, canceled, partial, or non-recursive scan cannot mark unseen
  siblings missing.
- Seen paths are touched independently from projection field updates so a
  concurrent user patch remains visible.

### Jobs and destructive operations

- Active commands hold a database-unique claim derived from their idempotency
  key or canonical payload.
- Status changes are conditional; `canceling` always converges to `canceled`.
- Partial success uses `completed_with_errors` and records per-operation
  outcomes.
- Rename is a journaled saga: completed operations are reflected in the
  projection even when a later operation fails.

### Paths and remote input

- Every read/write path is resolved against configured media roots.
- Output installation uses atomic replacement and does not follow target
  symlinks.
- Remote artwork connections are pinned to validated public IP addresses;
  every redirect is revalidated and response type/size/content are checked.

### Extension points

- Scrapers are registered through `SCRAPER_FACTORIES`.
- Media capabilities declare supported scrapers, outputs, rename, and lyrics
  behavior.
- Adding a source or media type must update a registry/capability test rather
  than introducing a new route-level source-name branch.

### Web client

- Organizer lists are paginated and server-filtered.
- Selection ranges operate on the rows actually displayed.
- Commands are disabled until their durable job reaches a terminal state.
- The browser persists view preferences only, never projection data or
  selected candidates.
- Metadata editors must map every editable field into a revision-checked patch.
