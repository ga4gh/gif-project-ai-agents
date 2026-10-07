# 0002: Eval case format — agent-skill shape with a deterministic fallback checker

**Status:** proposed
**Date:** 2026-10-07
**Decided by:** Venkat Malladi

## Context

Issue [#11](https://github.com/ga4gh/gif-project-ai-agents/issues/11) needs `benchmark` to eventually reference real eval results, not stay a placeholder. The eval cases for the Service Registry MCP example should read like realistic user interactions — matching how agent-skill eval specs structure test cases (a `prompt`, a human-readable `expected_output`, optional input files) — rather than purely mechanical "call this tool with these args" cases.

But there's no agent/LLM harness wired into this repo today. `evals/run_evals.py` calls the named tool function directly; nothing reads a natural-language `prompt` and decides what to call. Building that (an agent loop against the MCP server via `anthropic` + `mcp.client.session.ClientSession`, or Claude Code itself in headless mode, plus a human- or LLM-judge grading step) is real, separate work — a new dependency, an API key, real inference cost per run, and non-deterministic judging.

## Options considered

- **Pure agent-skill-style cases** (`id`/`tool`/`prompt`/`expected_output`/`files` only), graded by running a real agent against the MCP server. Most faithful to the "agent eval" framing in #11, but not buildable yet without first deciding how to automate grading — and un-runnable at all until that harness exists.
- **Pure mechanical cases** (tool + arguments + dotted-path `expect` assertions only, what this repo originally had). Fully deterministic, zero cost, fast, no new dependencies — but doesn't model the actual thing being benchmarked (an agent using this MCP server from a natural-language prompt), and doesn't match #11's eval framing.
- **Hybrid (chosen)**: keep `prompt`/`expected_output`/`files`/`id`/`tool` as the agent-skill-shaped eval definition, but also pin `arguments`/`expect` per case so the current runner can execute deterministically today, with no agent and no API key. `prompt`/`expected_output` are printed alongside each result for human review even though they're not consumed by the mechanical check.

## Decision

Use the hybrid shape, in a single `evals/evals.json` file grouped under `mcp_name`, with each eval carrying a stable integer `id` and naming the `tool` it exercises. `run_evals.py` executes only the deterministic `arguments`/`expect` path. `prompt` and `expected_output` are documentation printed alongside each result, not graded automatically yet. Building an actual agent-in-the-loop runner is deferred — sketched in `mcp/service-registry-mcp/README.md`'s "Evals" section, not implemented — pending a separate decision to add the `anthropic` dependency, an API key, and a grading strategy.

## Consequences

- Eval cases double as both agent-skill-style eval definitions (readable prompt framing) and deterministic regression checks (`arguments`/`expect`) — until an agent harness exists, `prompt`/`expected_output` are illustrative, not verified against real agent behavior.
- If/when an agent-in-the-loop runner is built, it can reuse the same `evals.json` (reading `prompt`/`expected_output`/`files`, ignoring `arguments`/`expect`), so this isn't throwaway work — it's forward-compatible with the fuller setup, not a format that'll need migrating later.
- Evals stay out of CI by design (live calls to a third-party registry would make the pipeline flaky); this decision doesn't change that, and the future agent-in-the-loop runner would inherit the same constraint plus an API-key/cost one.
- Not an `api-gap`: this is purely about how this project runs its own evals, not something that depends on or constrains the GA4GH Service Registry spec itself.
