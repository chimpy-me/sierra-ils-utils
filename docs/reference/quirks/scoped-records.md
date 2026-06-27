# Scoped records (`campus_code`)

In a shared or consortium Sierra, the database holds records for more than one agency. The REST API
shows you only the host library's own slice — which surprises you the first time you reconcile an API
harvest against a raw SQL count.

## `GET items?deleted=false` returns only the host's own records (`campus_code = ''`)

**Behavior:** A full enumeration of `items?deleted=false` returns only the records the host library
*owns* — the ones whose `sierra_view.record_metadata.campus_code` is the empty string. In a
multi-agency deployment the same `record_metadata` view (`record_type_code='i'`,
`deletion_date_gmt IS NULL`) also contains **scoped/virtual item records** for partner agencies under
*non-blank* `campus_code` values. Those scoped records are **not** returned by the REST items
endpoint, even though they are non-deleted and look identical to a count over the SQL view. The same
applies to the other record types that participate in scoping.

This is also why `record_num` is **not unique** in `record_metadata`: one record number can appear once
per scope (the host's blank-campus row plus one row per agency that has a scoped copy), so a naive
`COUNT(*)` over the view over-counts relative to `COUNT(DISTINCT record_num)`, and *both* over-count
relative to what REST returns.

**Type:** By design (the REST API is scoped to the host record set).

**How to handle:** When you reconcile a REST item (or bib) harvest against the SQL views, filter the
SQL side to `campus_code = ''` before comparing — otherwise you will chase a phantom gap. Compare
**sets, not counts**: anti-join distinct API `id` against distinct `record_num`, because the SQL-side
`record_num` non-uniqueness and the `record_metadata → item_record` join fan-out both inflate any
count-based decomposition. Don't expect REST to expose partner-agency scoped records at all; if you
need them, they come from SQL (or possibly a per-`id` `GET items/{record_num}` — confirm on your
deployment). Scoped record numbers can fall **outside** the host's own record-number range, so a
range/keyset walk of the host scope will never reach them — that is correct, not a truncation bug.

```sql
-- The REST items?deleted=false universe == the host's own (blank-campus) records:
SELECT count(DISTINCT record_num)
FROM sierra_view.record_metadata
WHERE record_type_code = 'i'
  AND deletion_date_gmt IS NULL
  AND campus_code = '';     -- omit this line and the count will exceed what REST returns
```

**How we know:** On one production consortium deployment, a complete keyset harvest of
`items?deleted=false` captured **4,815,679** item records. The SQL view had **5,185,806** distinct
non-deleted type-`i` `record_num`s — ~370k (~7%) more. A set anti-join (not counts) settled it: every
captured record existed in SQL (`bronze − SQL = 0`), the entire 370,127-record gap was **non-blank
`campus_code`** (≈200 partner agencies), and the distinct `record_num` count for `campus_code = ''`
was **4,815,679 — exactly equal, to the record, to the REST capture.** The gap records spanned record
numbers from `5` to `38,419,702`, well outside the host's own `1,000,002–13,194,349` item-number
range. Suppression was ruled out separately (suppressed host records *are* returned inline — see
[Suppression](suppression.md)); the axis was scope, not suppression.
