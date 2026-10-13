# Service Registry MCP (example)

An MCP server wrapping the [GA4GH Service Registry API](https://github.com/ga4gh/ga4gh-service-registry/blob/develop/service-registry.yaml), built for the `ws:mcp-tools` workstream (see issue [#1](https://github.com/ga4gh/gif-project-ai-agents/issues/1) and its sub-issues).

## Scope

This is a deliberately minimal first pass, covering exactly:

- [#3](https://github.com/ga4gh/gif-project-ai-agents/issues/3) — a Service Registry MCP example lives under `mcp/`.
- [#4](https://github.com/ga4gh/gif-project-ai-agents/issues/4) — a sample request and response payload (see [`samples/`](samples/)).
- [#5](https://github.com/ga4gh/gif-project-ai-agents/issues/5) — every tool response includes all seven top-level envelope fields below.

Each field is intentionally simple here — a single generic error type, one `allow`/`deny` decision, no retries, no caller/telemetry provenance. Elaborating any one of them further is tracked in separate follow-up issues: typed error taxonomy ([#6](https://github.com/ga4gh/gif-project-ai-agents/issues/6)), richer policy reasoning ([#7](https://github.com/ga4gh/gif-project-ai-agents/issues/7)), trace/timing/retries ([#8](https://github.com/ga4gh/gif-project-ai-agents/issues/8)), source detail ([#9](https://github.com/ga4gh/gif-project-ai-agents/issues/9)), provenance elements ([#10](https://github.com/ga4gh/gif-project-ai-agents/issues/10)), and benchmark conditionality ([#11](https://github.com/ga4gh/gif-project-ai-agents/issues/11)).

## The response envelope

Every tool returns a single JSON string (so it survives as plain MCP tool output) with these seven top-level fields:

| Field | Purpose |
| --- | --- |
| `data` | The normalized payload — the thing the caller actually asked for. `null` on failure. |
| `source` | Which upstream endpoint answered, and the spec version it implements. |
| `trace` | `request_id` and start/end timestamps + duration. |
| `policy` | `allow` or `deny`, plus a machine-readable `reason.code` and a human-readable `reason.message`. |
| `errors` | Array of typed error objects: `type`, `code`, `message`, `retryable`. Empty on success. |
| `benchmark` | Reserved for a published benchmark reference; always `null` for now (see [#11](https://github.com/ga4gh/gif-project-ai-agents/issues/11)). |
| `provenance` | `query_provenance` (what was asked), `response_provenance` (where/when the answer came from), and a response `timestamp`. |

## Tools

All tools accept an optional `registry_url` (defaults to `https://registry.ga4gh.org/v1`).

| Tool | Registry endpoint | Description |
| --- | --- | --- |
| `list_services` | `GET /services` | List services, optionally filtered by `service_type` (matches `type.artifact`, e.g. `trs`, `wes`, `tes`, `drs`). |
| `get_service` | `GET /services/{serviceId}` | Get full details for one service by ID. |
| `list_service_types` | `GET /services/types` | List all distinct service types the registry exposes. |
| `get_registry_info` | `GET /service-info` | Get `service-info` metadata about the registry itself. |

## Sample request / response

The full payload pair lives under [`samples/`](samples/):

- [`list_services_request.json`](samples/list_services_request.json) — the MCP tool name and arguments.
- [`list_services_response.json`](samples/list_services_response.json) — the resulting envelope (`policy.decision: "allow"`).

Response shape, trimmed here to the structure (see the sample file for the full envelope):

```json
{
  "data": { "services": ["..."], "count": 1 },
  "source": { "endpoint": "https://registry.ga4gh.org/v1/services", "version": "1.0.0" },
  "trace": { "request_id": "req-...", "timing": { "start": "...", "end": "...", "duration_ms": 420 } },
  "policy": { "decision": "allow", "reason": { "code": "POLICY_OK", "message": "Request allowed." } },
  "errors": [],
  "benchmark": null,
  "provenance": {
    "query_provenance": { "...": "..." },
    "response_provenance": { "...": "..." },
    "timestamp": "..."
  }
}
```

## Running it

```bash
uv venv
source .venv/bin/activate
uv sync
```

```bash
# run directly
uv run python ga4gh_registry.py

# or inspect it interactively
npx @modelcontextprotocol/inspector uv run python ga4gh_registry.py
```

Example `claude_desktop_config.json` entry:

```json
"ga4gh-service-registry": {
  "command": "uv",
  "args": ["--directory", "mcp/service-registry-mcp", "run", "python", "ga4gh_registry.py"]
}
```

## Testing

Unit tests mock `_fetch` directly — no network calls, no live registry dependency. 23 tests total.

```bash
uv sync --extra test
uv run pytest
```

| File | Covers |
| --- | --- |
| `tests/test_list_services.py` | `list_services`: allow (unfiltered, filtered, no-match), deny, `registry_url` override, envelope shape |
| `tests/test_get_service.py` | `get_service`: allow, deny (404, connection error), envelope shape |
| `tests/test_list_service_types.py` | `list_service_types`: allow (populated, empty), deny, non-list payload handling, `registry_url` override, envelope shape |
| `tests/test_get_registry_info.py` | `get_registry_info`: allow, deny (404, 500), `benchmark` always `null`, `registry_url` override, envelope shape |
| `tests/test_samples.py` | Guards #4/#5 directly against the committed `samples/` files, not just inline mocks |

## Credits

Adapted from the `ga4gh-registry` server in [vsmalladi/ga4gh-mcp](https://github.com/vsmalladi/ga4gh-mcp/blob/main/servers/ga4gh_registry.py), updated to call the endpoints actually defined in [`service-registry.yaml`](https://github.com/ga4gh/ga4gh-service-registry/blob/develop/service-registry.yaml) (including the dedicated `/services/types` endpoint and the `service-info` schema's real field names) and to return the standardized envelope described above instead of a formatted text summary.
