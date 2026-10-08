"""MCP server — Analisi email e ordini da email (futuro)."""
import sys

from mcp.server.fastmcp import FastMCP
from _common import _check_api_key

mcp = FastMCP("email")


@mcp.tool()
def stato_email() -> str:
    """Stato del modulo email (non ancora attivo)."""
    return "ℹ️ Modulo email in sviluppo. Funzionalità: analisi ordini da email, estrazione dati, creazione OrdineEmail."


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
