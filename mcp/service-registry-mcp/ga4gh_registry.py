"""GA4GH Service Registry MCP server.

Wraps the GA4GH Service Registry API
(https://github.com/ga4gh/ga4gh-service-registry) and returns every tool
response inside a standardized envelope — data, source, trace, policy,
errors, benchmark, provenance — so agent clients get one consistent,
machine-readable contract regardless of which registry they query.

This is a deliberately minimal first pass covering GA4GH GIF project
issues #3-#5: the example lives in `mcp/`, ships a sample request/response
pair (see `samples/`), and every tool returns all seven envelope fields.
Elaborating any one field further — a typed error taxonomy, richer policy
reasoning, retries, caller/telemetry provenance, etc. — is tracked in
issues #6-#11 and beyond, not implemented here yet. See README.md.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("ga4gh-service-registry")

DEFAULT_REGISTRY_URL = "https://registry.ga4gh.org/v1"
SPEC_VERSION = "1.0.0"  # service-registry.yaml info.version
USER_AGENT = "ga4gh-service-registry-mcp/1.0"
TIMEOUT_SECONDS = 30.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _dumps(envelope: dict[str, Any]) -> str:
    return json.dumps(envelope, indent=2, default=str)


async def _fetch(endpoint: str) -> tuple[Any, httpx.HTTPError | None]:
    """GET an endpoint once. Returns `(payload, None)` or `(None, error)`."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        try:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            return response.json(), None
        except httpx.HTTPError as exc:
            return None, exc


def _match_service_type(service_type: Any, filter_str: str) -> bool:
    """Match a GA4GH ServiceType object against an artifact filter (e.g. 'trs')."""
    if isinstance(service_type, dict):
        return service_type.get("artifact", "").lower() == filter_str.lower()
    return str(service_type).lower() == filter_str.lower()


def _envelope(
    *,
    data: Any,
    endpoint: str,
    request_id: str,
    start: datetime,
    end: datetime,
    decision: str,
    reason_code: str,
    reason_message: str,
    query: dict[str, Any],
    errors: list[dict[str, Any]] | None = None,
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response_time = _now()
    return {
        "data": data,
        "source": {
            "endpoint": endpoint,
            "version": SPEC_VERSION,
        },
        "trace": {
            "request_id": request_id,
            "timing": {
                "start": _iso(start),
                "end": _iso(end),
                "duration_ms": round((end - start).total_seconds() * 1000),
            },
        },
        "policy": {
            "decision": decision,
            "reason": {
                "code": reason_code,
                "message": reason_message,
            },
        },
        "errors": errors or [],
        "benchmark": benchmark,
        "provenance": {
            "query_provenance": query,
            "response_provenance": {
                "source_endpoint": endpoint,
                "retrieved_at": _iso(end),
            },
            "timestamp": _iso(response_time),
        },
    }


def _error_envelope(
    error: httpx.HTTPError, endpoint: str, request_id: str, start: datetime, query: dict[str, Any]
) -> str:
    end = _now()
    status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
    code = f"HTTP_{status_code}" if status_code is not None else "REQUEST_FAILED"
    typed_error = {
        "type": "UpstreamError",
        "code": code,
        "message": str(error),
        "retryable": status_code is None or status_code >= 500,
    }
    return _dumps(_envelope(
        data=None,
        endpoint=endpoint,
        request_id=request_id,
        start=start,
        end=end,
        decision="deny",
        reason_code=code,
        reason_message=str(error),
        query=query,
        errors=[typed_error],
    ))


@mcp.tool()
async def list_services(service_type: str | None = None, registry_url: str | None = None) -> str:
    """List services registered in a GA4GH Service Registry.

    Calls GET {registry_url}/services and, if `service_type` is given,
    filters client-side on the service's `type.artifact` field (e.g.
    "trs", "wes", "tes", "drs").

    Args:
        service_type: Optional artifact filter (trs, wes, tes, drs, etc.)
        registry_url: Optional custom registry base URL (defaults to the
            official GA4GH registry)
    """
    base_url = registry_url or DEFAULT_REGISTRY_URL
    endpoint = f"{base_url}/services"
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    query = {"operation": "getServices", "registry_url": base_url, "service_type": service_type}
    start = _now()

    payload, error = await _fetch(endpoint)
    if error is not None:
        return _error_envelope(error, endpoint, request_id, start, query)

    services = payload if isinstance(payload, list) else []
    if service_type:
        services = [s for s in services if _match_service_type(s.get("type"), service_type)]

    return _dumps(_envelope(
        data={"services": services, "count": len(services)},
        endpoint=endpoint,
        request_id=request_id,
        start=start,
        end=_now(),
        decision="allow",
        reason_code="POLICY_OK",
        reason_message="Request allowed.",
        query=query,
    ))


@mcp.tool()
async def get_service(service_id: str, registry_url: str | None = None) -> str:
    """Get details for a specific GA4GH service by ID.

    Calls GET {registry_url}/services/{serviceId}.

    Args:
        service_id: Service ID to retrieve
        registry_url: Optional custom registry base URL
    """
    base_url = registry_url or DEFAULT_REGISTRY_URL
    endpoint = f"{base_url}/services/{service_id}"
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    query = {"operation": "getServiceById", "registry_url": base_url, "service_id": service_id}
    start = _now()

    payload, error = await _fetch(endpoint)
    if error is not None:
        return _error_envelope(error, endpoint, request_id, start, query)

    return _dumps(_envelope(
        data=payload,
        endpoint=endpoint,
        request_id=request_id,
        start=start,
        end=_now(),
        decision="allow",
        reason_code="POLICY_OK",
        reason_message="Request allowed.",
        query=query,
    ))


@mcp.tool()
async def list_service_types(registry_url: str | None = None) -> str:
    """List all distinct service types exposed by a GA4GH Service Registry.

    Calls GET {registry_url}/services/types.

    Args:
        registry_url: Optional custom registry base URL
    """
    base_url = registry_url or DEFAULT_REGISTRY_URL
    endpoint = f"{base_url}/services/types"
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    query = {"operation": "getServiceTypes", "registry_url": base_url}
    start = _now()

    payload, error = await _fetch(endpoint)
    if error is not None:
        return _error_envelope(error, endpoint, request_id, start, query)

    types = payload if isinstance(payload, list) else []
    return _dumps(_envelope(
        data={"types": types, "count": len(types)},
        endpoint=endpoint,
        request_id=request_id,
        start=start,
        end=_now(),
        decision="allow",
        reason_code="POLICY_OK",
        reason_message="Request allowed.",
        query=query,
    ))


@mcp.tool()
async def get_registry_info(registry_url: str | None = None) -> str:
    """Get service-info metadata about the registry itself.

    Calls GET {registry_url}/service-info.

    Args:
        registry_url: Optional custom registry base URL
    """
    base_url = registry_url or DEFAULT_REGISTRY_URL
    endpoint = f"{base_url}/service-info"
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    query = {"operation": "getServiceInfo", "registry_url": base_url}
    start = _now()

    payload, error = await _fetch(endpoint)
    if error is not None:
        return _error_envelope(error, endpoint, request_id, start, query)

    return _dumps(_envelope(
        data=payload,
        endpoint=endpoint,
        request_id=request_id,
        start=start,
        end=_now(),
        decision="allow",
        reason_code="POLICY_OK",
        reason_message="Request allowed.",
        query=query,
    ))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
