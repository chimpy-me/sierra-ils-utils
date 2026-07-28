# Reads & IDs

How to fetch complete records, and how the API's record identifiers relate to the underlying
database.

## `fields=,` returns all fields; allow-lists may 400

**Behavior:** Passing `params={"fields": ","}` (a bare comma) makes a `GET` return **all** available
fields — `varFields`, `fixedFields`, `phones`, etc. Without it, you get a minimal response. An
explicit allow-list of field names is risky: some valid-sounding names cause a `400` (`Invalid
parameter : <field> is not a valid field ...`) depending on what the deployment has materialized.

**"All" is not literal — `deletedDate` is accepted by name but omitted from `fields=,`.** On
`GET bibs`, `fields=,` returns 27 keys and `deletedDate` is not among them, yet
`fields=id,deletedDate` returns it happily. So `fields=,` means "all fields of a live record",
not "every field the endpoint will serve". Anything you need for a *deleted* record must be
named explicitly.

**Type:** By design (the `fields=,` form is undocumented; allow-list rejection is
deployment-specific; the `deletedDate` omission is consistent with `fields=,` projecting the
live-record model).

**How to handle:** Use `fields=,` whenever you need the full record (for example, before a
GET-modify-PUT). Avoid building explicit allow-lists — they're deployment-specific landmines.
But **do not assume `fields=,` covers delete-related fields**: pair it with an explicit
`fields=id,deletedDate` call for the deleted side (see
[Change polling → `fields=,` is rejected on a `deleted=true` query](change-polling.md)).

```python
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})

# `deletedDate` must be named — it is NOT in the fields=, projection
client.request("GET", "bibs", params={"fields": "id,deletedDate", "deleted": "true"})
```

**How we know:** The `fields=,` trick has been relied on across multiple projects; separately, a
plausible-looking field name returned `400` on one deployment's patron model. The `deletedDate`
omission was measured on sierra-test 2026-07-27: enumerating every candidate bib field found 26
accepted by name, of which `deletedDate` was the only one missing from the `fields=,` response
(`holdings` was the sole outright `400`).

## `isRequestable` costs ~56× more per record than any other bib field

**Behavior:** On `GET bibs`, including `isRequestable` in the projection raises per-record latency
from ~1.3 ms to **~73 ms** — roughly 56×. Every other field measured (including the fat ones like
`varFields`) costs ≤2.2 ms/rec. The field evaluates hold/request rules per bib, so Sierra does real
work to answer it; bytes are not the issue, computation is.

**Type:** By design (it is a computed field, not a stored one).

**How to handle:** Leave `isRequestable` out of any bulk read. On a full-catalog sweep the
difference is the difference between a coffee break and two days: a ~2.19M-bib harvest extrapolates
to **~2.7 h** without it and **~48.6 h** with it, from the same page size and the same 25 other
fields. If you need requestability for a *specific* bib, ask for it on that one record. The same
caution likely applies to other computed fields — measure before adding one to a sweep.

```python
# ❌ one field turns a ~3-hour catalog sweep into a ~2-day one
params = {"fields": ",", "id": "[1000001,]", "limit": 1000}

# ✅ name the fields you want and omit the computed ones
FIELDS = "id,updatedDate,title,author,fixedFields,varFields,locations,copies,available"
params = {"fields": FIELDS, "id": "[1000001,]", "limit": 1000}
```

**How we know:** Probed against sierra-test 2026-07-27, isolating one field at a time over a fixed
base of `id,updatedDate,title` (page of 200): base 1.3 ms/rec · `+locations` 2.2 · `+varFields` 2.1
· `+fixedFields` 1.2 · `+copies`/`available`/`orders`/`volumes`/`items` 0.7–0.8 ·
**`+isRequestable` 73.4**. Timings are from a test deployment and will differ on prod; the ratio is
the durable signal.

## The item-type REST field is `itemType`, not `itype`

