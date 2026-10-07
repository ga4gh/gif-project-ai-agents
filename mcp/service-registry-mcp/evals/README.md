# Evals

A small eval suite for the Service Registry MCP tools, in the spirit of an agent-skill eval suite: one file, `evals.json`, with an `mcp_name` and a list of `evals`. Each eval has:

- **`id`** — a stable integer identifier.
- **`tool`** — which MCP tool the eval exercises.
- **`prompt`** — a realistic user message, the kind of thing someone would actually type.
- **`expected_output`** — a human-readable description of what success looks like.
- **`files`** — input files the case needs, resolved relative to this directory. None of the current cases need any.

There's no agent/LLM in this runner's loop to turn a `prompt` into a tool call, so each eval also pins down `arguments` and `expect` (machine-checkable assertions against the response envelope) — the deterministic ground truth the runner actually executes. `prompt` and `expected_output` are printed alongside each result so a human (or, eventually, an LLM judge, or a real agent harness run through the MCP server) can read the case's intent and sanity-check the actual response against it, not just the mechanical assertions. See the root [README's "Evals" section](../README.md#evals) for how that fuller, agent-in-the-loop setup would work.

This is prep for issue [#11](https://github.com/ga4gh/gif-project-ai-agents/issues/11) (`benchmark` conditionality) — once results from a run of this suite are recorded somewhere durable, `benchmark` in `ga4gh_registry.py` can reference that instead of staying `null`. That wiring isn't done yet; this is just the eval format and runner.

Unlike `tests/`, which mocks `_fetch` and never touches the network, these cases call the real `registry.ga4gh.org` — the point is to validate and time actual behavior, not isolated logic. For that reason this isn't wired into the GitHub Actions workflow: live third-party calls in CI would make the pipeline flaky and rate-limit-prone. Run it manually instead.

## Running

```bash
uv sync
uv run python evals/run_evals.py
```

Exits non-zero if any case fails, so it's usable as a manual gate even without CI wiring.

## File format

```json
{
  "mcp_name": "service-registry-mcp",
  "evals": [
    {
      "id": 2,
      "tool": "get_service",
      "prompt": "Can you give me details about Dockstore's registration in the GA4GH service registry?",
      "expected_output": "Returns Dockstore's full service record - ID org.dockstore.dockstoreapi, its name, organization, and URL - without reporting an error.",
      "files": [],
      "arguments": { "service_id": "org.dockstore.dockstoreapi" },
      "expect": {
        "policy.decision": "allow",
        "data.id": "org.dockstore.dockstoreapi",
        "errors": []
      }
    }
  ]
}
```

`expect` keys are dotted paths into the response envelope (`errors.0.code` indexes into a list). Values are either a literal to match exactly, or a single-key operator object for anything that can't be pinned to an exact value because live registry content changes over time:

| Operator | Meaning |
| --- | --- |
| `{"gte": N}` / `{"lte": N}` / `{"gt": N}` / `{"lt": N}` | Numeric comparison |
| `{"exists": true\|false}` | Path resolves to a non-null value, or doesn't |
| `{"in": [...]}` | Value is one of a set |
| `{"type": "list"\|"dict"\|"str"\|...}` | Python type name of the value |

## Current evals

| ID | Tool | Validates |
| --- | --- | --- |
| 1 | `list_services` | A type filter succeeds and returns at least one result |
| 2 | `get_service` | Resolves a known, stable ID (Dockstore's TRS registration) |
| 3 | `get_service` | Denies an unknown ID with `HTTP_404` |
| 4 | `list_service_types` | Returns at least one type |
| 5 | `get_registry_info` | Resolves the registry's own `service-info` |
