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

## PUT `varFields` replaces per `fieldTag` group

**Behavior:** A `PUT` containing `varFields` is **neither a whole-array replace nor a plain merge**
— it replaces **one `fieldTag` group at a time**. For every fieldTag present in your payload, Sierra
rewrites that tag's entire group to exactly the fields you sent; a fieldTag you send **no** members
of is left untouched. Two consequences that look contradictory until you see the rule:

- Send one of a tag's two fields (drop the other) → the dropped sibling **is deleted**.
- Send **none** of a tag → every field of that tag **survives** — which is why "just omit it from
  the array" silently does nothing when the field is the *only* one of its tag.

**Type:** By design.

### Deleting a field

Two routes, depending on the field:

1. **It shares its `fieldTag` with fields you're keeping** — send those, omit the target. The
   group is rewritten without it, so it's removed. Works on patron, item, and bib.
2. **It's the only field of its tag** (or you want the whole tag gone) — omission can't do it
   (sending none = untouched). Send the field with **empty `content`** instead. What that does is
   **record-type-specific**:

| Field | `content: ""` | `subfields: []` | subfields blanked | `content: null` |
|---|---|---|---|---|
| **Patron** · content | **removed** | — | — | 400 |
| **Item / Bib** · content | blanked to an empty shell (row stays) | — | — | 400 |
| **Item / Bib** · subfields | 400 | 400 | blanked to an empty shell | 400 |

So a **patron** content varField is the one field with a clean full removal by blanking. For item
and bib fields — and any subfield-bearing field — blanking only leaves an empty shell; the only
clean removal is route 1 (drop one of a repeated tag). This matches Innovative treating standalone
item/bib varField deletion as an enhancement request.

**Editing** an existing field: GET-modify-PUT — fetch `fields=,`, change the field in place, PUT
back. Keeping each field's identity is what makes the group-replace *update* it rather than
duplicate it. See [Safely edit a record](../../how-to/safe-get-modify-put.md).

```python
# Delete a patron varField by blanking its content (patrons drop empty-content entries):
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})
varfields = resp.json().get("varFields", [])
for vf in varfields:
    if vf.get("fieldTag") == "x" and is_target(vf):
        vf["content"] = ""            # empty STRING, not None (null -> 400); patron drops the entry
client.request("PUT", f"patrons/{record_num}", json={"varFields": varfields})

# Delete ONE of several same-tag fields on ANY record type: send the keepers, omit the target.
keep = [vf for vf in varfields if not is_target(vf)]   # target shares its fieldTag with a keeper
client.request("PUT", f"items/{record_num}", json={"varFields": keep})   # target's tag-group rewritten w/o it

# On an item/bib, blanking only EMPTIES the field — the row stays (NOT a removal):
after = client.request("GET", f"items/{record_num}", params={"fields": ","}).json()["varFields"]
[vf for vf in after if vf.get("fieldTag") == "x"]   # -> [{"fieldTag": "x", "content": "", ...}]
```

**How we know:** Re-derived on sierra-test 2026-07-23 with a reversible probe
(`scripts/probe-varfield-write-semantics.py`) that first proves each PUT mutates the record (a
positive control), so a "survived" result can't be a silent no-op. The per-`fieldTag`-group rule
was confirmed on **patron, item, and bib** (drop one of a repeated tag → the sibling is deleted;
drop the whole tag → all survive). The deletion table was measured for **content and subfield
fields on item and bib**, and for **content fields on patron** (patron varFields carry only
`content` — no subfield-bearing patron field was found to test). Each cell was measured on one
representative field tag per record type; we assume Sierra treats tags uniformly within a record
type, but that dimension was not swept. An earlier draft of this page called the behaviour "full
replacement", then "merge" — both were partial views of the per-tag-group rule. Behaviour is
deployment- and version-specific; re-run the probe on your own system before relying on it —
see [Verify write semantics on your deployment](../../how-to/verify-write-semantics.md).

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

## Empty-content varFields: dropped on patrons, blanked on items and bibs

**Behavior:** An entry sent with empty `content` behaves **by record type** on save (the PUT
returns `204` either way):

- **Patron:** Sierra **removes the entry entirely** — the patron deletion lever (see
  [PUT varFields replaces per fieldTag group](write-semantics.md) above).
- **Item and bib:** the entry is **kept with empty content** (an empty shell); it is *not* removed.

**Type:** By design on patrons (it is the deletion path); the patron-vs-item/bib split is a quirk.

**How to handle:** If you *don't* intend a deletion, pre-filter empty-content varFields before
sending (`if vf.get("content"):`) so you don't blank a patron field by accident. In before/after
verification, treat "an empty patron varField disappeared" as expected.

**How we know:** On sierra-test (2026-07-23), `content: ""` removed the field on every patron tested
and left an empty shell on every item and bib tested.

## `emails`/`phones`/`addresses`/`names` are derived projections

**Behavior:** These four top-level fields are **not independent state** — Sierra renders them from
the underlying `varFields` and **re-renders** them after every `varFields` PUT.

**Type:** By design.

**How to handle:** Don't compare these top-level arrays before/after a write to detect "did something
else change?" — they shift on every legitimate varField edit. Compare the underlying varFields
instead. See [Why writes have side effects](../../explanation/sierra-rest-thin-projection.md) for the underlying reason.

**How we know:** Equality checks on these arrays false-positived on every successful varField edit
during pilot runs; switching the check to the underlying varFields resolved it.
