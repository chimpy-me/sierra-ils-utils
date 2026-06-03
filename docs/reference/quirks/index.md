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
    *your* system — and see [Discover quirks yourself](#discovering-quirks-yourself).

!!! note "Provenance: patron-record heavy"
    Most of this knowledge came from patron-record projects, so the catalog leans that way today.
    The behaviors are usually general Sierra REST traits, but bib/item/order-specific quirks are
    under-represented for now. Found one? [Send it in.](https://github.com/chimpy-me/sierra-ils-utils)

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
| "Ghost records": GET 200 but PUT 404 | Bug-or-quirk | [Reads & IDs](reads-and-ids.md) |
| API `id` = `record_num`, not the DB primary key | By design | [Reads & IDs](reads-and-ids.md) |
| Multiple values packed into one varField | Data quality | [Reads & IDs](reads-and-ids.md) |
| varField content length ceiling is ≥ 8000 chars | By design | [Reads & IDs](reads-and-ids.md) |

## Discovering quirks yourself

You don't have to take these on faith. The safe way to confirm a behavior on your own deployment:

- Test against a **test/sandbox Sierra** if you have one, or pick clearly **inactive** records.
- Probe with **identical-data** PUTs (send a record's data back unchanged) and **intentionally
  malformed** PUTs — both let you observe side effects without meaningfully altering data.
- **Hash the content fields** before and after to prove the payload is unchanged while you watch
  what Sierra mutates on its own.
- Cross-check against the database (read-only) if you have SQL access.

A runnable, deployment-agnostic version of this probe harness is planned for a later phase of this
guide.
