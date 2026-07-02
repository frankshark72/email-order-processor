"""MCP server — Tracking chiamate via Tasker (Android)."""
import sys
from datetime import date

from mcp.server.fastmcp import FastMCP
from _common import _post, _patch, _search, _check_api_key

mcp = FastMCP("chiamate")


@mcp.tool()
def log_chiamata_tasker(numero: str, durata_secondi: int = 0,
                        direzione: str = "Outbound", data: str = "") -> str:
    """Registra una chiamata ricevuta da Tasker (Android).
    numero: numero chiamante/chiamato.
    direzione: Outbound (uscente) | Inbound (entrante).
    data: YYYY-MM-DD, default oggi.
    """
    d = data or date.today().isoformat()
    durata_min = max(1, durata_secondi // 60)

    # Cerca account con quel numero
    accounts = _search("Account", [{"type": "equals", "attribute": "phoneNumber", "value": numero}],
                       select="id,name", max_size=1)

    payload = {
        "name": f"Chiamata {direzione} {numero}",
        "dateStart": f"{d} 09:00:00",
        "duration": durata_secondi or 60,
        "status": "Held",
        "direction": direzione,
        "description": f"Registrata da Tasker. Numero: {numero}",
    }
    if accounts:
        payload["parentType"] = "Account"
        payload["parentId"] = accounts[0]["id"]
        _patch("Account", accounts[0]["id"], {"ultimaChiamata": d})
        nome = accounts[0]["name"]
    else:
        nome = numero

    _post("Call", payload)
    return f"✅ Chiamata {direzione} con {nome} ({durata_min} min) registrata."


@mcp.tool()
def stato_chiamate() -> str:
    """Info sul modulo chiamate Tasker."""
    return ("📞 Modulo chiamate attivo.\n"
            "Configura Tasker su Android per inviare webhook a questo endpoint quando termina una chiamata.\n"
            "Il sistema abbina automaticamente il numero al cliente in EspoCRM.")


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