**Behavior:** On `GET items`, requesting `fields=itype` returns `400 Invalid parameter` — even though
`itype` is what the SQL side calls it and the item's `fixedFields` I-TYPE slot is `61`. The REST field
name is **`itemType`**, and it returns a *label* string (e.g. `"Juvenile Book"`), not the numeric
I-TYPE code. The raw integer code is only reachable via `fields=fixedFields` (slot `61`) — which also
returns the entire `fixedFields` block, including `66` (patron record id) and `67` (checkout) on a
checked-out item.

**Type:** By design (a REST field name doesn't always match the SQL/`fixedFields` name for the same
datum).

**How to handle:** Request `itemType` for the human label. If you need the numeric code *and* are
keeping patron PII off your surface, you can't take it from `fixedFields` without also pulling 66/67 —
derive the code from a reference-dim join on the label instead, or accept the label. General rule:
never assume a field's SQL or `fixedFields` name is its REST name; probe before trusting an allow-list.

```python
# ❌ 400 Invalid parameter — `itype` is the SQL / fixedFields name, not the REST field name
client.request("GET", "items", params={"fields": "id,itype"})

# ✅ 200 — the REST field is `itemType`, and it returns a LABEL, not the numeric code
resp = client.request("GET", "items", params={"fields": "id,itemType"})
resp.json()["entries"][0]           # -> {"id": "...", "itemType": "Juvenile Book"}

# The numeric I-TYPE code lives only in fixedFields slot 61 — but requesting fixedFields
# returns the WHOLE block, including patron PII (slots 66/67) on a checked-out item.
resp = client.request("GET", f"items/{record_num}", params={"fields": "fixedFields"})
resp.json()["fixedFields"]["61"]    # the I-TYPE code slot (block also carries 66/67)
```

**How we know:** Probed against sierra-test 2026-07-23: `fields=id,itype` → `400 Invalid parameter`;
`fields=id,itemType` → `200` with `{"id": "...", "itemType": "Juvenile Book"}`. A bib+item harvest that
requested `itype` silently sealed **0 items** — the 400 was swallowed as an empty result set.

## "Ghost records": GET 200 but PUT 404

**Behavior:** Some records return `200` to a `GET` but `404` (`Patron record not found`) to a `PUT`.
They're visible in the database view and readable, but not writable through the API.

**Type:** Bug-or-quirk (likely soft-deleted or otherwise inconsistent records).

**How to handle:** Treat a `404` on PUT as a **non-fatal skip**, even when a prior GET succeeded. A
successful GET does not guarantee the PUT will work.

**How we know:** Individual records returned `200` on GET and `404` on PUT during side-effect testing
and again during a large batch — a small but real fraction.

## API `id` = `record_num`, not the database primary key

**Behavior:** The REST API's `id` field is the record's **record number** (the human-facing number,
also used in URL paths), **not** the database's internal primary key. In the SQL views these are two
different columns.

**Type:** By design.

**How to handle:** Use the API `id` (the record number) in request paths (`patrons/{record_num}`).
When joining API data to the database, map the API `id` to the record-number column — not to the
internal primary-key column. The two are easy to confuse because both are large integers.

**How we know:** Joining API results to the database on the wrong column silently returns nothing;
mapping API `id` → the record-number column fixes it.

## Multiple values packed into one varField

**Behavior:** A single varField's `content` sometimes holds **several values separated by commas**
(for example, two email addresses in one field) rather than one value per varField.

**Type:** Data quality.

**How to handle:** Split on the delimiter before processing, and rejoin after filtering. Anchored
regex (`^...$`) over the whole field will miss values that aren't first or last.

```python
def split_values(content: str) -> list[str]:
    return [v.strip() for v in (content or "").split(",") if v.strip()]
```

**How we know:** In a large patron dataset, a meaningful number of email varFields held
comma-separated lists; treating each varField as a single value produced wrong classifications.

