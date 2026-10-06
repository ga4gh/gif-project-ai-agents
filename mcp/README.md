# MCP

This is a schema for GA4GH MCP that has every tool returns the same seven-field response envelope, regardless of which registry endpoint it calls or whether the call succeeded. An agent that learns this contract once can apply it to any other GA4GH MCP server that adopts the same shape (DRS, TRS, WES/TES, Passport), instead of parsing a bespoke format per server.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) — fast Python package manager and runner, used to install dependencies and run every MCP server in this directory

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

