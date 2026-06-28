# TODO

## Harvest patterns — explanation page (`docs/explanation/`)

Add a Diátaxis **explanation** page documenting the Sierra *harvest patterns* proven in the
chimpy-lake harvest-core convergence (these are patterns built *on* the API — explanation, not
endpoint reference, so they do **not** belong in `reference/`):

- **Watermark never advances past a failed fetch** — a failure-aware `updatedDate` high-water
  mark holds the line below the earliest failed id and lets the next overlap window re-sweep,
  never skip.
- **Orphan ledger: "empty" vs "failed"** — distinguish a known-orphan (record legitimately yields
  nothing; record it, never re-try blindly) from a transient failure (must hold the watermark).
- **Two independent cursors** — the `deletedDate` delete cursor advances (or is HELD on failure)
  on its own, never derived from the `updatedDate` watermark; the delete phase is non-fatal.
- **Reappear/delete ordering guard** — run the delete poll *after* ingest and skip ids the
  change poll returned live this run, so a just-reappeared record is never tombstoned.
- **Reconcile tombstone tripwire** — bound the blast radius if a source-of-truth is mis-scoped
  (e.g. the `campus_code` host-scope subtlety already in the scoped-records quirk page).

Source: chimpy-lake `chimpy_lake.sierra` harvest-core (design §1–§13). Cross-link the existing
`change-polling` / `scoped-records` quirk pages. Tracked on the chimpy-lake ROADMAP under
"Sierra harvest-core convergence".

## Audit Logging Feature

Add exportable audit logging for tracking API calls, especially mutations.

### What to capture

For each API call:
- Timestamp
- Method + endpoint
- Request params/body (sanitized - no credentials)
- Response status code
- Response body (or summary/ID for large responses)
- Duration
- Session/correlation ID

### API Shape Options

**Option 1: Callback/Hook**
```python
def my_audit_handler(event: AuditEvent):
    # Write to file, sqlite, send to logging service, etc.
    print(event.to_json())

client = SierraAPI(..., audit_callback=my_audit_handler)
```

**Option 2: Built-in collector with export**
```python
client = SierraAPI(..., audit=True)

# ... do work ...

# Export options
client.audit_log.to_jsonl("session_2024-01-19.jsonl")
client.audit_log.to_sqlite("audit.db")
client.audit_log.entries  # List[AuditEvent]
```

**Option 3: Context manager for scoped sessions**
```python
async with client.audited_session("bulk-holds-job") as session:
    items = await v6_create_list_query(session, ...)
    # ... mutations ...

# session.audit_log available after
```

### Event Structure

```python
@dataclass
class AuditEvent:
    timestamp: datetime
    session_id: str
    method: str
    endpoint: str
    params: dict | None
    request_body: dict | None  # Sanitized
    status_code: int
    response_summary: str  # e.g., "Created item 12345" or error message
    duration_ms: float

    def to_dict(self) -> dict: ...
    def to_json(self) -> str: ...
```

### Open Questions

1. **Granularity**: Should audit capture every HTTP call, or only "significant" ones (mutations, queries)?
2. **Sensitive data**: Should we auto-redact patron info, or leave that to the consumer?
3. **Storage**: Prefer in-memory + export, or streaming to a destination?
4. **Primary use case**: Post-hoc analysis of what a script did, or real-time monitoring?
