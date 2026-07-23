# Verify write semantics on your deployment

**Goal:** re-derive the claims in [Write semantics](../reference/quirks/write-semantics.md) —
the per-`fieldTag`-group PUT model and the varField deletion table — on **your own** Sierra,
using the reversible probe that produced them. Sierra behavior is deployment- and
version-specific; don't take that page's word for it.

The probe ([`scripts/probe-varfield-write-semantics.py`](https://github.com/chimpy-me/sierra-ils-utils/blob/main/scripts/probe-varfield-write-semantics.py))
is designed to be safe to run:

- It **refuses to run against anything that doesn't look non-prod** (URL must contain
  `test` or `train`).
- Every write is **snapshot → mutate → observe → restore → verify-restored**. A record that
  doesn't come back to baseline is flagged loudly (`!! DID NOT RESTORE`).
- It touches only free-text/local field tags — never barcodes, names, or identity fields —
  and prints only field *structure* and content hashes, never contents.

## Before you start

- A **non-production** Sierra (test or train server) reachable from your machine.
- An API key/secret for it with **read and write** scope on **patrons, items, and bibs**
  (Sierra admin: the key's permissions must include record update). A read-only key will
  fail at the first PUT with `401`/`403` — that's your key's scope, not a quirk.
- A checkout of this repo and [uv](https://docs.astral.sh/uv/) (the probe imports
  `sierra_ils_utils` and needs the project's dependencies — plain `python3` will typically
  fail with `ModuleNotFoundError: httpx`).

```bash
git clone https://github.com/chimpy-me/sierra-ils-utils.git
cd sierra-ils-utils
uv sync
```

## 1. Create a config file for the non-prod system

```json
{
  "sierra_api_base_url": "https://sierra-test.example.org/iii/sierra-api/v6/",
  "sierra_api_key": "...",
  "sierra_api_secret": "..."
}
```

Save it somewhere outside the repo, e.g. `~/.config/sierra/api-test.json`.

## 2. Run the probe

```bash
SIERRA_API_CONFIG=~/.config/sierra/api-test.json \
    uv run python scripts/probe-varfield-write-semantics.py --kinds patron,item,bib
```

!!! warning "If the probe refuses to run"
    The guard rejects any base URL that doesn't contain `test` or `train`. If your sandbox
    is named differently, **don't** reflexively reach for `--allow-prod` — that flag means
    "mutate whatever this URL points at, I've checked." First confirm the URL really is a
    sandbox; only then pass the flag. Never point this script at production.

## 3. Read the output

A healthy run looks like this (record ids truncated by the probe):

```text
host: sierra-test.example.org

=== PATRON ===
  group-model on ...0017 (repeated tag 'x', 2 members):
    drop ONE (keep siblings): PUT 204 -> dropped 1 of 'x', DELETED
    drop ALL (send none)     : PUT 204 -> dropped 2 of 'x', SURVIVED
  deletion / patron/content on ...0017 tag='x' (PUT-mutates control: True):
      content=""       -> REMOVED
      content=null     -> HTTP 400

=== ITEM ===
  group-model on ...0204 (repeated tag 'x', 2 members):
    drop ONE (keep siblings): PUT 204 -> dropped 1 of 'x', DELETED
    drop ALL (send none)     : PUT 204 -> dropped 2 of 'x', SURVIVED
  deletion / item/content on ...0009 tag='s' (PUT-mutates control: True):
      content=""       -> BLANK-SHELL
      content=null     -> HTTP 400
  deletion / item/subfields on ...0002 tag='a' (PUT-mutates control: True):
      content=""       -> HTTP 400
      content=null     -> HTTP 400
      subfields=[]     -> HTTP 400
      subfields-blank  -> BLANK-SHELL

=== BIB ===
  ... (same shape as item, except patron-style REMOVED never appears)
```

How each line maps to the write-semantics page:

| Output | Claim it verifies |
|---|---|
| `drop ONE ... DELETED` + `drop ALL ... SURVIVED` | The **per-`fieldTag`-group replace** model — omission deletes only when a same-tag sibling is still sent |
| `PUT-mutates control: True` | The positive control: this record's varFields demonstrably change via PUT, so a later `SURVIVED`/`IGNORED` can't be a silent no-op. **If this is `False`, discard that section's results** |
| `content="" -> REMOVED` (patron) vs `-> BLANK-SHELL` (item/bib) | The deletion-table split: blanking fully removes a patron content field but only empties an item/bib one |
| `-> HTTP 400` rows | The rejected-payload cells of the deletion table |
| no `!! DID NOT RESTORE` anywhere | Every probed record was returned to its baseline |

## 4. If a trial is skipped

A line like `group-model: no record with a repeated safe tag on item in scanned window — skipped`
means the probe couldn't find a suitable record among the first ~2,000 ids and **that cell is
unmeasured on your system** — don't extrapolate it from the other record types. Widen the scan
(raise `pages=` in `Probe.batch`) or point it at a record range you know has repeated notes.

## Verify

Compare your run against the table and rule in
[Write semantics](../reference/quirks/write-semantics.md). If any outcome **differs**, trust
your run over the page — behavior varies by Sierra version and configuration — and please
[open an issue](https://github.com/chimpy-me/sierra-ils-utils/issues) with your Sierra
version and the probe output so the catalog can record the variance.

---

**Underlying behavior (reference):**

- [Write semantics → PUT varFields replaces per fieldTag group](../reference/quirks/write-semantics.md)

**Why this method is trustworthy:**
[Discovering quirks yourself](../explanation/discover-quirks-yourself.md)
