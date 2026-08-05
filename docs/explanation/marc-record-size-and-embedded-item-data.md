# Why MARC exports lose item data

Sierra's bulk MARC export can hand you a complete, valid, parseable record that is missing most of
the items you asked for. The [MARC export](../reference/quirks/marc-export.md) card documents what
that looks like and how to detect it. This page is the *why*: where the limit comes from, why every
ILS has the same one, and what has been proposed to fix it.

The short version, which the rest of this page unpacks:

> Sierra is not unusual in hitting the ceiling. It is unusual in not telling you.

!!! note "A word on 'holdings'"
    MARC 21 uses *holdings* as an umbrella term covering single-part, multipart, and serial bibliographic units —
    a one-volume book has a holdings statement — with item-level detail carried at `876`–`878`. In
    Sierra, and in most day-to-day library conversation, a **holdings record** means something
    narrower: the serials check-in record, with `853` publication patterns and `866` textual
    statements. The two senses collide constantly.

    This guide uses **item** for the individual barcoded physical piece, and reserves **holdings
    record** for Sierra's record type. Where the standard's umbrella sense is meant, it says so.

## The practice has a name

MARC 21 distinguishes two ways to say what a library holds:

- a **separate holdings record**, linked to the bibliographic record by field `004`; and
- **embedded holdings information**, carried inside the bibliographic record itself.

Sierra's `945` is the second. So is Koha's `952` and Symphony's `999`. When the standard embeds
holdings this way, only field `852` (Location) is required, and item-level detail belongs in
`876`–`878` ("Item Information").

This matters because it means the flattening is not a vendor hack around a missing feature. It is a
recognised shape that the standard describes — the vendors simply did not use the standard's fields
for it. Using them would not have raised the ceiling, incidentally — `876`–`878` consume bytes like
any other field.

## Why every vendor invented its own field

MARC 21 reserves the entire `9XX` block for **local implementation** and defines nothing in it. That
is an invitation, and every ILS accepted it differently:

| ILS | Items embedded as | Standard field? | How we know |
|---|---|---|---|
| Sierra (III) | `945`, plus `907` record number and `998` BCODE3 | no — local `9XX` | measured; see the MARC export card |
| Koha | `952` | no — local `9XX` | Koha manual |
| Symphony (SirsiDynix) | `999` | no — local `9XX` | VuFind's SirsiDynix export notes |
| Evergreen | `852` | **yes** | Evergreen `marc_export` docs |

Four systems, four answers, and only Evergreen uses a standard holdings tag. The consequence is
worth stating plainly for anyone building a harvester:

!!! tip "The portability consequence"
    **"Ingest MARC with items" is not a portable instruction.** A harvester that reads item data out
    of exported MARC must know which ILS produced the file. There is no field you can look for that
    works everywhere.

## Why the ceiling exists, and why it is not Sierra's

