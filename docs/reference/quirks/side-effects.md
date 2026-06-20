# Side effects

What a write touches *besides* the data you sent. These matter most for retention, purge, and
freshness workflows that key off record timestamps.

## PUT bumps four `fixedFields` timestamps/counters — with no opt-out

**Behavior:** A successful `PUT` updates several housekeeping `fixedFields` **even when the payload is
byte-identical to what was already on the record**:

| Key | Label | Effect of a PUT |
|---|---|---|
| 84 | Updated Date | set to the PUT timestamp |
| 85 | No. of Revisions | incremented |
| 98 | PDATE | set to the PUT timestamp |
| 163 | Last Circ Activity (CIRCACTIVE) | set to the PUT timestamp |

The CIRCACTIVE bump is the consequential one: Sierra treats *any* patron PUT as circulation activity.

**Type:** By design (no per-request opt-out exists; disabling it is a system-wide vendor setting).

**How to handle:** Assume every PUT moves all four. Any retention/purge/dormancy workflow keyed on
`activity_gmt` (CIRCACTIVE), Updated Date, Revisions, or PDATE will see touched records as "recently
active." If that matters, skip records you'd rather not bump, or accept the bump knowingly. Exclude
these four keys from any "did anything else change?" verification. See [Why writes have side effects](../../explanation/sierra-rest-thin-projection.md) for why an identical PUT still moves them.

**How we know:** A round-trip test (GET → PUT identical data → GET) showed identical content hashes
before and after, but all four timestamps/counters had moved; reconfirmed across thousands of PUTs
on more than one deployment.

## GET never bumps; a failed PUT (400) never bumps

**Behavior:** A `GET` does **not** change any timestamp. A `PUT` that fails validation with `400`
also changes **nothing** — Sierra validates before writing.

**Type:** By design.

**How to handle:** Bulk reads are safe — fetch freely for analysis or backup without polluting
activity timestamps. Batch error handling doesn't need to worry about partial timestamp corruption
from rejected writes.

**How we know:** Side-effect tests on inactive records showed neither `GET` nor a `400`-returning PUT
moved `activity_gmt` or the updated timestamp.

## Revisions counter: +2 per REST PUT vs +1 per Desktop save

**Behavior:** The Revisions counter (fixedField 85) increments by **2** per Sierra REST API PUT, but
by **1** per Sierra Desktop staff save.

**Type:** Bug-or-quirk (the doubling is invisible in the HTTP response but persisted on the record).

**How to handle:** Use it as a rough forensic signal when auditing record history: a `+2` Revisions
delta suggests a REST API touch, `+1` suggests a Desktop save. It's a first cut, not proof — a
coincidence could produce either. See [Why writes have side effects](../../explanation/sierra-rest-thin-projection.md) (a REST PUT is effectively two saves).

**How we know:** REST PUTs were observed moving the counter by 2 (e.g. 42 → 44) while an
empirical Desktop edit moved it by exactly 1. The likely cause is that a REST PUT performs two
internal saves — one for the payload, one for its own bookkeeping fields.
