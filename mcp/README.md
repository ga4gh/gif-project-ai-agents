# MCP

This is a schema for GA4GH MCP that has every tool returns the same seven-field response envelope, regardless of which registry endpoint it calls or whether the call succeeded. An agent that learns this contract once can apply it to any other GA4GH MCP server that adopts the same shape (DRS, TRS, WES/TES, Passport), instead of parsing a bespoke format per server.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) — fast Python package manager and runner, used to install dependencies and run every MCP server in this directory

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

<<<<<<< Updated upstream
=======
## The response envelope

Every tool returns a single JSON string (so it survives as plain MCP tool output) with exactly these top-level fields:

| Field | Purpose |
| --- | --- |
| `data` | The normalized payload — the thing the caller actually asked for. `null` on failure. |
| `source` | Which upstream endpoint answered, and the spec version it implements. |
| `trace` | `request_id`, start/end timestamps + duration, and retry count/policy — for debugging and latency reporting. |
| `policy` | `allow` / `deny` / `partial`, plus a machine-readable `reason.code` and a human-readable `reason.message`. |
| `errors` | Array of typed error objects: `type`, `code`, `message`, `retryable`, optional `details`. Empty on success. |
| `benchmark` | Reference to a published benchmark, when a performance/quality claim is being made. `null` otherwise — see [below](#benchmark-field). |
| `provenance` | `query_provenance` (what was asked), `caller_provenance` (who/what asked — see [below](#caller-provenance-harness--model)), `response_provenance` (where/when the answer came from), and a response `timestamp`. |

### Policy decisions

- **`allow`** — the call succeeded and `data` holds the full result.
- **`partial`** — the call succeeded, but a client-side filter (e.g. `service_type` on `list_services`) matched nothing; the request was fine, the result set is just empty.
- **`deny`** — the call failed. `data` is `null` and `errors` has at least one entry describing why (not found, unauthorized, upstream 5xx, timeout, connection failure, or an unexpected payload shape).

### Benchmark field

`benchmark` is conditional: it's only populated when a tool's output is meant to be compared against a published baseline. In this example, only `get_registry_info` attaches one (`BENCHMARK_REF` in `ga4gh_registry.py`), as an illustration of the shape — it is **not** a real, maintained benchmark yet. `list_services`, `get_service`, and `list_service_types` leave it `null` because they don't make a performance or quality claim about the data they return.

### Caller provenance (harness + model)

`provenance.caller_provenance` identifies what's driving the call:

```json
{
  "harness": { "name": "claude-code", "version": "2.1.0" },
  "model": "claude-sonnet-5"
}
```

- **`harness`** — the MCP client application — is captured automatically from the standard MCP `initialize` handshake (`clientInfo`), via `ctx.session.client_params.client_info` in `_caller_provenance()`. Every MCP client sends this, so it's always populated (falling back to `{"name": "unknown", "version": "unknown"}` only if a client skips it entirely).
- **`model`** — which LLM is behind the harness — has **no standard MCP field**. `clientInfo` identifies the client application, not the model it happens to be running. This example reads it from the open `_meta` map on the individual tool call request, under the key `ga4gh.model` (see [`samples/list_services_request.json`](samples/list_services_request.json) for the wire shape). It's a convention this project defines, not a protocol guarantee — a harness has to opt in to populate it; if it doesn't, `model` is `"unknown"` (see [`samples/get_service_not_found_request.json`](samples/get_service_not_found_request.json), which omits `_meta` on purpose to show the fallback).

The same values are also stamped onto the OTel spans in [`telemetry.db`](#telemetry) (`mcp.client_name`, `mcp.client_version`, `ga4gh.model`), so call history can be filtered by harness or model after the fact, not just inspected per response.

## Telemetry

Every tool call opens a real [OpenTelemetry](https://opentelemetry.io/) span, and every upstream HTTP attempt inside `_fetch` opens a child span (`registry.http.get`) — so a retried call shows up as multiple linked rows, not one. `telemetry.py` exports these to a local SQLite database (`telemetry.db`, next to the server; override with `GA4GH_REGISTRY_TELEMETRY_DB`) via a small custom `SpanExporter`, instead of requiring a collector.

This is separate from the `trace`/`provenance` envelope fields returned to the MCP client: the envelope is what the *caller* sees for one request/response pair, while `telemetry.db` is call history the *server operator* can inspect after the fact — e.g. to see every attempt behind a retry, or every call across tools/sessions.

Schema (`spans` table): `trace_id`, `span_id`, `parent_span_id`, `name`, `start_time_unix_nano`, `end_time_unix_nano`, `duration_ms`, `status_code`, `status_message`, `attributes_json`, `resource_json`.

```bash
sqlite3 telemetry.db "SELECT name, status_code, duration_ms FROM spans ORDER BY start_time_unix_nano;"

# follow one call's full span tree (tool span -> its HTTP attempt(s))
sqlite3 telemetry.db "
  SELECT trace_id, span_id, parent_span_id, name, status_code, attributes_json
  FROM spans WHERE trace_id = '<trace_id from a row above>'
  ORDER BY start_time_unix_nano;
"
```

Because this uses the standard `opentelemetry-sdk` API (`tracer.start_as_current_span`, `Status`/`StatusCode`), swapping the destination for a real backend later is a one-line change in `telemetry.py`'s `init_tracer` — replace `SQLiteSpanExporter` with an OTLP exporter pointed at a collector. Nothing in `ga4gh_registry.py` would need to change.

`mcp[cli]>=2.0.0` ships its own built-in OTel instrumentation for protocol-level RPCs (`initialize`, `tools/list`, `tools/call`, ...). Since `init_tracer` registers the process-wide `TracerProvider`, those spans land in `telemetry.db` too — you'll see them interleaved with `list_services`/`get_service`/etc. That's expected; it's extra context for free, not noise from this example's own code.
>>>>>>> Stashed changes
