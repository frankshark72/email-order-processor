"""MCP server — Ordini email e briefing giornaliero."""
import sys
from datetime import date, datetime

from mcp.server.fastmcp import FastMCP
from _common import _search, _check_api_key, API_BASE, _headers

import requests

mcp = FastMCP("ordini")


@mcp.tool()
def ordini_in_attesa() -> str:
    """Elenca gli ordini email con stato 'in_attesa'."""
    r = requests.get(f"{API_BASE}/OrdineEmail", headers=_headers(),
                     params={"maxSize": 1}, timeout=10)
    if r.status_code == 404:
        return "ℹ️ Entità OrdineEmail non ancora configurata."
    results = _search("OrdineEmail",
                      [{"type": "equals", "attribute": "stato", "value": "in_attesa"}],
                      select="id,emailDa,emailOggetto,emailData,noteAgente", max_size=20)
    if not results:
        return "✅ Nessun ordine in attesa."
    today = date.today()
    lines = [f"💰 Ordini in attesa ({len(results)}):"]
    for o in results:
        data_email = o.get("emailData","")
        try:
            giorni = (today - datetime.strptime(data_email[:10], "%Y-%m-%d").date()).days
            data_str = f"{giorni}gg fa"
        except Exception:
            data_str = data_email[:10] or "?"
        lines.append(f"• {o.get('emailDa','?')} | {o.get('emailOggetto','?')} | {data_str}")
    return "\n".join(lines)


@mcp.tool()
def briefing() -> str:
    """Briefing mattutino: task di oggi, ordini in attesa, top 5 clienti urgenti."""
    today = date.today()
    giorni_it = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
    mesi_it = ["","gennaio","febbraio","marzo","aprile","maggio","giugno",
               "luglio","agosto","settembre","ottobre","novembre","dicembre"]
    data_it = f"{giorni_it[today.weekday()]} {today.day} {mesi_it[today.month]} {today.year}"
    sezioni = [f"☀️ Briefing {data_it}\n"]

    # Task
    today_str = today.isoformat()
    where_task = [
        {"type": "or", "value": [
            {"type": "equals", "attribute": "dateEnd", "value": today_str},
            {"type": "before", "attribute": "dateEnd", "value": today_str},
        ]},
        {"type": "notEquals", "attribute": "status", "value": "Completed"},
    ]
    tasks = _search("Task", where_task, select="name,dateEnd,parentName,priority", max_size=10)
    if tasks:
        sezioni.append(f"📋 Task ({len(tasks)}):")
        for t in tasks:
            scad = t.get("dateEnd","")[:10]
            scaduto = " ⚠️" if scad < today_str else ""
            sezioni.append(f"  • {t['name']}{scaduto}")
    else:
        sezioni.append("📋 Nessun task in scadenza.")

    # Ordini
    sezioni.append("\n" + ordini_in_attesa())

    # Clienti urgenti
    all_clients = _search("Account", [],
                          select="id,name,zona,phoneNumber,frequenzaVisitaGiorni,ultimaVisita",
                          max_size=200)
    urgenti = []
    for c in all_clients:
        ultima = c.get("ultimaVisita")
        freq = int(c.get("frequenzaVisitaGiorni") or 30)
        if not ultima:
            ritardo = 9999
        else:
            try:
                ritardo = (today - datetime.strptime(ultima[:10], "%Y-%m-%d").date()).days - freq
            except Exception:
                ritardo = 9999
        if ritardo > 0:
            urgenti.append((ritardo, c))

    urgenti.sort(key=lambda x: -x[0])
    if urgenti[:5]:
        sezioni.append("\n📞 Da ricontattare (top 5):")
        for ritardo, c in urgenti[:5]:
            ultima = c.get("ultimaVisita")
            nota = f"{(today - datetime.strptime(ultima[:10], '%Y-%m-%d').date()).days}gg fa" if ultima else "mai 🆕"
            sezioni.append(f"  • {c['name']} ({c.get('zona','—')}) — {nota}")
        zone: dict = {}
        for _, c in urgenti[:5]:
            z = (c.get("zona") or "").strip()
            if z: zone[z] = zone.get(z, 0) + 1
        if zone:
            zona_top = max(zone, key=lambda z: zone[z])
            sezioni.append(f"\n📍 Zona consigliata: {zona_top} ({zone[zona_top]} clienti urgenti)")
    else:
        sezioni.append("\n📞 Tutti i clienti sono aggiornati ✅")

    return "\n".join(sezioni)


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
