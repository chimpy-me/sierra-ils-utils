# Suppression (`suppressed`, BCODE3 / ICODE2)

How Sierra exposes OPAC suppression across the REST API and the MARC export. Suppression is **not
deletion** — a suppressed record is live and fully retrievable; it is merely hidden from the public
discovery layer. If you are building a patron-facing slice, this is the flag you filter on.

## `suppressed` is a read-only boolean on bibs and items

**Behavior:** `GET bibs?fields=id,suppressed` and `GET items?fields=id,suppressed` both return a
boolean `suppressed` on every record (e.g. `{"id": "1000165", "suppressed": true}`). It is a
*computed reflection* of an underlying fixed field (below), not an independently writable field — it
appears in the API's list of PUT-rejected read-only fields (see [Write semantics](write-semantics.md)).

**Type:** By design.

**How to handle:** Read it freely to know a record's discovery visibility. To *change* suppression,
edit the underlying fixed field (BCODE3 for bibs, ICODE2 for items), not `suppressed`.

**How we know:** Live read-only probes on sierra-test (`v6`), 2026-06-21: both endpoints returned
the boolean; `suppressed` is also enumerated among the read-only top-level fields rejected on PUT.

## `suppressed=true` is a valid filter param on both endpoints

**Behavior:** `GET bibs?suppressed=true&fields=id,suppressed` (and the `items` equivalent) returns
**only** suppressed records — the symmetric counterpart to `deleted=true&deletedDate=...` for
deletions. Suppressed records are otherwise **included by default**: a plain `deleted=false` query,
and the MARC export, both return suppressed records inline (suppression does not hide a record from
queries the way deletion does).

**Type:** By design.

**How to handle:** Use `suppressed=true` to enumerate the suppressed set directly, or request the
`suppressed` field on a normal sweep and filter client-side. Do **not** assume a normal harvest
excludes suppressed records — it doesn't; you simply can't tell which are suppressed unless you ask
for the field (or read the MARC fixed-field below).

**How we know:** Probes on sierra-test, 2026-06-21: `suppressed=true` returned all-suppressed pages
on both `bibs` and `items`; a default `deleted=false` window contained `suppressed:true` records
inline.

## Suppression is carried in the MARC export — bib `998$e` (BCODE3), item `945$o` (ICODE2)

**Behavior:** The boolean is computed from a Sierra fixed field — **BCODE3** ("Suppress (BCODE3)")
for bibs, **ICODE2** ("Suppress (ICODE2)") for items. Critically, those fixed fields are **present in
the MARC export** Sierra generates via `bibs/marc`: BCODE3 lands in **`998$e`** and ICODE2 in
**`945$o`** (the 945 item-data field). On the deployment observed, the suppressed value is `'s'` and
the unsuppressed value is `'-'`, correlating 1:1 with the REST `suppressed` boolean. So a MARC-based
harvest already carries suppression — no separate JSON fetch is required to capture it.

**Type:** By design.

**How to handle:** If you harvest MARC, extract `998$e` (bib) and `945$o` (item) to capture
suppression for free, in the same pass — and to backfill it from already-stored MARC with zero new
API calls. **Store the raw code, not a hard-coded boolean** — and **do not assume `'s'` is the only
suppressed code.** The reliable rule is the *inverse*: `'-'` is the OPAC-display (not-suppressed)
value, and **any other code is suppressed** (`suppressed = code != '-'`). At CHPL, BOTH `'s'` and
`'d'` occur and both map to REST `suppressed=true` (the `'s'`-only assumption from a test-environment
sample missed the `'d'`, which only appeared in production data). So keep the raw code in the lake
and apply `coalesce(code,'-') <> '-'` (or `NOT IN (<your library's display code>)`) downstream;
that survives codes you haven't enumerated yet. Confirm your deployment's display code by correlating
the fixed-field value against the REST `suppressed` boolean across a varied sample, **including a
full-corpus pass** — rare codes hide in the long tail.

**How we know:** sierra-test `v6`, 2026-06-21, via the two-phase `bibs/marc` export used by a
production harvest. A known-suppressed bib (`.b1000165`, BCODE3=`s`, REST `suppressed=true`) had
`998$e='s'`; four unsuppressed bibs in the same page had `998$e='-'`. A known-suppressed item
(ICODE2=`s`, REST `suppressed=true`) had `945$o='s'`; an unsuppressed item on the same bib had
`945$o='-'`. The per-record `GET bibs/{id}/marc` endpoint returned `400` on this version — MARC is
available only through the two-phase batch export. **Full-corpus confirmation:** a complete MARC
re-parse of ~2.08M prod bibs + ~4.65M items found `998$e` ∈ {`-`: 2,080,029; `s`: 12,079; `d`: 1}
and `945$o` ∈ {`-`; `s`: 464,229} — the single `d` bib (3947502) returned REST `suppressed=true`,
confirming the `!= '-'` rule and that a test-only sample under-counts the code set.

## Does toggling suppression bump `updatedDate`?

**Behavior:** Because `suppressed` reflects a fixed field, an interactive suppress toggle is a
record edit and bumps `updatedDate` — so a normal change poll re-fetches the record and a MARC
harvest re-captures `998$e`/`945$o`. The standing caveat is **batch fixed-field updates** (Sierra
Global Update), a known class that *may* alter the fixed field without bumping `updatedDate`; not
specifically confirmed for suppression.

**Type:** By design (with a batch-op residual).

**How to handle:** Rely on the change poll for interactive toggles. Cover the batch-op residual with
a periodic id/field reconciliation — a cheap `fields=id,suppressed` re-sweep compared against your
stored value — the same reconcile the [Change polling](change-polling.md) page prescribes for
deletions. A one-time baseline (re-derive from stored MARC, or one `fields=id,suppressed` sweep)
seeds the column.

**How we know:** Design-resolved from the fixed-field semantics above plus the API's read-only
treatment of `suppressed`; the batch-op exception is the documented Global-Update behavior, flagged
here as an unverified residual to reconcile against rather than a confirmed bump.
