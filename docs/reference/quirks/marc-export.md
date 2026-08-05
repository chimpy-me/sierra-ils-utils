# MARC export (`bibs/marc`)

The two-phase export has a failure mode worth knowing before you build on it: it can hand you a
**complete, valid, parseable MARC record that is missing most of the data you asked for**, with a
`200` at every step.

**"Two-phase" means the file does not come back from the request that asks for it:**

1. **You ask, and the server builds a file.** `GET bibs/marc?id=…` returns a *receipt* — the
   MarcSummary JSON — carrying record counts and a URL for a server-generated `.mrc` file.
2. **You download that file.** A second `GET` returns raw binary ISO-2709.

You then `DELETE` the file, or generated files accumulate server-side. Parsing happens locally,
afterwards, and is not one of the phases.

The distinction matters for one specific reason: **the receipt is the only place truncation is
reported.** By the time you are holding the bytes, the signal is gone. That is the subject of this
page.

For the export's *pagination* behavior — keyset cursors, the ~2000 `limit` cap, and the full
GET/GET/DELETE recipe — see [Change polling, ranges & pagination](change-polling.md). This page is
about what's *inside* the file.

Why the 99,999-byte limit exists at all, how other ILSes hit the same one, and what has been proposed
to fix it: [Why MARC exports lose item data](../../explanation/marc-record-size-and-embedded-item-data.md).

## A MARC record cannot exceed 99,999 bytes — bibs with many items are silently truncated

**Behavior:** ISO-2709 stores the record length in leader positions 00–04 — five decimal digits — and
each directory entry's field start position in five more. Nothing beyond byte 99,999 is addressable.
Sierra generates one `945` field per attached item at export time, appended *after* the bibliographic
fields. When a bib's items push the record past the ceiling, the `945` run is cut off: the
bibliographic portion arrives complete, the item tail does not.

Where the cut lands **varies by bib**, because the constraint is a byte budget rather than a field
count — a bib with long call numbers or volume statements fits fewer items. Observed cutoffs ranged
from **463 to 595 items** across one 2.1M-record catalog.

```
GET bibs/marc?id=1014568                     ->  200
{ "inputRecords": 1, "outputRecords": 1, "errors": 1 }

GET bibs/marc/files/<fileId>                 ->  200, 99,819 bytes
  leader[00:05] = 99819            (equals the actual file length)
  directory     = 504 entries, of which 464 are 945
  last field ends at byte 99,818;  record terminator at 99,819
  headroom under the ceiling: 180 bytes;  one more 945 costs ~215
```

That bib has **5,736 items** in Sierra. The export carried 464 of them. The other 5,272 are simply
absent, with nothing in the file to say so.

**Type:** By design — of ISO-2709, not of Sierra. The *silence* is the quirk (see the next card).

**How to handle:** **Never treat MARC `945` as an item inventory.** Fetch item data from
`GET items?bibIds=<id>`, which has no such ceiling — the same bib returns all 5,736 items in three
2000-row pages. Treat the MARC export as bibliographic data that happens to carry a partial item
convenience copy. If you must rely on the export, at minimum detect the truncation (next card).

In practice only serials and periodicals reach the ceiling, since one item per issue is the realistic
way a bib accumulates 600+ items. A bib only accumulates issues, so records near the ceiling cross it
over time without anything changing on your side.

**How we know:** A production Sierra v6 deployment, read-only probes, 2026-07-27. Across 2,097,246 archived
bib records the maximum observed `945` count is 595 and no record exceeds 99,999 bytes. Counting the
directory's `945` entries by raw byte scan — no MARC library involved — and with `pymarc` gives the
identical count, so nothing is being dropped client-side. Re-requesting the same bib returns the same
truncated record.

## Truncation is reported only as `errors` in the MarcSummary — the HTTP calls succeed and the MARC is valid

**Behavior:** nothing in the download signals the loss. Phase 1 returns `200`. Phase 2 returns `200`
with `application/octet-stream`. The file is well-formed ISO-2709 — the leader's length matches the
actual file length, every directory offset resolves, the field and record terminators are present,
and `pymarc` parses it without a warning. The count identity holds too: `outputRecords` +
`deletedRecords` == `inputRecords`.

The **only** channel carrying the signal is the `errors` counter in the phase-1 MarcSummary:

```json
// a truncated bib
{ "file": "…", "inputRecords": 1, "outputRecords": 1, "errors": 1 }

// an ordinary bib
{ "file": "…", "inputRecords": 1, "outputRecords": 1, "errors": 0 }
```

Note `outputRecords: 1` *and* `errors: 1` together — Sierra reports the record as successfully
exported and as problematic in the same breath. A harvester that reconciles only on the count
identity sees nothing wrong.

**Type:** Bug-or-quirk.

**How to handle:** Read `errors` on **every** batch, not only when the file comes back empty. In a
batched sweep it is a per-batch count, so a nonzero value tells you the batch contains at least one
truncated record but not which one — re-request that batch's ids individually to identify them. The
resulting list is also exactly the worklist for re-fetching those bibs' items from
`GET items?bibIds=`.

**How we know:** A production Sierra v6 deployment, 2026-07-27. Two bibs independently confirmed truncated
returned `errors: 1`; two ordinary bibs returned `errors: 0`.

!!! warning "Small sample — confirm before you gate on it"
    That is **n=4**, and the `errors` field is undocumented. "Nonzero `errors` means truncation" is a
    strong hypothesis, not an established fact — it may also cover other export problems. Widen it on
    your own deployment before treating it as a gate. What *is* certain is that no other part of the
    response dissents.

