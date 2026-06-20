# Poll for changed and deleted records

**Goal:** keep a downstream copy of Sierra current by incrementally harvesting records
that changed, and — separately — records that were deleted, without missing or
double-counting any.

You need **two** poll loops on **two** cursors. A `deleted=false` change poll structurally
cannot see deletions (a deleted record just stops appearing), so deletions get their own
loop. Both use keyset pagination, not `offset`.

## 1. Poll for changes (windowed keyset pagination)

Page through a change window by ascending `id`, advancing the cursor to `max(id) + 1`
each page. Combine a time window and an id range in one query — they AND together — so you
get the late-arriving-data safety of a time window with the gap/dup-free property of a
seek cursor.

```python
def poll_changes(client, since, until, *, start_id=0, limit=2000):
    cursor = start_id
    while True:
        url = f"bibs?deleted=false&updatedDate=[{since},{until}]&id=[{cursor},]&limit={limit}"
        resp = client.request("GET", url)
        if resp.status_code == 404:        # Sierra's "no records match" for a range query
            break                          # treat 404 + code 107 as zero results, not an error
        resp.raise_for_status()
        entries = resp.json().get("entries", [])
        if not entries:
            break
        yield from entries
        if len(entries) < limit:           # short page => end of results (don't trust `total`)
            break
        cursor = entries[-1]["id"] + 1     # keyset advance; entries are ascending by id
```

Two traps this handles: a zero-match window returns **`404` + `code 107`**, not an empty
list, so it's caught explicitly; and the end of results is a **short page**, not
`total` (which reflects only the capped per-request count).

## 2. Poll for deletions (separate cursor, day-granular)

`deletedDate` is **date-only** (no time component), so the deletion cursor must be
day-granular with a **≥1-day overlap** re-sweep. You'll re-see freshly deleted ids until
the cursor passes their whole `deletedDate` day — so make the downstream action (e.g.
tombstoning) **idempotent** and the overlap costs nothing.

```python
def poll_deletions(client, since_day, until_day, *, start_id=0, limit=2000):
    cursor = start_id
    while True:
        url = f"bibs?deleted=true&deletedDate=[{since_day},{until_day}]&id=[{cursor},]&limit={limit}"
        resp = client.request("GET", url)
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        entries = resp.json().get("entries", [])
        if not entries:
            break
        yield from entries
        if len(entries) < limit:
            break
        cursor = entries[-1]["id"] + 1
```

Note the *deleted* variant returns `200 {"entries": []}` on an idle window where the
*change* variant returns `404` — don't assume the two shapes behave the same; the `404`
guard above is harmless either way.

## 3. Reconcile periodically (catch what polls can't)

Even with both loops, a record deleted outside your overlap window, or a poll that
silently dropped, can leave a phantom-live row. Periodically **reconcile**: compare your
live id set against Sierra's and tombstone the difference. Don't try to infer deletions
from "an id I expected but didn't get back" in the change poll — that false-positives on
suppressed / no-MARC records.

## Verify

- Run the change poll over a window you know contains edits; confirm it terminates on a
  short page and re-running with the same cursor is idempotent.
- Run the deletion poll over a window with a known deletion; confirm the id appears and
  that re-running (overlap) doesn't double-tombstone.

---

**Underlying behavior (reference):**

- [Change polling, ranges & pagination](../reference/quirks/change-polling.md) — the
  `404`-on-empty, date-only `deletedDate`, ascending-`id` keyset, range-AND, ~2000 cap,
  and `deleted=false`-hides-deletions entries.

**For bulk MARC specifically:**
[Bulk-export the full MARC catalog](bulk-export-marc.md)
