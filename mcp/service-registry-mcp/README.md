# Service Registry MCP (example)

An MCP server wrapping the [GA4GH Service Registry API](https://github.com/ga4gh/ga4gh-service-registry/blob/develop/service-registry.yaml).

## The response envelope

Every tool returns a single JSON string (so it survives as plain MCP tool output) with these seven top-level fields:

| Field | Purpose |
| --- | --- |
| `data` | The normalized payload — the thing the caller actually asked for. `null` on failure. |
| `source` | Which upstream endpoint answered, and the spec version it implements. |
| `trace` | `request_id` and start/end timestamps + duration. |
| `policy` | `allow` or `deny`, plus a machine-readable `reason.code` and a human-readable `reason.message`. |
| `errors` | Array of typed error objects: `type`, `code`, `message`, `retryable`. Empty on success. |
| `benchmark` | Reserved for a published benchmark reference; always `null` for now and [`evals/`](evals/)). |
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

## Evals

[`evals/`](evals/evals.json) holds a small set of eval cases, in the spirit of an agent-skill eval suite: each one names the `tool` it exercises and has a `prompt`, `expected_output`, and optional `files`. `evals/run_evals.py` calls the real registry directly (unlike `tests/`, which mocks `_fetch`) using each case's `arguments`/`expect` as deterministic ground truth, and prints `prompt`/`expected_output` alongside the result for a human to sanity-check. This is prep for issue [#11](https://github.com/ga4gh/gif-project-ai-agents/issues/11). Run manually with:

```bash
uv run python evals/run_evals.py
```

**Running with an actual agent in the loop.** The runner above never has an LLM read `prompt` and decide what to call — it just executes the pinned `arguments` directly. To really exercise prompt → tool-call → answer, point an MCP-aware agent harness at this server (it already speaks standard stdio, the same way `tests/`/manual smoke tests connect to it) — Claude Code itself (register the server in `.mcp.json`, run `claude -p "<prompt>"` per eval and capture stdout), the Claude Agent SDK, or a small hand-rolled loop using the `anthropic` SDK plus `mcp.client.session.ClientSession` (fetch tool schemas from the server, convert to Claude's tool-use format, loop until Claude returns final text). Grading `expected_output` against that free-text response is then either a human reading both, or a second LLM call acting as judge. Not implemented here yet — it needs a new dependency, an API key, and non-deterministic judging, a meaningfully bigger lift than the current mocked/deterministic runner.

