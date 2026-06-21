# Safely edit a record (GET-modify-PUT)

**Goal:** change one or more `varFields` on a patron (or bib/item) record without
destroying the fields you didn't touch.

A `PUT` that includes `varFields` **replaces the entire array** — every varField you omit
is deleted. So you never construct a PUT body from scratch; you fetch the whole record,
edit it in memory, and PUT the *complete* array back.

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

Edit the list you fetched, leaving every entry you don't intend to change untouched. Drop
any entry whose `content` is empty before sending — Sierra silently removes empty-content
varFields on save, so pre-filtering keeps your before/after comparison honest.

```python
varfields = [vf for vf in varfields if vf.get("content")]   # drop empty-content entries
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

- **Full-array replacement** — step 1's `fields=,` + step 3's complete-array PUT is the
  whole point; omitting a varField deletes it.
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

- [Write semantics → PUT varFields is full replacement](../reference/quirks/write-semantics.md)
- [Reads & IDs → `fields=,` returns all fields](../reference/quirks/reads-and-ids.md)

**Why this is necessary:**
[Why writes have side effects](../explanation/sierra-rest-thin-projection.md)
