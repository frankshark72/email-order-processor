"""MCP server — Integrazione WhatsApp (futuro)."""
import sys

from mcp.server.fastmcp import FastMCP
from _common import _check_api_key

mcp = FastMCP("whatsapp")


@mcp.tool()
def stato_whatsapp() -> str:
    """Stato del modulo WhatsApp (non ancora attivo)."""
    return "ℹ️ Modulo WhatsApp in sviluppo. Funzionalità: ricezione messaggi, log conversazioni, creazione task da chat."


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
