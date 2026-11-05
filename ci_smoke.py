"""Startet den Server wie ein MCP-Client und prüft, dass alle Tools gemeldet werden."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED = {"remarkable_live_screen"}


async def main() -> None:
    server = StdioServerParameters(
        command="uv", args=["run", "-q", "--script", str(Path(__file__).parent / "server.py")]
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
    missing = EXPECTED - names
    print("Tools:", sorted(names))
    sys.exit(f"fehlt: {missing}" if missing else 0)


asyncio.run(main())
