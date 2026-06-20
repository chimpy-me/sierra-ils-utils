# sierra-ils-utils

**The unofficial Sierra REST API field guide — for developers, builders, and hackers.**

`sierra-ils-utils` is a small Python library that wraps [HTTPX](https://www.python-httpx.org/)
to make the [Sierra ILS](https://www.iii.com/) REST API pleasant to work with: automatic OAuth2
token handling, sync **and** async requests, retries with backoff, and typed responses.

But this site is more than library docs. The Sierra REST API has **sparse official documentation
and a lot of non-obvious behavior**. This guide collects what we learned the hard way — across real
projects touching tens of thousands of records — so you don't have to discover it mid-batch on
production data.

## Where to go

- **[Get Started](tutorials/getting-started.md)** — new here? Go from zero to your first successful
  API call: get credentials, install, authenticate, and read a record.
- **[The Quirks Catalog](reference/quirks/index.md)** — the crown jewel. Every gotcha we've hit:
  additive `phones`, full-replace `varFields`, the 204 that isn't 200, timestamp side effects, ghost
  records — each with how to handle it and how we know.

## A note on trust

The behaviors documented here were observed empirically on real Sierra deployments (production and
test). Sierra deployments differ in version and configuration, so **treat every quirk as "verify on
your own deployment."** Each catalog entry includes a *How we know* line so you can judge how solid
the finding is — and the guide tells you [how to probe safely yourself](reference/quirks/index.md).

This is a community field guide, not an official Innovative/Clarivate product. Corrections and
additions are welcome at [GitHub](https://github.com/chimpy-me/sierra-ils-utils).
