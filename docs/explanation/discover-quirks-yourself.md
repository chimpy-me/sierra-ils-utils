# Discovering quirks yourself

You don't have to take this catalog on faith. Every entry here started as a behavior
someone observed, then confirmed with a deliberately safe probe — and you can confirm
any of them on your own deployment the same way. This page is about the *method*: how
to learn what Sierra actually does without endangering real data.

## The principle: observe without meaningfully mutating

The whole approach rests on one idea — arrange a write whose *content* effect is nil
while you watch what the system does *around* it. If the data you send back is identical
to what was already there, anything that changed afterward was the system's doing, not
yours. That's what makes side effects visible in isolation.

## How the safe probes work, and why

- **Test against a sandbox, or pick clearly inactive records.** A test/sandbox Sierra is
  ideal; failing that, records you can prove are dormant keep the blast radius near zero.
- **Probe with identical-data PUTs and intentionally malformed PUTs.** An identical-data
  PUT changes no content but still triggers whatever side effects a write carries — so it
  isolates them. A malformed PUT (one Sierra will reject) lets you confirm the
  *validate-before-write* boundary: nothing should move when the write fails.
- **Hash the content fields before and after.** Equal hashes prove the payload is
  unchanged while you watch which housekeeping fields Sierra moved on its own. This is how
  the "an identical PUT still bumps four timestamps" finding was pinned down.
- **Cross-check against the database read-only.** If you have SQL access, comparing the
  API's view against the underlying rows is how you learn things like "the API `id` is the
  record number, not the primary key."

The reason these probes are trustworthy is the model in
[Why writes have side effects](sierra-rest-thin-projection.md): because the API writes
straight to the database, an identical-data PUT exercises the *real* write path, so the
side effects you observe are the real ones — not an artifact of a test double.

## A runnable harness is planned

A deployment-agnostic, sanitized version of this probe harness is planned for a later
phase of this guide, so you can run the confirmations rather than hand-roll them.
