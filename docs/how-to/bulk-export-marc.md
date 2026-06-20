<!--
DRAFT — Phase 2 (Recipes / how-to). Intentionally NOT yet wired into mkdocs.yml nav.
The how-to quadrant's structure is an open Phase-2 Diátaxis decision; place/format on resume.
-->

# Bulk-export the full MARC catalog

**Goal:** pull binary MARC (ISO-2709) for your entire bib catalog — or just the bibs you're missing —
in one efficient pass, without enumerating ids and without an offline Data Exchange job.

This is the fast path: a single-threaded range sweep that exports **~900 records/sec (~55k/min)**, so a
~2-million-bib catalog finishes in well under an hour. It works because `bibs/marc` accepts an `id`
range and returns the lowest contiguous block of each page (see the reference entries linked at the
bottom for *why* this is correct).

## Before you start

- A `SierraRESTClient` authenticated against your catalog.
- A MARC parser that can read ISO-2709 bytes and pull each record's bib number (e.g. `pymarc`; the bib
  number is typically in `907$a`, deployment-dependent).
- If you only want the bibs you *lack* MARC for, a way to list those ids (your store's anti-join). For a
  whole-catalog export, just start the cursor at your lowest bib id.

## The two-phase export protocol

`bibs/marc` never returns records inline. Each page is three calls:

1. `GET bibs/marc?id=[<cursor>,<max>]&limit=2000` → a small **MarcSummary** JSON pointing at a
   server-generated `.mrc` file.
2. `GET bibs/marc/files/<fileId>` → the binary ISO-2709 MARC.
3. `DELETE bibs/marc/files/<fileId>` → clean up the server-side file (**don't skip this** — the files
   accumulate otherwise).

```python
def fetch_marc_page(client, cursor, *, max_id=9_999_999, limit=2000):
    """One page: returns raw ISO-2709 bytes for the lowest <=limit bibs in [cursor, max_id]."""
    summary = client.request("GET", f"bibs/marc?id=[{cursor},{max_id}]&limit={limit}").json()
    if summary.get("outputRecords", 0) == 0:
        return b"", 0
    file_id = summary["file"].rsplit("/", 1)[-1]
    mrc = client.request("GET", f"bibs/marc/files/{file_id}").content
    client.request("DELETE", f"bibs/marc/files/{file_id}")
    return mrc, summary["outputRecords"]
```

## Sweep the id space with a keyset cursor

Advance the cursor to **`max(bib id on the page) + 1`** after each page. Because every page is the
lowest contiguous block of the remaining range, this is gap-free and duplicate-free — even under
concurrent inserts/deletes.

```python
import pymarc

def bulk_export_marc(client, *, start_id, max_id=9_999_999, on_record):
    cursor, pages, total = start_id, 0, 0
    while True:
        mrc, out = fetch_marc_page(client, cursor, max_id=max_id)
        if out == 0:
            break                                   # catalog exhausted
        ids = []
        for record in pymarc.MARCReader(mrc):
            if record is None:
                continue
            bib_id = int(record["907"]["a"].lstrip(".b")[:-1])   # adjust to your deployment
            ids.append(bib_id)
            on_record(bib_id, record)
        pages, total = pages + 1, total + len(ids)
        if not ids:
            break
        cursor = max(ids) + 1                        # keyset advance
    return {"pages": pages, "records": total}
```

`on_record` is your sink: write the MARC to a store, or filter to only the bibs you were missing and
drop the rest.

## Gap-fill only the bibs you're missing

For a re-baseline you usually only want bibs that *lack* MARC. Keep the cheap full sweep — Sierra has no
"only these ids" filter for a range — but **keep** only the records whose id is in your missing set:

```python
missing = set_of_bib_ids_without_marc()        # from your store's anti-join
def keep_if_missing(bib_id, record):
    if bib_id in missing:
        store_marc(bib_id, record.as_json())
        missing.discard(bib_id)

bulk_export_marc(client, start_id=min(missing), on_record=keep_if_missing)
# anything still in `missing` after the sweep is an orphan: a live bib Sierra returns no MARC for
```

The sweep still *fetches* the already-archived records interleaved through the range (unavoidable), but
you only pay to parse + store the ones you need.

## Verify

- **Coverage:** every id you targeted should be either stored or left in `missing` as a genuine orphan.
  A clean run reports `written + orphans == |missing|`.
- **Orphans are expected.** A few percent of live bibs (blank MARC-type, suppressed, etc.) return no
  MARC at all. To prove an orphan is *real* and not a pagination skip, re-fetch a sample of them
  **individually** — `GET bibs/marc?id=<one>`. If a single-id fetch returns MARC, your range pagination
  skipped it; if it's empty, the orphan is genuine. (In a 179-page production run, 0 of 5,000 targeted
  ids were skipped — but verify on your deployment before trusting the sweep blind.)
- **Round-trip fidelity:** `record.as_json()` round-trips to the same ISO-2709 leader + field tags, so
  storing the JSON loses nothing.

## Gotchas

- **Keep it single-threaded.** This endpoint is fast *because* each call returns 2000 records; adding
  concurrency on top mostly multiplies timeouts. Don't reach for it.
- **`limit` caps at ~2000.** Asking for more silently gives you 2000.
- **Don't enumerate ids.** An `id=1,2,3,…` list is capped at **50** and silently truncated — the slow,
  wrong tool for a full sweep. See *Reads & IDs → The 50-record cap applies to enumerated id lists*.
- **Always DELETE the generated file** each page.

---

**Underlying behavior (reference):**

- [Change polling, ranges & pagination → `bibs/marc` is a two-phase binary export](../reference/quirks/change-polling.md)
- [Reads & IDs → The 50-record cap applies to enumerated `id` lists, not ranges](../reference/quirks/reads-and-ids.md)