## varField content length ceiling is ≥ 8000 chars

**Behavior:** A varField's `content` accepts and stores **at least 8000 characters** verbatim — far
more than you'd expect for a "note" field.

**Type:** By design.

**How to handle:** Length is rarely the constraint. Keep system-written notes concise for human
readability rather than because of an API limit; the ceiling is high enough that it's effectively a
non-issue for normal use.

**How we know:** A ladder test (100 → 8000 chars) on a test record stored every size verbatim with no
truncation.

## The 50 on an enumerated `id` list is the *default page size* — set `limit`

**Behavior:** When you fetch several records by listing their ids — `id=1001,1002,1003,…` — and you
do **not** pass `limit=`, Sierra returns at most **50** records and silently drops the rest. No error,
no warning: a 51-id request returns 50 and looks identical to a valid one.

The 50 is Sierra's **default page size**, not a property of the id-list form. Setting `limit=` lifts
it: `id=<251 ids>&limit=251` returns all 251. This holds on every surface tested — `items`, `volumes`,
`bibs`, and `bibs/marc` alike. There is **no MARC-specific 50-cap**, and no per-resource carve-out.

`limit` governs both request forms. The real difference between an enumerated list and a range
(`id=[<start>,<end>]`) is not a cap but **throughput** — see *How to handle*.

> **Corrected 2026-07-28.** This card previously stated the 50 was a hard cap on the enumerated
> id-list form that `limit` could not lift, and advised chunking into ≤50-id requests. That was wrong.
> The original observation ("a 51-id request returned 50") did not record whether `limit` was set —
> it wasn't, and the default page size fully explains it. The error propagated: one downstream tenant
> chunked at 50 for no reason, and another invented an unsupported "the 50-cap is bibs/marc-only"
> justification for batching at 250 (a correct decision reached by wrong reasoning).

**Type:** By design (the default page size is undocumented, and the silent truncation when you exceed
it without setting `limit` is the trap).

**How to handle:** When enumerating ids, **always set `limit` ≥ the number of ids you send**, and
**assert you received every id back**. Treat a response holding exactly the page size with ids missing
as a truncation, not as "those records are deleted" — absent-means-deleted is a common inference, and
a silent truncation is indistinguishable from a mass delete unless you check.

For a bulk read across an id span, still prefer a **range + `limit`**: one `id=[lo,hi]&limit=2000` call
does the work of forty 50-id calls, and for MARC the two-phase `bibs/marc` range sweep (see *Change
polling*). That advice is about per-request overhead, not about a cap. Don't push `limit` past ~2000.

**How we know:** Probed against a production Sierra v6 deployment, 2026-07-28, on `items`, `volumes`,
`bibs` and `bibs/marc`. Each surface was sent the same id set three ways, after a self-test that sent
51 ids with an explicit `limit=50` and confirmed exactly 50 came back (so the probe could demonstrably
detect a truncation before any verdict was read):

| request | records returned |
|---|---|
| 51 ids, no `limit` | 50 — and the dropped id is the **last** requested, i.e. ordinary page truncation |
| 51 ids, `limit=51` | 51 |
| 251 ids, `limit=251` | 251 |

Identical on all four surfaces. For `bibs/marc` the counts were parsed out of the downloaded `.mrc`
(ids read from `907$a`) rather than taken from the summary's `outputRecords`, since a self-reported
count cannot evidence the absence of silent drops. `limit` was not probed beyond 251; the ~2000
ceiling documented in *Change polling* is untested here.

The throughput finding is unaffected and still holds: a production MARC backfill that switched from
50-id enumerated batches to 2000-wide range pages went from **~100 records/min to ~55,000 records/min**
against the *same* catalog. The bottleneck was never Sierra's MARC assembly; it was per-request
overhead paid once per 50 records instead of once per 2000. For a cold bulk read, **make pages bigger,
not threads more** — raising concurrency on the id-list form only multiplied timeouts.
