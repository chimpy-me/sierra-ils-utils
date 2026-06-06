# Change polling, ranges & pagination

How to harvest changed and deleted records over time, and how Sierra's range filters and pagination
actually behave. Most of the catalog leans toward patron-record writes; this page is the read/harvest
side, gathered from running an incremental **bib** harvest against a production catalog. The behaviors
are general to any list/range endpoint.

## A zero-match range query can return `404 Record not found` — and not every query shape agrees

**Behavior:** A range query that matches **no records** does not reliably return an empty list. On a
production deployment, `GET bibs?deleted=false&updatedDate=[<window with no changes>]` returns **HTTP
404** with `{"code": 107, ... "name": "Record not found"}`. But the *deleted* variant of the same
shape — `GET bibs?deleted=true&deletedDate=[<window with no deletions>]` — returns **HTTP 200** with
`{"start": 0, "entries": []}`. Same resource, same "zero results," two different status codes.

**Type:** Bug-or-quirk (404-on-empty is a long-standing Sierra trait; the inconsistency *between query
shapes* is the trap).

**How to handle:** Treat `404` + `code 107` as **"zero results," not an error**, for a range/list
poll — otherwise an idle window (no changes, or, more commonly, no deletions) crashes the harvest.
Note that `sierra-ils-utils` returns 4xx responses **verbatim** (it does not raise on them), so you
check `response.status_code` yourself rather than relying on `raise_for_status()`. And don't assume
uniformity — probe the *specific* query shape you depend on.

```python
resp = client.request("GET", url)
if resp.status_code == 404:        # Sierra's "no records match" for a range query
    entries = []
else:
    resp.raise_for_status()
    entries = resp.json().get("entries", [])
```

**How we know:** Read-only probes against a production catalog using far-future date windows
guaranteed to match nothing: the `updatedDate` / `deleted=false` poll returned `404 code 107`; the
`deletedDate` / `deleted=true` poll returned `200 {"start":0,"entries":[]}`.

## `deletedDate` is date-only; `updatedDate` is a full timestamp

**Behavior:** `updatedDate` is a second-granularity datetime (`'2021-10-07T13:52:27Z'`), but
`deletedDate` is **date-only** (`'2023-11-30'`) — no time component, and the time zone is unspecified.

**Type:** By design (an undocumented granularity difference between the two clocks).

**How to handle:** A deletion-tracking cursor must be **day-granular**, with a **≥1-day overlap**
re-sweep — a sub-day "lag" is meaningless against a date-only field. Expect to re-see a freshly
deleted id on later polls until the cursor advances past its whole `deletedDate` day, so make the
downstream action (e.g. tombstoning) **idempotent** and the re-sweep is free. Because the zone is
unspecified, a record deleted near midnight can land a calendar day either side of your "today"; the
overlap absorbs that too.

**How we know:** Probing `deleted=true&deletedDate=[…]` on a production catalog returned date-only
`deletedDate` values on every entry, alongside full-timestamp `updatedDate` values from the same
records' change history.

## `GET bibs` returns entries ascending by `id` (so you can keyset-paginate)

**Behavior:** `GET bibs` returns its entries **sorted ascending by `id`**, and an `id=[<n>,]`
lower-bound filter starts exactly at `n`. Successive pages requested as `id=[<last_id + 1>,]` come back
strictly after the previous page, with no gap and no overlap.

**Type:** By design (the ordering is relied upon, but confirm it on your deployment).

**How to handle:** Prefer **keyset (seek) pagination** — `id=[<last_seen_id + 1>,]` — over `offset` for
large or long-running sweeps. Offset pagination can drop or duplicate rows if the underlying set
changes mid-sweep; an ascending-`id` seek cursor is gap/dup-free under concurrent inserts and deletes.

**How we know:** Page 1 (`id=[1000000,]`, limit 50) returned `1000001…1000051` ascending; page 2
(`id=[1000052,]`) returned `1000052…` — strictly after page 1, with no gap or overlap.

## Range filters AND together: `updatedDate` + `id` in one query

**Behavior:** A time-range filter and an id-range filter can be **combined in a single query**, and
they are ANDed: `GET bibs?updatedDate=[<since>,<until>]&id=[<cursor>,]` returns records satisfying
both.

**Type:** By design.

**How to handle:** Combine them for **windowed keyset pagination** — page through a change window by
ascending `id` with no `offset`, getting both the late-arriving-data safety of a time window and the
gap/dup-free property of a seek cursor.

**How we know:** `updatedDate=[2020-…,2030-…]&id=[1000000,]` returned `200` with 50 ascending entries,
each carrying a populated `updatedDate`.

## List responses are capped (~2000); detect the end by a short page, not by `total`

**Behavior:** A list/range `GET` returns at most ~2000 entries per request, and the `total` field
reflects the **capped** count for that request rather than the true size of the matching set. Trusting
`total` to decide "am I done?" stops you early.

**Type:** By design.

**How to handle:** Page until you receive a page **shorter than your requested `limit`** — that short
page is the end-of-results signal. Don't compare against `total`.

```python
limit = 2000
offset = 0  # or a keyset cursor: id=[last_seen + 1,]
while True:
    page = fetch(offset, limit)
    yield from page
    if len(page) < limit:          # short page => done
        break
    offset += limit
```

**How we know:** A production bib harvest paginating by request limit terminates correctly on the
first short page, whereas a `total`-based stop condition truncated long sweeps.

## `deleted=false` silently hides server-deleted records — they vanish from incremental polls

**Behavior:** When a record is deleted in Sierra its `deleted` flag flips to `true`, so it **drops out**
of every `deleted=false` query. A high-water-mark incremental poll filtered on `deleted=false`
therefore **never learns the record is gone** — it simply stops appearing, indistinguishable from
"unchanged."

**Type:** By design (but a silent data-integrity footgun for anyone caching or mirroring Sierra).

**How to handle:** A `deleted=false` change poll cannot track deletions. Run a **separate
`deleted=true&deletedDate=[…]` poll on its own cursor** (mind its day granularity, above), and/or a
periodic **id reconciliation** (compare your live id set against Sierra's) to catch the deletions the
change poll structurally cannot see. Don't try to infer deletions from "an id I expected but didn't get
back" in a change poll — that false-positives on suppressed / no-MARC records.

**How we know:** A mirror built only on `deleted=false` incremental polls accrued server-deleted
records as permanently-live rows; adding a `deletedDate` delete-poll plus an id reconcile was required
to converge.
