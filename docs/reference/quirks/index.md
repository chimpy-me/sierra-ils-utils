# The Quirks Catalog

The Sierra REST API behaves in ways its documentation doesn't always mention. This catalog records
the non-obvious behaviors we've hit in real work, so you can plan for them instead of discovering
them mid-batch.

## How to read these entries

Every quirk is a card with the same four lines:

- **Behavior** — what actually happens.
- **Type** — *Bug-or-quirk*, *By design*, or *Data quality*.
- **How to handle** — the workaround or rule of thumb.
- **How we know** — the empirical evidence behind the claim.

!!! warning "Verify on your own deployment"
    These behaviors were observed on specific Sierra deployments (production and test). Versions and
    configuration differ between libraries. Treat each entry as a strong hypothesis to confirm on
    *your* system — and see [Discover quirks yourself](../../explanation/discover-quirks-yourself.md).

!!! note "Provenance: patron-record heavy (bib/harvest coverage growing)"
    Most of the write/side-effect knowledge came from patron-record projects, so the catalog still
    leans that way. The [Change polling](change-polling.md) page begins filling the bib/harvest gap
    (range queries, deletion polling, pagination) from a production bib-harvest project; item- and
    order-specific quirks are still under-represented. Found one?
    [Send it in.](https://github.com/chimpy-me/sierra-ils-utils)

## Quick reference

| Quirk | Type | Page |
|---|---|---|
| PUT `phones` is additive, not replacement | Bug-or-quirk | [Write semantics](write-semantics.md) |
| PUT `varFields` is full replacement | By design | [Write semantics](write-semantics.md) |
| A successful PUT returns `204`, not `200` | By design | [Write semantics](write-semantics.md) |
| `fixedFields` PUT requires `label` beside `value` | By design | [Write semantics](write-semantics.md) |
| PUT rejects ~9 read-only top-level fields | By design | [Write semantics](write-semantics.md) |
| Empty-content varFields are silently dropped on PUT | Bug-or-quirk | [Write semantics](write-semantics.md) |
| `emails`/`phones`/`addresses`/`names` are derived projections | By design | [Write semantics](write-semantics.md) |
| PUT bumps four `fixedFields` timestamps/counters, no opt-out | By design | [Side effects](side-effects.md) |
| GET never bumps; a failed PUT (400) never bumps | By design | [Side effects](side-effects.md) |
| Revisions counter: +2 per REST PUT vs +1 per Desktop save | Bug-or-quirk | [Side effects](side-effects.md) |
| `fields=,` returns all fields; allow-lists may 400 | By design | [Reads & IDs](reads-and-ids.md) |
| The item-type REST field is `itemType`, not `itype` | By design | [Reads & IDs](reads-and-ids.md) |
| "Ghost records": GET 200 but PUT 404 | Bug-or-quirk | [Reads & IDs](reads-and-ids.md) |
| API `id` = `record_num`, not the DB primary key | By design | [Reads & IDs](reads-and-ids.md) |
| Multiple values packed into one varField | Data quality | [Reads & IDs](reads-and-ids.md) |
| varField content length ceiling is ≥ 8000 chars | By design | [Reads & IDs](reads-and-ids.md) |
| Zero-match range query may 404 (`code 107`) — and query shapes disagree | Bug-or-quirk | [Change polling](change-polling.md) |
| `deletedDate` is date-only; `updatedDate` is a full timestamp | By design | [Change polling](change-polling.md) |
| `GET bibs` returns entries ascending by `id` (keyset-paginable) | By design | [Change polling](change-polling.md) |
| `updatedDate` + `id` range filters AND together in one query | By design | [Change polling](change-polling.md) |
| List responses cap at ~2000; detect end by a short page, not `total` | By design | [Change polling](change-polling.md) |
| `deleted=false` hides server-deleted records (they vanish from polls) | By design | [Change polling](change-polling.md) |
| `suppressed` is a read-only boolean on bibs and items | By design | [Suppression](suppression.md) |
| `suppressed=true` filters; suppressed records are otherwise returned inline | By design | [Suppression](suppression.md) |
| Suppression rides in the MARC export — bib `998$e`, item `945$o` | By design | [Suppression](suppression.md) |
| `items?deleted=false` returns only the host's own (`campus_code=''`) records | By design | [Scoped records](scoped-records.md) |
| `record_num` is non-unique in `record_metadata` (one row per scope) | By design | [Scoped records](scoped-records.md) |
| `validate` `caseSensitivity` defaults to `true` — rejects mixed-case identifiers | By design | [Patron validation](patron-validate.md) |
| `validate` checks only the first 8 characters of the PIN | Bug-or-quirk | [Patron validation](patron-validate.md) |

## Discovering quirks yourself

You don't have to take these on faith — every entry is a hypothesis you can confirm on
your own deployment with safe, read-mostly probes. See
[Discovering quirks yourself](../../explanation/discover-quirks-yourself.md) for the method.
