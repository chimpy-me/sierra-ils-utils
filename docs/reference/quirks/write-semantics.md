# Write semantics

How `PUT` actually behaves when you modify a record. Read this before you write anything back to
Sierra — it's where the costly surprises live.

## PUT `phones` is additive, not replacement

**Behavior:** Including a top-level `phones` array in a `PUT` body **appends** those phones to the
existing list instead of replacing it — the opposite of how most fields behave. You get duplicate
phone entries.

**Type:** Bug-or-quirk.

**How to handle:** Don't send the top-level `phones` key at all. Manage phone data through
`varFields` (phone field tags) instead, which follow normal replacement rules.

**How we know:** A pilot batch returned `204` (success) on every record, yet verification showed
every record had gained duplicate phone entries. Removing the `phones` key from the payload fixed it.

## PUT `varFields` is full replacement

**Behavior:** When `varFields` is present in a `PUT` body, it **replaces the entire array**. Any
varField you omit is deleted — names, barcodes, addresses, notes, everything.

**Type:** By design.

**How to handle:** Use **GET-modify-PUT**: fetch the full record (`fields=,`), modify the varFields
array in memory, then PUT back the *complete* array including everything you want to keep.

```python
# 1. GET the full record
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})
record = resp.json()

# 2. Modify varFields in memory, keeping everything you don't touch
varfields = record.get("varFields", [])
# ... edit varfields ...

# 3. PUT the COMPLETE array back
client.request("PUT", f"patrons/{record_num}", json={"varFields": varfields})
```

For the full safe-write procedure, see [Safely edit a record (GET-modify-PUT)](../../how-to/safe-get-modify-put.md).

**How we know:** Confirmed repeatedly across large patron cleanups, and re-confirmed with a
controlled sentinel probe (append a known marker, verify, then PUT the originals back to remove it).

## A successful PUT returns `204`, not `200`

**Behavior:** A successful update returns HTTP **204 No Content**. There is no response body.

**Type:** By design (standard REST, but easy to miss).

**How to handle:** Check for `204`. Don't call `.json()` on the response — there's nothing to parse.

```python
resp = client.request("PUT", f"patrons/{record_num}", json=patch)
if resp.status_code == 204:
    ...  # success, no body
```

**How we know:** Every successful patron update across tens of thousands of records returned `204`.

## `fixedFields` PUT requires `label` beside `value`

**Behavior:** A `fixedFields` entry in a `PUT` body must include **both** `label` and `value`. Sending
just `value` makes Sierra reject the **entire** payload with `400 Invalid JSON : field(s) unknown :
fixedFields.`

**Type:** By design (asymmetric: GET responses always include `label`, so it's easy to assume
`value`-only works on write).

**How to handle:** Include the canonical label string for each field:

```python
# Rejected (400):
{"fixedFields": {"268": {"value": "p"}}}

# Accepted (204):
{"fixedFields": {"268": {"label": "Notice Preference", "value": "p"}}}
```

Some fields also have a top-level convenience key (e.g. manual block via `blockInfo`); others, like
notice preference, only work through `fixedFields`.

**How we know:** An entire batch failed with thousands of identical `400`s until the `label` key was
added; the same payload then returned `204`.

## PUT rejects ~9 read-only top-level fields

**Behavior:** Several fields returned on `GET` are **rejected** on `PUT`. A naïve "PUT back what I
GETted" fails with `400 Invalid JSON : field(s) unknown : ...` listing fields such as `id`,
`homeLibrary`, `autoBlockInfo`, `message`, `moneyOwed`, `suppressed`, `updatedDate`, `deleted`,
`createdDate`.

**Type:** By design.

**How to handle:** Send only the mutable subset you actually want to change. For varField edits,
`{"varFields": [...]}` alone is sufficient — don't echo the whole GET response back.

**How we know:** Surfaced building a rollback that PUT a full GET response verbatim; Sierra named the
unknown fields in the `400`.

## Empty-content varFields are silently dropped on PUT

**Behavior:** If a `PUT` body's `varFields` array contains an entry whose `content` is empty,
Sierra **silently removes** that entry on save. The PUT still returns `204`.

**Type:** Bug-or-quirk.

**How to handle:** Pre-filter empty-content varFields before sending (`if vf.get("content"):`), or
treat "an empty varField disappeared" as benign in any before/after verification.

**How we know:** Records whose snapshot held an empty alternate-phone varField came back without it
after a `204` PUT; a survey found every empty-content varField dropped and none preserved.

## `emails`/`phones`/`addresses`/`names` are derived projections

**Behavior:** These four top-level fields are **not independent state** — Sierra renders them from
the underlying `varFields` and **re-renders** them after every `varFields` PUT.

**Type:** By design.

**How to handle:** Don't compare these top-level arrays before/after a write to detect "did something
else change?" — they shift on every legitimate varField edit. Compare the underlying varFields
instead. See [Why writes have side effects](../../explanation/sierra-rest-thin-projection.md) for the underlying reason.

**How we know:** Equality checks on these arrays false-positived on every successful varField edit
during pilot runs; switching the check to the underlying varFields resolved it.
