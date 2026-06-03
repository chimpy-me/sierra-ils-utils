# Reads & IDs

How to fetch complete records, and how the API's record identifiers relate to the underlying
database.

## `fields=,` returns all fields; allow-lists may 400

**Behavior:** Passing `params={"fields": ","}` (a bare comma) makes a `GET` return **all** available
fields — `varFields`, `fixedFields`, `phones`, etc. Without it, you get a minimal response. An
explicit allow-list of field names is risky: some valid-sounding names cause a `400` (`Invalid
parameter : <field> is not a valid field ...`) depending on what the deployment has materialized.

**Type:** By design (the `fields=,` form is undocumented; allow-list rejection is deployment-specific).

**How to handle:** Use `fields=,` whenever you need the full record (for example, before a
GET-modify-PUT). Avoid building explicit allow-lists — they're deployment-specific landmines.

```python
resp = client.request("GET", f"patrons/{record_num}", params={"fields": ","})
```

**How we know:** The `fields=,` trick has been relied on across multiple projects; separately, a
plausible-looking field name returned `400` on one deployment's patron model.

## "Ghost records": GET 200 but PUT 404

**Behavior:** Some records return `200` to a `GET` but `404` (`Patron record not found`) to a `PUT`.
They're visible in the database view and readable, but not writable through the API.

**Type:** Bug-or-quirk (likely soft-deleted or otherwise inconsistent records).

**How to handle:** Treat a `404` on PUT as a **non-fatal skip**, even when a prior GET succeeded. A
successful GET does not guarantee the PUT will work.

**How we know:** Individual records returned `200` on GET and `404` on PUT during side-effect testing
and again during a large batch — a small but real fraction.

## API `id` = `record_num`, not the database primary key

**Behavior:** The REST API's `id` field is the record's **record number** (the human-facing number,
also used in URL paths), **not** the database's internal primary key. In the SQL views these are two
different columns.

**Type:** By design.

**How to handle:** Use the API `id` (the record number) in request paths (`patrons/{record_num}`).
When joining API data to the database, map the API `id` to the record-number column — not to the
internal primary-key column. The two are easy to confuse because both are large integers.

**How we know:** Joining API results to the database on the wrong column silently returns nothing;
mapping API `id` → the record-number column fixes it.

## Multiple values packed into one varField

**Behavior:** A single varField's `content` sometimes holds **several values separated by commas**
(for example, two email addresses in one field) rather than one value per varField.

**Type:** Data quality.

**How to handle:** Split on the delimiter before processing, and rejoin after filtering. Anchored
regex (`^...$`) over the whole field will miss values that aren't first or last.

```python
def split_values(content: str) -> list[str]:
    return [v.strip() for v in (content or "").split(",") if v.strip()]
```

**How we know:** In a large patron dataset, a meaningful number of email varFields held
comma-separated lists; treating each varField as a single value produced wrong classifications.

## varField content length ceiling is ≥ 8000 chars

**Behavior:** A varField's `content` accepts and stores **at least 8000 characters** verbatim — far
more than you'd expect for a "note" field.

**Type:** By design.

**How to handle:** Length is rarely the constraint. Keep system-written notes concise for human
readability rather than because of an API limit; the ceiling is high enough that it's effectively a
non-issue for normal use.

**How we know:** A ladder test (100 → 8000 chars) on a test record stored every size verbatim with no
truncation.
