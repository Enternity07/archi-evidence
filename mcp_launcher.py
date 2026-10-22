"""Absolute-path entry point for MCP hosts; stdout is reserved for protocol."""
from archi_agent.mcp_server import create_server

if __name__ == "__main__":
    create_server().run(transport="stdio")
