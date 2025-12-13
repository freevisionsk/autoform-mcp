# Autoform MCP Server

Model Context Protocol (MCP) server for the Autoform service from Slovensko.Digital based on the [API documentation](https://ekosystem.slovensko.digital/sluzby/autoform/integracny-manual#api).

**Author:** [@alhafoudh](https://github.com/alhafoudh)

## Features

- Search Slovak corporate bodies (companies, organizations) by name
- Search by registration number (IČO/CIN)
- Filter results to show only active (non-terminated) entities
- Returns detailed company information including addresses and tax IDs

## Quick Start (Hosted Version)

The easiest way to use Autoform MCP is through our hosted version at `https://autoform.fastmcp.app/mcp` using Streamable HTTP mode. No installation required.

### Authentication

Pass your Autoform API token using one of these methods (in priority order):

1. **Authorization header** (recommended): `Authorization: Bearer <token>`
2. **Custom header**: `x-autoform-private-access-token: <token>`

### Privacy Notice

**Your tokens are safe with us.** We take privacy seriously:
- Your API tokens are **never stored** on our servers
- Tokens are only used to authenticate requests to the Autoform API on your behalf
- We do not log, track, or exploit your credentials in any way
- All communication is encrypted via HTTPS

### Claude Code Integration (Hosted)

```bash
claude mcp add autoform --transport http --header "Authorization: Bearer your-token-here" https://autoform.fastmcp.app/mcp
```

### Claude Desktop Integration (Hosted)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "autoform": {
      "type": "streamable-http",
      "url": "https://autoform.fastmcp.app/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

---

## Self-Hosted Installation

### From PyPI (recommended)

```bash
pip install autoform-mcp
```

Or using uvx to run directly without installation:

```bash
uvx autoform-mcp
```

### From source

```bash
# Clone the repository
git clone https://github.com/alhafoudh/autoform-mcp.git
cd autoform-mcp

# Install dependencies
uv sync
```

## Configuration

Set the `AUTOFORM_PRIVATE_ACCESS_TOKEN` environment variable with your API token from [Slovensko.Digital](https://ekosystem.slovensko.digital/).

```bash
export AUTOFORM_PRIVATE_ACCESS_TOKEN="your-token-here"
```

## Usage

### Run the MCP server (STDIO transport)

```bash
# If installed from PyPI
autoform-mcp

# Or using uvx
uvx autoform-mcp

# Or from source
uv run python autoform_mcp.py
```

### Run with FastMCP CLI

```bash
uv run fastmcp run autoform_mcp.py
```

### Inspect available tools

```bash
uv run fastmcp inspect autoform_mcp.py
```

### Development mode with MCP Inspector

```bash
uv run fastmcp dev autoform_mcp.py
```

## Available Tools

### query_corporate_bodies

Search Slovak corporate bodies using a query expression.

**Parameters:**
- `query` (string, required): Query expression in format `field:value`
- `limit` (integer, optional): Maximum number of results (1-20, default 5)
- `active_only` (boolean, optional): If true, return only active entities

**Query format:**
- `name:<value>` - Search by company name prefix
- `cin:<value>` - Search by IČO (registration number) prefix

**Examples:**
```
query_corporate_bodies(query="name:Slovenská pošta")  # Find companies starting with "Slovenská pošta"
query_corporate_bodies(query="cin:36631124")          # Find company with IČO 36631124
query_corporate_bodies(query="cin:366", limit=10)     # Find companies with IČO starting with "366"
query_corporate_bodies(query="name:Test", active_only=True)  # Only active companies
```

## Available Resources

### autoform://api-info

Returns information about the Autoform API and this MCP server.

## Claude Code Integration (Self-Hosted)

### Using uvx (recommended)

Run the server directly from PyPI without installation:

```bash
claude mcp add autoform -e AUTOFORM_PRIVATE_ACCESS_TOKEN=your-token-here -- uvx autoform-mcp
```

### Using local installation

If you've cloned the repository:

```bash
claude mcp add autoform -e AUTOFORM_PRIVATE_ACCESS_TOKEN=your-token-here -- uv run python /path/to/autoform_mcp.py
```

## Claude Desktop Integration (Self-Hosted)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

### Using uvx (recommended)

```json
{
  "mcpServers": {
    "autoform": {
      "command": "uvx",
      "args": ["autoform-mcp"],
      "env": {
        "AUTOFORM_PRIVATE_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

### Using local installation

```json
{
  "mcpServers": {
    "autoform": {
      "command": "uv",
      "args": ["run", "python", "/path/to/autoform-mcp.py"],
      "env": {
        "AUTOFORM_PRIVATE_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Development

### Install dev dependencies

```bash
uv sync --all-extras
```

### Run tests

```bash
uv run pytest -v
```

## License

MIT
