"""Test helpers: fake `_fetch` results and real httpx exception builders, so
tool tests never hit the network.
"""

import json
from typing import Any

import httpx

ENVELOPE_FIELDS = {"data", "source", "trace", "policy", "errors", "benchmark", "provenance"}


def fetch_ok(payload: Any) -> tuple[Any, None]:
    """Build the `(payload, error)` tuple `_fetch` returns on success."""
    return payload, None


def fetch_fail(error: Exception) -> tuple[None, Exception]:
    """Build the `(payload, error)` tuple `_fetch` returns on failure."""
    return None, error


def http_status_error(status_code: int, url: str = "https://registry.example.org/services") -> httpx.HTTPStatusError:
    request = httpx.Request("GET", url)
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


def connect_error(url: str = "https://registry.example.org/services") -> httpx.ConnectError:
    return httpx.ConnectError("Connection refused", request=httpx.Request("GET", url))


def fake_fetch(result: tuple[Any, Any]):
    """An async stand-in for `ga4gh_registry._fetch` that returns `result` regardless of input."""

    async def _fetch(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
        return result

    return _fetch


async def call(tool_fn, **kwargs: Any) -> dict[str, Any]:
    """Call an MCP tool function directly and parse its JSON envelope."""
    return json.loads(await tool_fn(**kwargs))
