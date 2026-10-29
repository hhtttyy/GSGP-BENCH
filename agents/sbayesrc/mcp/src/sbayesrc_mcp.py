"""SBayesRC MCP server entry point.

Run from this directory:
    python sbayesrc_mcp.py
or register with your MCP client via the tools in USAGE.md.
"""
from fastmcp import FastMCP

from tools.sbayesrc import mcp as sbayesrc

app = FastMCP("SBayesRC")
app.mount(sbayesrc, namespace="sbayesrc")

if __name__ == "__main__":
    app.run()
