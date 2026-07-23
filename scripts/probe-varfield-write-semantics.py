#!/usr/bin/env python3
"""Probe Sierra REST varField write-semantics against a live (NON-PROD) deployment.

Empirically re-derives, on your own system, how `PUT {record}s/{id} {"varFields":[...]}`
behaves — because this is deployment- and version-specific and worth confirming before you
trust it (see docs/reference/quirks/write-semantics.md).

It answers two questions, reversibly:

  1. GROUP MODEL — is a PUT a full-array replace, a merge, or per-`fieldTag`-group replace?
     (Drops one member of a repeated tag while keeping a sibling, vs. dropping the whole tag.)

  2. DELETION TABLE — for content-string vs subfields-array fields, what actually removes a
     field: omission, `content:""`, `subfields:[]`, blanked subfields, or `content:null`?

SAFETY
  * Refuses to run unless the base URL looks non-prod (contains 'test' or 'train'),
    unless you pass --allow-prod (don't).
  * Every write is reversible: snapshot -> mutate -> observe -> PUT original back -> verify.
    Any record that does not restore to baseline is reported loudly.
  * Only field *structure* and sha1 content-hashes are printed — never field contents.
  * Targets only "safe" free-text/local field tags; never identity/system tags
    (patron '=', name/address; bib leader '_'; item barcode 'b').

USAGE
  SIERRA_API_CONFIG=~/.config/sierra/api-test.json \
      python scripts/probe-varfield-write-semantics.py --kinds patron,item,bib

  Config JSON: {"sierra_api_base_url": "...", "sierra_api_key": "...", "sierra_api_secret": "..."}
"""
import argparse, json, os, sys, hashlib, copy
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sierra_ils_utils import SierraRESTClient

SAFE_TAGS = {
    "patron": {"x", "t", "z"},          # notes / stat fields — never '=', name, address
    "item":   {"x", "m", "a", "c", "s"},# notes, call-no; never barcode 'b'
    "bib":    {"y", "o", "d", "r", "s", "n"},  # local / repeatable; never leader '_'
}
SENT = "ZZZ-VARFIELD-PROBE-DO-NOT-KEEP"
h = lambda s: hashlib.sha1((s or "").encode()).hexdigest()[:10] if s else "-"


def key(v):
    return (v.get("fieldTag"), h(v.get("content")),
            tuple(h(s.get("content")) for s in (v.get("subfields") or [])))


def structure(v):
    return "subfields" if v.get("subfields") else ("content" if v.get("content") else "empty")