Binary MARC is [ISO 2709](https://www.loc.gov/marc/specifications/specrecstruc.html), and the format
is built on fixed-width byte offsets:

- **Leader positions 00–04** hold the Logical Record Length as **five decimal digits**. The largest
  number expressible is 99,999, so nothing beyond byte 99,999 is addressable.
- **Each directory entry** is twelve bytes: a three-character tag, a **four-digit field length**, and
  a five-digit starting position. So an individual field caps at **9,999 bytes** and can fail
  independently of the total record size.

Neither limit is Sierra's invention, and neither is avoidable while emitting binary MARC. Every
system that writes ISO 2709 hits the same wall in the same place. Ex Libris documents the identical
ceiling for **Aleph**, for the identical reason — items expanded into the bibliographic record — and
documents a maximum record size for **Voyager** as well.

What differs between systems is not the limit. It is whether the system tells you when you cross it.
Aleph and Voyager document a maximum. Sierra returns `200`, a well-formed record that parses without
a warning, and an undocumented `errors` counter carrying no record identity — no id, no reason, no
count of what was omitted. That asymmetry is the part that is fairly Sierra's.

## What a fix would look like

These are proposals from the community and from the structure of the problem, ordered by how much
they would disturb. None of them is implemented in Sierra today.

### 1. A sentinel length — `00000`, not `99999`

Rochkind's 2010 *Spec for a better ILS MARC exporter* recommends that a record too long for MARC 21
be emitted with `99999` in the Leader's length (or `00000`), and `9999` in an over-long field's
directory length — while **every other byte offset stays correct and legal**.

This preserves the flattening the whole ecosystem depends on, needs no new format, and asks nothing
of clients that already handle such records.

**But which sentinel you pick matters, and the received wisdom is only half right.** We measured it
rather than taking the 2010 write-up on faith:

!!! success "Measured against pymarc 5.3.1 — 2026-08-05"
    | Mutation, with every other offset left correct | Result |
    |---|---|
    | Leader 00–04 = `99999` | **rejected** — `TruncatedRecord`, no fields recovered |
    | Leader 00–04 = `00000` | **parsed** — all fields recovered |
    | A directory entry's field length = `9999` | **parsed** — all fields recovered |

    Controls, to show the test could detect breakage: truncating the record raised
    `TruncatedRecord` and destroying its final record terminator raised `EndOfRecordNotFound`.
    A record with an internal field terminator overwritten, and one with a directory entry's
    start position shifted 40 bytes, both parsed with every field recovered.

So the recommendation survives — in its `00000` form only. This parser rejects the `99999` form
outright, raising `TruncatedRecord` and recovering nothing.

It is tempting to explain this by saying MARC parsers locate boundaries by the field and record
terminators rather than by the leader's length. **Our measurements do not settle that.** The
`00000` row above is the reason to doubt the simplest story: a parser that merely believed the
leader would have read zero bytes and recovered nothing, and instead every field came back. But the
rest of the probe cuts across any tidy account — pymarc recovered every field from a record whose
internal field terminator had been overwritten, and from one whose first directory entry pointed
forty bytes off target, yet failed cleanly when the record was truncated or its final record
terminator destroyed. **Treat the mechanism as an open question**; what is measured is the table
above.

### 2. Name the truncated record

Today truncation surfaces as `errors: 1` in the phase-1 summary — a bare count, with no indication of
*which* record lost data or *how much*. Turning that into a structured list:

```json
{ "errors": [ { "id": 1014568, "reason": "record exceeds 99999 bytes", "itemsOmitted": 5272 } ] }
```

…would be additive and non-breaking, and it converts a silent failure into a loud one. Of the three,
this is the smallest change with the largest effect.

### 3. Honor `Accept` on the bulk endpoint

Sierra already serves MARCXML and MARC-in-JSON from the *per-record* endpoint, and those
serializations have no length prefix and therefore no ceiling. The bulk export ignores the `Accept`
header at both phases. Honoring it would be ceiling-free and standards-clean — though note it would
only help if the bulk export's generated `945` fields came along, which is a larger change than it
first appears. See the [MARC export](../reference/quirks/marc-export.md) card for the measured
behavior of all three surfaces.

## The open question

!!! warning "Unconfirmed"
    **Does any mainstream ILS ship a bulk export that is both item-bearing and ceiling-free?**

    We do not know, and it matters. For Sierra the answer is measured and negative: the surface that
    generates `945` cannot escape the byte ceiling, and every surface that escapes the ceiling never
    carried `945`. For the others it is untested. Evergreen's `marc_export` supports both `-f XML`
    and `--items`, but its documentation does not state that the two combine. Koha exports MARCXML
    and holds item data in `952`, which makes a ceiling-free item-bearing export plausible.
    Symphony's XML support was not investigated.

    The cheapest way to settle it: run `marc_export -f XML --items` against an Evergreen demo
    instance and count `852` fields on a bib with a high item count. If several systems manage it,
    Sierra's mutual exclusivity is a genuine outlier. If none do, then Sierra is ordinary here and
    only the silence is unusual.

## What this does not mean

One inference is tempting and wrong, so it is worth closing off explicitly.

Sierra does implement MARC holdings records, and does expose them over REST — confirmed by
read-only probe of `GET /v6/holdings` on sierra-test, 2026-08-04, which returned genuine MFHD
structure (`853` caption/pattern and `866` textual holdings, with `001` and `004` linkage). It would
seem to follow that a bib with thousands of items could be represented compactly by a holdings
record instead of by thousands of `945` fields. **It does not follow, for two independent
reasons.**

**Holdings records are not item records.** Sierra's holdings records are serials constructs: a
predictive publication pattern (`853`) plus a textual statement (`866`) expressing "we hold v.1–50."
Item records are individual barcoded physical pieces. A bib with 5,736 items has 5,736 barcodes, and
`853`/`866` do not enumerate them. They are different levels of description, not two encodings of the
same thing.

**And the machine-readable enumeration is largely unpopulated.** Field `863` carries the enumeration
that would be needed to expand a holdings statement into specific pieces. Measured across 22,428
holdings records on sierra-test, a lagging clone of production (read-only SQL probe, 2026-08-04),
`863` appears on **4.4%** of them — and on **none** of the five highest-item-count bibs on that
deployment. A compact representation that is empty is not a representation.

The general shape of the error, in both cases, is reasoning from what a schema *permits* to what the
data *contains*.

## Where to go next

- [MARC export (`bibs/marc`)](../reference/quirks/marc-export.md) — the measured behavior: what
  truncation looks like, how to detect it, and how the three serialization surfaces differ.
- [Bulk-export the full MARC catalog](../how-to/bulk-export-marc.md) — the working recipe.
- [Discovering quirks yourself](discover-quirks-yourself.md) — how these findings were produced, if
  you want to re-derive them on your own deployment.

## Sources

- [LC — MARC 21 Specifications for Record Structure](https://www.loc.gov/marc/specifications/specrecstruc.html)
- [LC — MARC 21 Format for Holdings Data: Leader](https://www.loc.gov/marc/holdings/hdleader.html)
- [LC — MFHD 863: Enumeration and Chronology](https://www.loc.gov/marc/holdings/hd863.html)
- [OCLC — MARC 21 Format for Holdings Data primer](https://help.oclc.org/Metadata_Services/Local_Holdings_Maintenance/A_holdings_primer/20MARC_21_Format_for_Holdings_Data)
- [Rochkind — Spec for a better ILS MARC exporter (2010)](https://bibwild.wordpress.com/2010/04/06/spec-for-a-better-ils-marc-exporter/)
- [Rochkind — Structural MARC problems you may encounter](https://bibwild.wordpress.com/2010/02/02/structural-marc-problems-you-may-encounter/)
- [Ex Libris — Limit on size of exported bib record (with items expanded into it)](https://knowledge.exlibrisgroup.com/Aleph/Knowledge_Articles/%22Directory_does_not_exist%22_messages_written_repeatedly_to_sqlnet.log/Limit_on_size_of_exported_bib_record_(with_items_expanded_into_it))
- [Ex Libris — Maximum length of MARC records in Voyager](https://knowledge.exlibrisgroup.com/Voyager/Knowledge_Articles/Maximum_length_of_MARC_records_in_Voyager)
- [Koha Manual — Cataloging](https://koha-community.org/manual/latest/en/html/cataloging.html)
- [Evergreen — `marc_export`](https://olddocs.evergreen-ils.org/docs/3.5/_marc_export_exporting_bibliographic_records_into_marc_files.html)
- [VuFind — SirsiDynix export notes](https://vufind.org/wiki/indexing:marc:export_notes:sirsidynix)
