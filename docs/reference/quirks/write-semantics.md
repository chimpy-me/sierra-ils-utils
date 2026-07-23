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

## PUT `varFields` is a merge — delete via empty content, not omission

**Behavior:** A `PUT` containing `varFields` **merges by field identity** — it does **not** replace
the stored array wholesale. Omitting a pre-existing varField does **not** delete it; the omitted
field survives untouched. Deletion works through **empty content** instead:

- **Patron records:** send the varField back with `content: ""` and Sierra **removes the entire
  entry**.
- **Item records:** `content: ""` only **blanks** the field — an empty shell stays on the record.
  A clean, full removal of an item varField via REST appears unsupported (consistent with
  Innovative treating item-varField deletion as an enhancement request).

Sending `content: null` (as opposed to `""`) is rejected with `400 Invalid JSON`.

One trap makes omission *look* like full replacement: a varField you **added via the API** in an
earlier PUT and then omit **is** removed. If you only ever test add-then-remove, you will wrongly
conclude the whole array is replaced on every write.

**Type:** By design (merge-by-identity).

**How to handle:**

- **Editing** existing fields: GET-modify-PUT — fetch the full record (`fields=,`), change what you
  need, PUT it back. Preserving each field's identity is what keeps updates from creating
  duplicates. See [Safely edit a record](../../how-to/safe-get-modify-put.md).
- **Deleting** a patron varField: send it with `content: ""`; don't rely on omitting it.

```python
# Delete a patron varField by blanking its content (NOT by omitting it):
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})
varfields = resp.json().get("varFields", [])
for vf in varfields:
    if vf.get("fieldTag") == "x" and is_target(vf):
        vf["content"] = ""            # empty string, not None; Sierra drops the entry (patron)
client.request("PUT", f"patrons/{record_num}", json={"varFields": varfields})
```

**How we know:** Probed against sierra-test on 2026-07-23 with a reversible add / omit / blank
harness and a positive control (a sentinel field first proved the PUT actually mutates `varFields`,
so a "survived" result couldn't be a silent no-op). Omitting a pre-existing note *or* barcode left
it in place on **both** patron and item records; `content: ""` removed the field on **5/5** patrons
tested (note fields) and only blanked-to-a-shell on items; `content: null` returned `400`. The
earlier "full replacement / omit deletes everything" claim traced to an add-then-remove sentinel
that exercised only the one case where omission deletes. Re-verify on your own deployment and Sierra
version before relying on either behavior.

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

## Empty-content varFields: dropped on patrons, blanked on items

**Behavior:** An entry whose `content` is empty behaves **differently by record type** on save (the
PUT returns `204` either way):

- **Patron:** Sierra **removes the entry entirely** — this is the supported way to *delete* a patron
  varField (see [PUT varFields is a merge](write-semantics.md) above).
- **Item:** the entry is **kept with empty content** (an empty shell); it is *not* removed.

**Type:** By design on patrons (it is the deletion path); the item/patron split is a quirk.

**How to handle:** If you *don't* intend a deletion, pre-filter empty-content varFields before
sending (`if vf.get("content"):`) so you don't blank a patron field by accident. In before/after
verification, treat "an empty patron varField disappeared" as expected.

**How we know:** On sierra-test (2026-07-23), `content: ""` removed the field on every patron tested
and left an empty shell on every item tested. Earlier: records holding an empty alternate-phone
varField came back without it after a `204` PUT.

## `emails`/`phones`/`addresses`/`names` are derived projections

**Behavior:** These four top-level fields are **not independent state** — Sierra renders them from
the underlying `varFields` and **re-renders** them after every `varFields` PUT.

**Type:** By design.

**How to handle:** Don't compare these top-level arrays before/after a write to detect "did something
else change?" — they shift on every legitimate varField edit. Compare the underlying varFields
instead. See [Why writes have side effects](../../explanation/sierra-rest-thin-projection.md) for the underlying reason.

**How we know:** Equality checks on these arrays false-positived on every successful varField edit
during pilot runs; switching the check to the underlying varFields resolved it.
