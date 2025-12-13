#!/usr/bin/env python3
"""CLI client for testing the Autoform MCP server."""

import argparse
import asyncio
import json

from fastmcp import Client

from autoform_mcp import mcp


async def main():
    parser = argparse.ArgumentParser(
        description="Test client for Autoform MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "name:Slovenská pošta"
  %(prog)s "cin:36631124"
  %(prog)s "name:Test" --limit 10
  %(prog)s "name:Test" --active-only
  %(prog)s "cin:366" --limit 20 --active-only
        """,
    )
    parser.add_argument(
        "query",
        help="Query expression (e.g., 'name:Company' or 'cin:12345678')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of results (1-20, default: 5)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Return only active (non-terminated) entities",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    async with Client(mcp) as client:
        result = await client.call_tool(
            "query_corporate_bodies",
            {
                "query": args.query,
                "limit": args.limit,
                "active_only": args.active_only,
            },
        )

        # Access result data (FastMCP returns a Root object with attributes)
        data = result.data
        count = data.count
        results = data.results

        if args.output_json:
            # Convert to dict for JSON output
            output = {
                "count": count,
                "results": [
                    {k: getattr(r, k) for k in dir(r) if not k.startswith("_")}
                    for r in results
                ],
            }
            print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"Found {count} result(s):\n")

            for i, body in enumerate(results, 1):
                print(f"[{i}] {getattr(body, 'name', 'N/A')}")
                print(f"    IČO: {getattr(body, 'cin', 'N/A')}")
                print(f"    DIČ: {getattr(body, 'tin', 'N/A')}")
                if getattr(body, "vatin", None):
                    print(f"    IČ DPH: {body.vatin}")
                print(f"    Address: {getattr(body, 'formatted_address', 'N/A')}")
                if getattr(body, "established_on", None):
                    print(f"    Established: {body.established_on}")
                if getattr(body, "terminated_on", None):
                    print(f"    Terminated: {body.terminated_on}")
                if getattr(body, "datahub_corporate_body_url", None):
                    print(f"    DataHub: {body.datahub_corporate_body_url}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