class Probe:
    def __init__(self, client):
        self.c = client

    def get(self, kind, rid):
        return self.c.request("GET", f"{kind}s/{rid}", params={"fields": ","}).json().get("varFields", [])

    def put(self, kind, rid, vfs):
        return self.c.request("PUT", f"{kind}s/{rid}", json={"varFields": vfs})

    def batch(self, kind, n=200):
        return self.c.request("GET", f"{kind}s", params={"limit": n, "fields": "id,varFields"}).json().get("entries", [])

    # ---- part 1: group model ----
    def group_model(self, kind):
        rid = mtag = None
        for e in self.batch(kind):
            c = Counter(v.get("fieldTag") for v in e.get("varFields", []) if v.get("fieldTag") in SAFE_TAGS[kind])
            multi = [t for t, k in c.items() if k >= 2]
            if multi:
                rid, mtag = e["id"], multi[0]
                orig = copy.deepcopy(e["varFields"])
                break
        if rid is None:
            print(f"  group-model: no record with a repeated safe tag on {kind} (singletons only) — skipped")
            return
        base = sorted(key(v) for v in orig)
        grp = [v for v in orig if v.get("fieldTag") == mtag]

        def trial(label, pred):
            payload = [v for v in orig if pred(v)]
            dropped = [key(v) for v in orig if not pred(v)]
            r = self.put(kind, rid, payload)
            after = sorted(key(v) for v in self.get(kind, rid))
            survived = [d for d in dropped if d in after]
            self.put(kind, rid, orig)
            restored = sorted(key(v) for v in self.get(kind, rid)) == base
            verdict = "SURVIVED" if survived else "DELETED"
            print(f"    {label}: PUT {r.status_code} -> dropped {len(dropped)} of '{mtag}', {verdict}"
                  + ("" if restored else "   !! DID NOT RESTORE"))

        print(f"  group-model on ...{str(rid)[-4:]} (repeated tag '{mtag}', {len(grp)} members):")
        first = key(grp[0])
        trial("drop ONE (keep siblings)", lambda v: key(v) != first)
        trial("drop ALL (send none)     ", lambda v: v.get("fieldTag") != mtag)

    # ---- part 2: deletion table ----
    def deletion(self, kind):
        rows = []
        for need in ("content", "subfields"):
            rec = next(((e["id"], i, e["varFields"])
                        for e in self.batch(kind)
                        for i, v in enumerate(e.get("varFields", []))
                        if v.get("fieldTag") in SAFE_TAGS[kind] and structure(v) == need), None)
            if not rec:
                continue
            rid, idx, orig = rec
            orig = copy.deepcopy(orig)
            base = sorted(key(v) for v in orig)
            tid = key(orig[idx]); tag = orig[idx]["fieldTag"]

            # positive control: prove the PUT mutates this record's varFields
            self.put(kind, rid, orig + [{"fieldTag": tag, "content": SENT}])
            ctrl = (tag, h(SENT), ()) in [key(v) for v in self.get(kind, rid)]
            self.put(kind, rid, orig)

            methods = {'content=""': lambda v: {**v, "content": ""},
                       "content=null": lambda v: {**v, "content": None}}
            if need == "subfields":
                methods["subfields=[]"] = lambda v: {**v, "subfields": []}
                methods["subfields-blank"] = lambda v: {**v, "subfields": [{**s, "content": ""} for s in v.get("subfields", [])]}

            print(f"  deletion / {kind}/{need} on ...{str(rid)[-4:]} tag='{tag}' (PUT-mutates control: {ctrl}):")
            for mname, mut in methods.items():
                payload = [(mut(v) if key(v) == tid else v) for v in orig]
                r = self.put(kind, rid, payload)
                after = [key(v) for v in self.get(kind, rid)]
                if r.status_code != 204:
                    outcome = f"HTTP {r.status_code}"
                elif tid in after:
                    outcome = "IGNORED"
                elif any(k[0] == tag and k not in base for k in after):
                    outcome = "BLANK-SHELL"
                elif sum(k[0] == tag for k in after) < sum(k[0] == tag for k in base):
                    outcome = "REMOVED"
                else:
                    outcome = "?"
                self.put(kind, rid, orig)
                restored = sorted(key(v) for v in self.get(kind, rid)) == base
                flag = "" if restored else "  !! DID NOT RESTORE"
                print(f"      {mname:16s} -> {outcome}{flag}")
                rows.append((kind, need, mname, outcome))
        return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.environ.get("SIERRA_API_CONFIG"),
                    help="JSON with sierra_api_base_url/key/secret (or $SIERRA_API_CONFIG)")
    ap.add_argument("--kinds", default="patron,item,bib", help="comma list of record types")
    ap.add_argument("--allow-prod", action="store_true", help="override the non-prod guard (don't)")
    a = ap.parse_args()
    if not a.config:
        ap.error("no --config / $SIERRA_API_CONFIG")
    cfg = json.load(open(os.path.expanduser(a.config)))
    url = cfg["sierra_api_base_url"]
    if not a.allow_prod and not any(t in url for t in ("test", "train")):
        sys.exit(f"REFUSING: {url!r} does not look non-prod; pass --allow-prod to override (don't).")
    client = SierraRESTClient(base_url=url, client_id=cfg["sierra_api_key"], client_secret=cfg["sierra_api_secret"])
    probe = Probe(client)
    print(f"host: {url.split('//')[-1].split('/')[0]}")
    for kind in [k.strip() for k in a.kinds.split(",") if k.strip()]:
        if kind not in SAFE_TAGS:
            print(f"skip unknown record type {kind!r}"); continue
        print(f"\n=== {kind.upper()} ===")
        probe.group_model(kind)
        probe.deletion(kind)


if __name__ == "__main__":
    main()
