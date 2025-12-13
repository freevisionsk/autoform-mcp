"""
MCP server for Autoform API from Slovensko.Digital.

Provides tools for searching Slovak corporate bodies (companies, organizations)
by name or registration number (IČO/CIN).
"""

import os
import re

import httpx
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from pydantic import BaseModel, Field

API_BASE_URL = "https://autoform.ekosystem.slovensko.digital/api"


class CorporateBody(BaseModel):
    """Corporate body record from Autoform API."""

    model_config = {"extra": "ignore"}

    cin: str | int | None = Field(None, description="Company identification number (IČO)")
    tin: str | int | None = Field(None, description="Tax identification number (DIČ)")
    vatin: str | None = Field(None, description="VAT identification number (IČ DPH)")
    name: str | None = Field(None, description="Official name of the corporate body")
    formatted_address: str | None = Field(
        None, description="Full formatted address as single string"
    )
    street: str | None = Field(None, description="Street name")
    reg_number: str | int | None = Field(
        None, description="Building registration number (súpisné číslo)"
    )
    building_number: str | int | None = Field(
        None, description="Building number (orientačné číslo)"
    )
    postal_code: str | None = Field(None, description="Postal code (PSČ)")
    municipality: str | None = Field(None, description="Municipality/city name")
    country: str | None = Field(None, description="Country name")
    established_on: str | None = Field(
        None, description="Date when the entity was established"
    )
    terminated_on: str | None = Field(
        None, description="Date when the entity was terminated (if applicable)"
    )
    datahub_corporate_body_url: str | None = Field(
        None, description="URL to DataHub API for additional registry information"
    )


class SearchResult(BaseModel):
    """Result of corporate body search."""

    results: list[CorporateBody] = Field(
        default_factory=list, description="List of matching corporate bodies"
    )
    count: int = Field(0, description="Number of results returned")


def get_access_token() -> str:
    """Get the private access token from environment."""
    token = os.environ.get("AUTOFORM_PRIVATE_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "AUTOFORM_PRIVATE_ACCESS_TOKEN environment variable is not set. "
            "Get your token from https://ekosystem.slovensko.digital/"
        )
    return token


def sanitize_url(url: str) -> str:
    """Remove sensitive tokens from URL for safe error messages."""
    return re.sub(r"private_access_token=[^&]+", "private_access_token=***", str(url))


mcp = FastMCP(
    "Autoform MCP Server",
    instructions="""
    This MCP server provides access to the Autoform API from Slovensko.Digital.

    Use this server to search for Slovak corporate bodies (companies, organizations)
    using the query_corporate_bodies tool.

    Query format examples:
    - name:Slovenská pošta  (search by company name prefix)
    - cin:36631124          (search by IČO/registration number prefix)

    The tool supports filtering to show only active (non-terminated) entities.
    """,
)


@mcp.resource("autoform://api-info")
def get_api_info() -> dict:
    """Information about the Autoform API and this MCP server."""
    return {
        "name": "Autoform API",
        "provider": "Slovensko.Digital",
        "description": "API for searching Slovak corporate bodies (companies, organizations)",
        "documentation": "https://ekosystem.slovensko.digital/sluzby/autoform/integracny-manual#api",
        "base_url": API_BASE_URL,
        "query_format": {
            "description": "Query string format: 'field:value' where field is 'name' or 'cin'",
            "examples": [
                {"query": "name:Slovenská pošta", "description": "Search by company name prefix"},
                {"query": "cin:36631124", "description": "Search by IČO (registration number) prefix"},
            ],
        },
        "authentication": "Requires AUTOFORM_PRIVATE_ACCESS_TOKEN environment variable",
    }


@mcp.tool(
    tags={"search", "corporate"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def query_corporate_bodies(
    query: str = Field(
        description="""Query expression in format 'field:value'.

Supported query formats:
- name:<value> - Search by company name prefix (e.g., 'name:Slovenská pošta')
- cin:<value>  - Search by IČO/registration number prefix (e.g., 'cin:36631124')

The search matches from the beginning of the field value."""
    ),
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results (1-20, default 5)",
    ),
    active_only: bool = Field(
        default=False,
        description="If true, return only active (non-terminated) entities",
    ),
    ctx: Context = CurrentContext(),
) -> SearchResult:
    """
    Search Slovak corporate bodies (companies, organizations).

    Query format examples:
    - query="name:Slovenská pošta" finds companies with names starting with "Slovenská pošta"
    - query="cin:36631124" finds the company with IČO 36631124
    - query="cin:366" finds all companies with IČO starting with "366"

    Returns matching records with identification numbers (IČO, DIČ, IČ DPH),
    addresses, establishment dates, and links to additional registry data.
    """
    await ctx.info(f"Querying corporate bodies: {query}")

    token = get_access_token()

    params = {
        "q": query,
        "private_access_token": token,
        "limit": limit,
    }
    if active_only:
        params["filter"] = "active"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/corporate_bodies/search",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            sanitized_url = sanitize_url(e.request.url)
            raise RuntimeError(
                f"API request failed: HTTP {e.response.status_code} for {sanitized_url}"
            ) from None
        data = response.json()

    results = [CorporateBody(**item) for item in data]
    await ctx.info(f"Found {len(results)} corporate bodies")

    return SearchResult(results=results, count=len(results))


@mcp.prompt
def search_company_prompt(query: str) -> str:
    """Prompt template for searching and analyzing a Slovak company."""
    return f"""Please search for the Slovak company "{query}" using the query_corporate_bodies tool.

Query format:
- If "{query}" looks like a number (IČO), use: query="cin:{query}"
- Otherwise, use: query="name:{query}"

After finding results, provide a summary including:
- Company name and registration number (IČO)
- Address
- Tax identification numbers (DIČ, IČ DPH) if available
- Status (active or terminated based on terminated_on field)
"""


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
