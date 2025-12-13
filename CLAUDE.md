# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server for the Autoform service from Slovensko.Digital. The API documentation is at https://ekosystem.slovensko.digital/sluzby/autoform/integracny-manual#api.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the MCP server (STDIO transport - default)
uv run python autoform_mcp.py

# Run with FastMCP CLI
uv run fastmcp run autoform_mcp.py

# Run with HTTP transport
uv run fastmcp run autoform_mcp.py --transport http --port 8000

# Inspect server (view tools, resources, prompts)
uv run fastmcp inspect autoform_mcp.py

# Development mode with MCP Inspector
uv run fastmcp dev autoform_mcp.py

# Run tests
uv run pytest
uv run pytest -v  # verbose
uv run pytest --cov=.  # with coverage
```

## Architecture

- **Framework:** FastMCP v2.14+ for building MCP servers
- **Python:** 3.12 (managed via mise)
- **Package manager:** uv

The main server implementation is in `autoform_mcp.py`.

## FastMCP Patterns

### Tools
Tools are functions that LLMs can call. Define with `@mcp.tool` decorator:

```python
@mcp.tool
def my_tool(param: str) -> str:
    """Tool description shown to LLM."""
    return result

# With tags and annotations
@mcp.tool(tags={"public"}, annotations={"readOnlyHint": True})
async def async_tool(param: str) -> dict:
    return {"result": param}
```

### Resources
Resources expose data to LLMs via URIs:

```python
@mcp.resource("resource://config")
def get_config() -> dict:
    return {"version": "1.0"}

# Resource templates with parameters
@mcp.resource("data://{item_id}/details")
def get_item(item_id: str) -> dict:
    return {"id": item_id}
```

### Prompts
Reusable message templates:

```python
@mcp.prompt
def analyze_prompt(data: str) -> str:
    return f"Please analyze: {data}"
```

### Context and Dependencies
Access request context and inject dependencies:

```python
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext, Depends

@mcp.tool
async def tool_with_context(param: str, ctx: Context = CurrentContext()) -> str:
    await ctx.info(f"Processing {param}")
    return result

# Custom dependencies
def get_api_client() -> Client:
    return Client(base_url="https://api.example.com")

@mcp.tool
async def tool_with_dep(query: str, client: Client = Depends(get_api_client)) -> dict:
    return await client.fetch(query)
```

## Testing

Use in-memory testing by passing server directly to Client:

```python
from fastmcp import FastMCP, Client

server = FastMCP("TestServer")

@server.tool
def add(a: int, b: int) -> int:
    return a + b

async def test_add():
    async with Client(server) as client:
        result = await client.call_tool("add", {"a": 1, "b": 2})
        assert result.data == 3
```

## Transport Options

- **STDIO** (default): `mcp.run()` - for CLI tools and local development
- **HTTP**: `mcp.run(transport="http", port=8000)` - for web services
- **SSE**: `mcp.run(transport="sse", port=8000)` - legacy, use HTTP instead
