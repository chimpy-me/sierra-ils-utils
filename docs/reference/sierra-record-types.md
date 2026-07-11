# Record types & data surfaces

Sierra stores everything as **typed records**. Each record has a one-letter
*record type code* and shares a common metadata spine (the `record_metadata`
row: id, creation/updated timestamps, deletion flag, campus scope). Almost
everything you build against Sierra is ultimately "read records of type X,
watch them change, act on some."

There are **two surfaces** onto that data, and knowing which one a given
record type lives on is the single most useful map to carry:

| Surface | What it is | Reach | Contract stability |
|---|---|---|---|
| **REST API** (`/v6/…`) | The vendor's curated HTTP projection | A **subset** of record types + live circulation | Documented, versioned, stable |
| **SQL replica** (`sierra_view.*`) | A read-only Postgres view of the whole database | **Everything** — including internal join/audit tables REST never exposes | Vendor-internal; can shift between Sierra releases |

The REST surface is where you want to be by default: stable, documented, safe
to poll. Drop to SQL only for the things REST *structurally cannot* give you
(see [SQL-only data](#sql-only-data-the-escape-hatch) below).

!!! note "Verify against your own deployment"
    The endpoint availability and the exact set of record type codes are
    **deployment-specific** (Sierra edition, licensed modules, local config).
    Treat the tables below as the shape to expect, then confirm on your own
    system — see [Enumerate your record types](#enumerate-your-own-record-types).

## REST-addressable record types

These are the record types the REST API exposes as first-class, pollable
resources. Each supports the standard read + change-polling patterns (see
[Poll for changed and deleted records](../how-to/poll-for-changes.md)).

| Record type | REST resource | Notes |
|---|---|---|
| Bibliographic | `/bibs` (+ `/bibs/marc`) | The catalog record. MARC available via the two-phase export ([bulk MARC](../how-to/bulk-export-marc.md)). |
| Item | `/items` | Physical/holdable copies; carries status, location, itype. |
| Patron | `/patrons` | Borrower records. Heavy PII — read semantics differ from writes ([write side effects](quirks/side-effects.md)). |
| Order | `/orders` | Acquisitions order records. |
| Volume | `/volumes` | Multi-volume groupings under a bib. |
| Authority | `/authorities` | Authority-controlled headings. |
| Course | `/courses` | Course-reserve records (if the module is licensed). |

## REST-addressable live circulation

Circulation state is exposed by REST as **live queryable resources**, not as
change-polled record types. They reflect *current* state, not an append-only
history:

| Resource | REST resource | Notes |
|---|---|---|
| Holds | `/patrons/{id}/holds`, `/bibs/{id}/holds` | **Current, active** holds only. Cleared/cancelled holds are *not* retrievable here — see below. |
| Checkouts | `/patrons/{id}/checkouts` | Currently checked-out items. |

## Config & reference resources

Lookup tables that resolve codes to human labels. Small, slow-changing, and
usually the first thing a reporting pipeline needs to make item/patron data
legible:

`/branches` · `/itemStatuses` · `/patronTypes` · `/itypes` · `/agencies` ·
`/fixedFields` · `/varFields`

## SQL-only data (the escape hatch)

Some of the most useful operational data has **no REST record-type endpoint**
and is reachable only through `sierra_view`:

| Data | Where | Why REST can't serve it |
|---|---|---|
| Circulation transaction log | `sierra_view` circ-transaction tables | REST exposes *current* checkouts, not the historical event stream. |
| Cleared / cancelled holds | `sierra_view.hold` history + removal tables | REST `/holds` returns only currently-active holds; removed holds are purged from the REST view on a rolling window. |
| Staff / system users | `sierra_view.iii_user` | Not modelled as a REST record type. |
| Internal join & audit tables | `sierra_view.*_record`, `*_record_metadata`, gtype/property tables | Vendor-internal plumbing; no projection into REST. |

The trade-off: SQL sees everything but you're now coupled to a vendor-internal
schema that can change between releases, and much of it is PII-dense. Prefer
REST; reach for SQL deliberately, per-entity, when REST leaves a gap.

## Enumerate your own record types

The authoritative denominator — *what record types actually exist on your
deployment, and how many of each* — is one read-only query against the SQL
replica:

```sql
SELECT record_type_code, count(*) AS n
FROM   sierra_view.record_metadata
GROUP  BY record_type_code
ORDER  BY n DESC;
```

`record_type_code` is the one-letter code (`b` bib, `i` item, `p` patron,
`o` order, `j` volume, `a` authority, …). Running this on your own system is
the fastest way to see the full, real universe you'd be mapping — including
any locally-licensed record types not listed above — and to size each one
before you decide what's worth ingesting.

This is a read-only aggregate (counts, no record contents), safe to run
against any deployment you have read access to.

## See also

- [Poll for changed and deleted records](../how-to/poll-for-changes.md) — the
  read pattern every record type above shares.
- [Discovering quirks yourself](../explanation/discover-quirks-yourself.md) —
  how to confirm any of this empirically on your deployment.
- [Why writes have side effects](../explanation/sierra-rest-thin-projection.md)
  — the thin-projection model that explains the REST-vs-SQL split.
