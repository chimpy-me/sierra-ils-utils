# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

**sierra-ils-utils** is a Python library that wraps httpx to provide convenient methods for interacting with the Sierra ILS (Integrated Library System) REST API v6. The library handles OAuth2 client credentials authentication automatically and includes configurable retry/backoff logic.

## Key Components

- **SierraRESTClient** (`sierra_rest_client.py`): Core HTTP client with sync (`request()`) and async (`async_request()`) methods. Handles token management, 401 refresh, and 5xx retries.
- **SierraDateTime/SierraDate** (`sierra_datetime.py`): Datetime wrappers ensuring Sierra API-compatible formatting (UTC, no microseconds, 'Z' suffix).
- **get_max_record_id** (`utils.py`): Utility to find maximum valid record ID using exponential/binary search.

## Development Commands

```bash
# Install dependencies (including dev/test)
uv sync --all-extras

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Build the package
uv build
```

## Architecture Notes

- The client maintains separate sync and async httpx clients internally
- Token management is thread-safe (sync) and async-lock protected (async)
- Custom httpx clients can be injected for caching (e.g., hishel)
- `SierraAPI` is an alias for `SierraRESTClient`
- Supports both sync and async context managers (`with` / `async with`)

## Testing

Tests use `pytest` with `respx` for HTTP mocking. Run with `uv run pytest`.

## TODO / Planned Improvements

### Code Quality

- [x] Remove duplicate max ID code (`sierra_get_max_id.py` removed)
- [x] Add context manager support (`__enter__`/`__exit__`, `__aenter__`/`__aexit__`)
- [x] Add type hints to `SierraRESTClient`
- [x] Fix token refresh placement in async_request (now inside retry loop)
- [x] Fix 401 token refresh to force new token regardless of expiry
- [x] Add `py.typed` marker for better IDE support
- [x] Export `__version__` from package

### Testing

- [x] Add tests for timeout/retry behavior
- [x] Add tests for `get_max_record_id()`
- [x] Add tests for custom client injection
- [x] Add tests for context manager
- [x] Add tests for sync 5xx retry
- [x] Add tests for async 401 refresh
- [x] Add tests for token expiry/refresh mid-session
- [x] Add tests for infinite loop protection (401)

### Features

- [ ] Add async version of `get_max_record_id()`
- [ ] Add convenience methods (`get()`, `post()`, etc.)
- [ ] Consider rate limiting support
- [ ] Add MARC record utilities using pymarc (optional `[marc]` extra)
