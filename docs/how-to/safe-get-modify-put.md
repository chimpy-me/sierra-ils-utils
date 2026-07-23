# Safely edit a record (GET-modify-PUT)

**Goal:** change or delete `varFields` on a patron (or item) record without corrupting the
fields you didn't touch.

A `PUT` with `varFields` replaces **one `fieldTag` group at a time**: for every fieldTag you send,
Sierra rewrites that tag's whole group with exactly what you sent, and leaves tags you send nothing
of untouched (see
[PUT varFields replaces per fieldTag group](../reference/quirks/write-semantics.md)). You still
fetch the whole record and edit in memory — both so an update keeps each field's identity instead of
duplicating it, and because **deleting** a field means either dropping it *while still sending its
same-tag siblings*, or (patrons only) blanking its `content`.

## Before you start

- A `SierraRESTClient` authenticated against your deployment.
- The record number (`record_num`) of the record you're editing.

## 1. GET the full record

Use the bare-comma `fields=,` form to get **all** fields — without it you get a minimal
response that's missing the varFields you need to preserve.

```python
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})
record = resp.json()
varfields = record.get("varFields", [])
```

## 2. Modify varFields in memory

Edit the list you fetched, leaving every entry you don't intend to change untouched.

- To **change** a field: edit its `content` in place.
- To **delete** a field:
    - if it shares its `fieldTag` with fields you're keeping → just leave it out; sending the
      siblings rewrites that tag-group without it (works on any record type).
    - if it's the **only** field of its tag → set `content` to `""` (patrons remove it; items/bibs
      only blank it — no clean removal there). Don't expect leaving the sole field of a tag out of
      the array to delete it — that sends zero of the tag, so Sierra leaves it untouched.
- If you *don't* want a deletion, drop empty-content entries before sending so you don't blank a
  patron field by accident:

```python
varfields = [vf for vf in varfields if vf.get("content")]   # avoid accidental empty-content deletes
# ... make your edits to varfields here ...
```

## 3. PUT only the mutable subset

Send just `{"varFields": [...]}` — the complete array. Do **not** echo the whole GET
response back: Sierra rejects ~9 read-only top-level fields (`id`, `homeLibrary`,
`updatedDate`, `createdDate`, `deleted`, …) with `400 Invalid JSON : field(s) unknown`.

```python
resp = client.request("PUT", f"patrons/{record_num}", json={"varFields": varfields})
```

## 4. Check for 204, not 200

A successful update returns **`204 No Content`** with no body. Don't call `.json()` on it.

```python
if resp.status_code == 204:
    ...  # success
elif resp.status_code == 404:
    ...  # "ghost record": GET worked but PUT 404s — skip it, non-fatal
else:
    resp.raise_for_status()
```

## Gotchas this recipe already handles

- **Per-tag-group replace** — omitting a field deletes it *only* if you still send another field
  of the same `fieldTag`; the sole field of a tag survives omission. Delete singletons by blanking
  `content` (patrons only). Step 1's `fields=,` + PUT-back preserves each field's identity so edits
  don't create duplicates.
- **Empty-content drop** — step 2 pre-filters so it doesn't surprise your verification.
- **Read-only fields** — step 3 sends only `varFields`, avoiding the `400`.
- **204 not 200** — step 4 checks the right status and never parses an empty body.
- **Ghost records** — step 4 treats a PUT `404` after a successful GET as a non-fatal skip.
- **Don't send top-level `phones`** — it *appends* instead of replacing; manage phone data
  through varFields, which this recipe does by construction.

## Verify

After the PUT, GET the record again with `fields=,` and compare the **underlying
varFields** — not the top-level `emails`/`phones`/`names` arrays, which Sierra re-renders
on every write and will always look "changed".

---

**Underlying behavior (reference):**

- [Write semantics → PUT varFields replaces per fieldTag group](../reference/quirks/write-semantics.md)
- [Reads & IDs → `fields=,` returns all fields](../reference/quirks/reads-and-ids.md)

**Why this is necessary:**
[Why writes have side effects](../explanation/sierra-rest-thin-projection.md)