## The bulk export is binary-only; the per-record MARC endpoint offers JSON/XML but carries no items

**Behavior:** these are two different surfaces, and they are easy to conflate.

**`bibs/marc`** — the bulk two-phase export — emits binary ISO-2709 and nothing else. Attempts to
select another serialization by query parameter are rejected:

```
GET bibs/marc?id=<id>&mimetype=application/marcxml+xml     -> 400
GET bibs/marc?id=<id>&mimetype=application/marc-in-json    -> 400
GET bibs/marc?id=<id>&format=xml                           -> 400
```

**`bibs/{id}/marc`** — per record — *does* serve alternate serializations, selected by **`Accept`
header**, not by query parameter. The accepted spellings are non-obvious:

| `Accept` | Result |
|---|---|
| `application/marc-in-json` | **200** |
| `application/marc-json` | **200** |
| `application/marc-xml` | **200** |
| `application/marc+json`, `application/marcxml+xml`, `text/xml`, `application/marc`, `application/json` | `400` |
| *(omitted)* | `400` — `code 108`, *"Unknown content type"* |

Those forms are genuinely not length-prefixed — the leader comes back zeroed, `00000cas  2200000Ia
4500` — so they carry no 99,999-byte ceiling. **But they are a narrower projection of the record, not
the same record in another format.** They omit precisely the fields the export job generates:

| Field | Bulk export | Per-record `marc-in-json` |
|---|---:|---:|
| `945` (one per item) | 464 | **0** |
| `907` (record number) | present | **absent** |
| `998` (BCODE3 suppression) | present | **absent** |
| total fields | 504 | 38 |

Neither side of that split can be bridged. The per-record endpoint takes no parameter that adds
items, and the bulk export ignores `Accept` at both phases:

```
GET bibs/{id}/marc?items=true            -> 400  Parameter not recognized
GET bibs/{id}/marc?includeItems=true     -> 400  Parameter not recognized
GET bibs/{id}/marc?fields=945            -> 400  Parameter not recognized
GET bibs/{id}/marc?expand=items          -> 200  — accepted and SILENTLY IGNORED (still 0 × 945)

GET bibs/marc?id=<id>   Accept: application/marc-in-json
  -> phase 1 still returns a MarcSummary; phase 2 still returns
     application/octet-stream, byte-identical binary, still truncated
```

**A third surface behaves the same way: the `marc` and `varFields` fields on `GET bibs`.** It is worth
naming explicitly, because reaching for the JSON record is the obvious next idea once the ceiling
bites:

```
GET bibs/{id}?fields=,
  marc      -> MARC-in-JSON, leader "00000cam  2200000 a 4500"  (zeroed — no ceiling)
  varFields -> the stored MARC record
```

Both are ceiling-free and **neither carries `945`** — measured 0 × `945` on a bib with 31 attached
items. `varFields` likewise has no `907` and no `998`. `marc` and `varFields` are two shapes of the
same stored record; capturing both is redundant.

**So the two capabilities are mutually exclusive across every surface:** the one surface that
generates `945` cannot escape the byte ceiling, and every surface that escapes the ceiling never had
`945`. For *why* that split exists and what it would take to close it, see
[Why MARC exports lose item data](../../explanation/marc-record-size-and-embedded-item-data.md).

**Type:** By design.

**How to handle:** The alternate serializations are **not** a workaround for the byte ceiling —
there are no items in them to truncate. Pick by what you need: `bibs/{id}/marc` for the catalogued
bibliographic record in JSON or XML; the bulk export when you want Sierra's generated `907`/`945`/`998`
alongside it; and **`GET items?bibIds=` whenever you want item data — it is the only surface of the
three that returns a complete item set.** Note also that converting a downloaded binary record to
MARCXML or MARC-in-JSON after the fact recovers nothing: the conversion happens after the fetch and
inherits whatever the ceiling removed.

Beware `?expand=items` specifically — a `200` with no error makes it look like it worked.

Because the per-record endpoints are a direct record read rather than an export job, they also carry
no `errors` key — the signal described in the previous card exists only in the two-phase summary.

**How we know:** A production Sierra v6 deployment, 2026-07-27. Same bib on the same day through all three
surfaces: 504 fields / 464 × `945` from the bulk export; 38 fields / 0 × `945` from both
`marc-in-json` and `marc-xml`. The `GET bibs` `marc`/`varFields` finding is separate — sierra-test,
same date: `marc.leader` came back zeroed and both fields returned 0 × `945` on a bib with 31 items,
with no `907` or `998` in `varFields`. Query-parameter spellings on `bibs/marc` were rejected `400`; the
`Accept`-header spellings were probed individually against `bibs/{id}/marc`; the item-inclusion
parameters and the bulk-export `Accept` header were probed as shown above. Not an exhaustive search of
every possible spelling, but every plausible one tried is closed.

## What truncation does *not* damage

Worth stating explicitly, because it bounds the blast radius: the bibliographic record survives
intact. Sierra appends the `945` block last, so truncation can only ever eat the item tail. On the
truncated example above, all 40 non-`945` fields are present and correct — including `998`, which
carries BCODE3 suppression (see [Suppression](suppression.md)):

```
001 003 005 008 010 019 022 032 035 035 040 042 092 222 245 246 246 260 260 300
310 321 500 500 500 515 588 590 590 650 650 650 856 907 998 944 941 959 959 959
```

So a MARC harvest remains sound for cataloging, discovery, and suppression purposes on these records.
It is unsound only as a source of item data.
