# Patron validation (`validate`)

How the `POST patrons/validate` endpoint matches the identifier and PIN you hand it — two
non-obvious behaviors that decide whether a login succeeds.

## `caseSensitivity` defaults to `true`, which rejects mismatched-case identifiers

**Behavior:** `POST /v6/patrons/validate` takes a body of `{barcode, pin, caseSensitivity}` and
returns **`204 No Content`** when the credentials are valid (a non-`204`, typically `400`, when they
aren't). The `barcode` field can carry either a barcode or — where the library enables it — a
**uniqueId** (alternate ID / username, varField `u`). The catch is that **`caseSensitivity` defaults
to `true`** (exact-case match). Sierra normalizes stored barcodes to uppercase, so an all-numeric or
already-uppercase barcode validates under the default regardless of how it's typed. A **mixed- or
lower-case identifier** submitted under the default **fails**; flip `caseSensitivity: false` and it
validates. Alt-ids are the usual visible victims because usernames are mixed-case and patrons type
them however they like, whereas barcodes rarely get miscapitalized — but the mechanism is the same
for both.

**Type:** By design (documented) — but the `true` default is a footgun, and the docs advise flipping
it precisely for uniqueId logins or space-bearing barcodes.

**How to handle:** If you accept **either** a barcode or an alt-id and can't know which one the
patron typed, send **`caseSensitivity: false` on every `validate` call**. It's the safe superset: it
folds case for mixed-case alt-ids, absorbs barcodes carrying embedded or trailing spaces, and only
relaxes case on real barcodes — which effectively never collide on case alone. Reserve
`caseSensitivity: true` for the narrow case where you *know* the identifier is a barcode stored in
matching case. **Separately:** whether `validate` accepts the uniqueId as a login identifier *at all*
is a Sierra system-configuration option. If an alt-id never validates under *any* case or flag,
that's the config gate, not `caseSensitivity` — check the system option before chasing case.

```python
resp = client.request(
    "POST", "patrons/validate",
    json={"barcode": identifier, "pin": pin, "caseSensitivity": False},
)
valid = resp.status_code == 204  # 204 = valid; non-204 (usually 400) = invalid
```

!!! tip "Use the minimal validate role, not patron-read"
    Authenticating patrons needs only the **Patron Validate** API application role, not the broader
    **Patron Read** role. `validate` returns a bare `204`/error — never patron PII — so an
    auth-only client should be scoped to just that role (least privilege).

**How we know:** *Tested against API `v6` · sierra-test · 2026-07-10* with a purpose-built, then
deleted, test patron whose barcode Sierra stored uppercase. Submitting that barcode **lower- or
mixed-case returned `400` under `caseSensitivity: true` and `204` under `caseSensitivity: false`**;
the exact-case form validated under both — case-folding on the identifier, exactly as the vendor
documents: *"If your library uses the uniqueId field identifier for patron validation instead of the
barcode, or your library has barcodes that contain spaces (including trailing spaces), use the
caseSensitivity parameter to allow for case-insensitive validation."* On that same deployment the
endpoint **would not validate the patron's uniqueId at all** (under any case or flag) even though the
value was stored on the record — the alt-id-login config option was off — which is how we learned
that acceptance of the uniqueId is a separate system-level gate. The alt-id-specific case behavior
was independently reported from a deployment that *does* enable uniqueId login: there, patrons
validated on their alt-id only with `caseSensitivity: false`.

## `validate` checks only the first 8 characters of the PIN

**Behavior:** `POST /v6/patrons/validate` compares only the **first 8 characters** of the submitted
PIN against the stored PIN. Characters past position 8 are **ignored**: a PIN that is correct in its
first 8 characters validates even when later characters are wrong, and a PIN whose 8th character is
wrong fails. Fewer than 8 correct leading characters fails. In effect, the PIN's authenticating
strength is capped at 8 characters no matter how long the stored PIN is.

**Type:** Bug-or-quirk (undocumented, and security-relevant — it silently caps effective PIN
entropy). Note this is distinct from PIN *complexity*, which Sierra **does** enforce at write time:
setting a "trivial" PIN (e.g. repeated characters) is rejected with `400` `code 136` /
`specificCode 6` *"PIN is not valid : PIN is trivial"*, and PINs longer than 8 characters are
accepted and stored — only the *validate* comparison truncates.

**How to handle:** Don't count on PIN characters beyond the 8th for authentication strength — they
are not checked. If you set or communicate a PIN policy, treat **8** as the significant length, and
don't assume a longer PIN is proportionally stronger against a `validate`-based guessing attempt.
Rate-limit and lock out on repeated failures rather than leaning on PIN length.

**How we know:** *Tested against API `v6` · sierra-test · 2026-07-10* with a purpose-built, then
deleted, test patron whose stored PIN was a non-trivial 10-character value. Validating the full PIN
succeeded (`204`); the first 8 characters alone succeeded; a PIN identical except for a **wrong 9th
or 10th character** still succeeded; a PIN with a **wrong 8th character** failed (`400`); and the
first 7 characters alone failed — pinning the significant length at exactly 8.
