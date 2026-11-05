# 0001: Use OpenTelemetry spans to back `provenance.query_provenance` / `response_provenance`

**Status:** proposed
**Date:** 2026-10-06
**Decided by:** Venkat Malladi

## Context

Issue [#10](https://github.com/ga4gh/gif-project-ai-agents/issues/10) requires the response envelope's `provenance` field to include query and response provenance elements — enough to reconstruct "what was asked" and "where/when the answer came from" after the fact, not just descriptive strings baked into one response.

A tool call already has a natural span shape: one span per tool invocation, with a child span per upstream HTTP attempt. OpenTelemetry gives us a standard way to capture that shape instead of inventing a bespoke provenance data model.

This was already prototyped end-to-end on the Service Registry MCP example (spans per tool call + child HTTP spans + a custom SQLite `SpanExporter`), then pulled out when that example was descoped down to issues #3/#4/#5 only. This decision proposes reviving it, scoped specifically to what #10 needs.

## Options considered

- **Bespoke provenance fields, no tracing library**: hand-roll `query_provenance`/`response_provenance` as plain dicts populated inline (what the minimal #3/#4/#5 example currently does). Simple, zero dependencies, but every call site has to remember to populate them correctly, there's no correlation ID standard, and retries/sub-calls aren't represented — only the last attempt is visible.
- **Full OpenTelemetry SDK, SQLite exporter (chosen)**: wrap each tool call in a real OTel span via `opentelemetry-sdk`, using `trace_id`/`span_id` as the correlation handle embedded in `query_provenance`, and deriving `response_provenance` (`source_endpoint`, `retrieved_at`, status, duration) from the same span data. Child spans per HTTP attempt make retries visible as a linked tree. Export to a local SQLite file via a small custom `SpanExporter` so there's a queryable call history without requiring a collector.
- **Full OpenTelemetry SDK, OTLP exporter to a real collector**: same instrumentation, but requires operators to stand up and point at a collector (Jaeger, Tempo, a vendor backend). More appropriate for a production deployment than for an example/dev repo; adds an external dependency this project doesn't otherwise need yet.

## Decision

Use `opentelemetry-sdk`: one span per tool call (`list_services`, `get_service`, etc.) with GA4GH-specific query parameters as span attributes, and one child span per upstream HTTP attempt (`registry.http.get`). `query_provenance` embeds the span's `trace_id`/`span_id` alongside the existing explicit query fields. `response_provenance` is derived from the same span's attributes/timing rather than recomputed separately. Export spans to a local SQLite database via a custom `SpanExporter`, not an OTLP collector, since this is an example/dev-facing implementation — swapping the exporter for OTLP later is a one-line change in the exporter configuration, not a rewrite of the instrumentation.

## Consequences

- `trace_id`/`span_id` becomes the shared correlation handle between the envelope's `provenance` (issue #10) and `trace.request_id` (issue #8) — both describe one call, so we use one identifier scheme instead of two.
- Adds `opentelemetry-sdk` as a runtime dependency to any MCP example that implements this (previously removed from the minimal #3/#4/#5 pass specifically to avoid this).
- Retried calls (once #8 implements retry logic) become visible as multiple linked child spans sharing one `trace_id`, rather than only the final attempt being recorded.
- Call history becomes queryable after the fact (`sqlite3 telemetry.db ...`) by any MCP example that adopts this, independent of any single response's `provenance` field — useful for debugging and for the project's eventual API-gap/latency reporting goals.
- Not an `api-gap`: this is purely how *our* MCP servers record provenance; it doesn't depend on or constrain the GA4GH Service Registry spec itself.
