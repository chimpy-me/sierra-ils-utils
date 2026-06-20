# Why writes have side effects: Sierra REST is a thin projection over the DB

If a single mental model saves you from the write-side surprises in this guide, it's
this one: **the Sierra REST API is a thin layer over the Sierra database, not a store
with its own state.** It reads and writes the same underlying tables that the Desktop
client and the SQL views see. Almost every "why does a write do *that*?" question
follows from that one fact.

## The model

The API does not hold an independent copy of a record. On a read it *renders* a JSON
view from the underlying rows; on a write it *applies* your changes back to those same
rows and re-renders. There is no separate API-side representation that could behave
differently from the database — which is exactly why the behaviors below are so
stubborn: they aren't API conveniences that a flag could turn off, they're properties
of the store.

## What follows from it

**The convenient top-level arrays are projections, not state.** `emails`, `phones`,
`addresses`, and `names` are *rendered from* the underlying `varFields` on every read,
and **re-rendered after every write**. They look like fields you could set, but they
have no independent existence — which is why writing them behaves oddly and why
comparing them before/after a write to ask "did anything else change?" always
false-positives. The varFields are the real state.

**A write is a write, even a byte-identical one.** Because your PUT is applied to the
database rather than diffed against an API cache, a successful PUT moves the record's
housekeeping bookkeeping — Updated Date, Revisions, PDATE, and Last Circ Activity
(CIRCACTIVE) — *even when the payload matches what was already there*. There is no
per-request opt-out because, at the storage layer, there is nothing to opt out of. A
`GET` changes nothing, and a PUT that fails validation (`400`) changes nothing, for the
same reason: only a successful write reaches the rows.

**A REST PUT looks like two saves.** The Revisions counter moves by **2** per REST PUT
but by **1** per Desktop save. The most economical explanation is that a REST write
performs two internal saves — one for your payload and one for the API's own
bookkeeping fields — each of which the store counts as a revision. You don't need the
internals to be certain; the +2 is a reliable, if rough, forensic signal that a change
came through REST rather than the Desktop client.

## Why it matters to you

- **Retention, purge, and dormancy workflows** that key off `activity_gmt` (CIRCACTIVE),
  Updated Date, Revisions, or PDATE will see every touched record as "recently active."
  If that's undesirable, skip records you'd rather not bump — you can't bump them
  "quietly."
- **Verification logic** must treat those four housekeeping fields, and the derived
  top-level arrays, as expected-to-move. Compare the underlying varFields instead.
- **Mirroring or caching Sierra** means respecting that the API is a window onto live
  state, not a system of record you can treat as static between polls.

## See also

- Reference: [Write semantics → derived projections](../reference/quirks/write-semantics.md)
  and [Side effects](../reference/quirks/side-effects.md) — the austere "what happens".
<!-- The "How-to: Safely edit a record" bullet is appended here in Task 3, once that
     page exists, to keep this commit's `mkdocs build --strict` link-clean. -->
