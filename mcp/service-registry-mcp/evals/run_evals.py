"""Eval runner for the Service Registry MCP example.

Reads evals/evals.json: a `mcp_name` and a list of `evals`, each naming the
`tool` it exercises and carrying an integer `id`. In the spirit of an
agent-skill eval, each case has a `prompt` (a realistic user message), an
`expected_output` (a human-readable description of what success looks
like), and `files` (input files it needs, resolved relative to evals/ —
none of the current cases need any). Since there's no agent/LLM in this
loop to turn a prompt into a tool call, each case also pins down
`arguments` and `expect` (machine-checkable assertions on the response
envelope) — the deterministic ground truth this runner actually executes.
`prompt` and `expected_output` are printed alongside each result for a
human reviewing the run to judge against, not consumed by the runner
itself.

Calls the named tool directly against the real GA4GH registry — no
mocking, unlike tests/ which mocks `_fetch` — since the point is to
validate and time actual behavior.

This is prep for issue #11 (`benchmark` conditionality): `benchmark` would
eventually reference a run of this suite once results are recorded
somewhere durable. For now it's a manual command, not wired into CI or
`ga4gh_registry.py`, since it makes live network calls against a
third-party service and shouldn't be a source of CI flakiness.

Usage:
    uv run python evals/run_evals.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import ga4gh_registry as reg  # noqa: E402

EVALS_DIR = Path(__file__).parent
EVALS_FILE = EVALS_DIR / "evals.json"
_OPERATORS = {"gte", "lte", "gt", "lt", "exists", "in", "type"}


def _get_path(data: Any, path: str) -> tuple[Any, bool]:
    """Walk a dotted path (e.g. `data.count`, `errors.0.code`) through dicts and lists."""
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                return None, False
            current = current[int(part)]
        elif isinstance(current, dict):
            if part not in current:
                return None, False
            current = current[part]
        else:
            return None, False
    return current, True


def _check(actual: Any, expected: Any) -> bool:
    """Compare `actual` to `expected`, which is either a literal or a single-key operator dict."""
    if isinstance(expected, dict) and len(expected) == 1 and next(iter(expected)) in _OPERATORS:
        op, val = next(iter(expected.items()))
        if op == "gte":
            return actual is not None and actual >= val
        if op == "lte":
            return actual is not None and actual <= val
        if op == "gt":
            return actual is not None and actual > val
        if op == "lt":
            return actual is not None and actual < val
        if op == "exists":
            return (actual is not None) == val
        if op == "in":
            return actual in val
        if op == "type":
            return type(actual).__name__ == val
    return actual == expected


def _load_evals() -> list[dict[str, Any]]:
    suite = json.loads(EVALS_FILE.read_text())
    return suite["evals"]


def _check_files(case: dict[str, Any]) -> list[str]:
    """Verify any declared `files` exist, resolved relative to evals/."""
    missing = []
    for rel_path in case.get("files") or []:
        if not (EVALS_DIR / rel_path).exists():
            missing.append(f"files: missing {rel_path!r}")
    return missing


async def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    failures = _check_files(case)

    tool_name = case["tool"]
    arguments = case.get("arguments", {})
    tool_fn = getattr(reg, tool_name)

    start = time.perf_counter()
    envelope = json.loads(await tool_fn(**arguments))
    wall_ms = round((time.perf_counter() - start) * 1000)

    for path, expected in case["expect"].items():
        actual, found = _get_path(envelope, path)
        if not found or not _check(actual, expected):
            failures.append(f"{path}: expected {expected!r}, got {actual!r}")

    return {
        "id": case["id"],
        "tool": tool_name,
        "prompt": case.get("prompt"),
        "expected_output": case.get("expected_output"),
        "passed": not failures,
        "failures": failures,
        "wall_ms": wall_ms,
        "reported_ms": envelope.get("trace", {}).get("timing", {}).get("duration_ms"),
    }


async def main() -> None:
    cases = _load_evals()
    results = [await _run_case(case) for case in cases]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"[{status}] #{result['id']} {result['tool']} "
            f"({result['wall_ms']}ms wall / {result['reported_ms']}ms reported)"
        )
        if result["prompt"]:
            print(f"       Prompt:   {result['prompt']}")
        if result["expected_output"]:
            print(f"       Expected: {result['expected_output']}")
        for failure in result["failures"]:
            print(f"       FAILED:   {failure}")

    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
