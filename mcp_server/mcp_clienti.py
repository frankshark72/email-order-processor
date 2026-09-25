"""MCP server — Clienti, Fornitori, Attività, Sconti."""
import sys
from datetime import date, datetime, timedelta

from mcp.server.fastmcp import FastMCP
from _common import _headers, _post, _patch, _search, _check_api_key, API_BASE

import requests

mcp = FastMCP("clienti")


@mcp.tool()
def crea_cliente(nome: str, telefono: str = "", email: str = "", indirizzo: str = "",
                 citta: str = "", cap: str = "", zona: str = "", tipo: str = "cliente",
                 frequenza_visita_giorni: int = 30, note: str = "") -> str:
    """Crea un nuovo Account (cliente o fornitore) in EspoCRM."""
    payload: dict = {"name": nome}
    if telefono: payload["phoneNumber"] = telefono
    if email: payload["emailAddress"] = email
    if indirizzo: payload["billingAddressStreet"] = indirizzo
    if citta: payload["billingAddressCity"] = citta
    if cap: payload["billingAddressPostalCode"] = cap
    if zona: payload["zona"] = zona
    if tipo: payload["tipoAccount"] = tipo
    if frequenza_visita_giorni: payload["frequenzaVisitaGiorni"] = frequenza_visita_giorni
    if note: payload["description"] = note
    result = _post("Account", payload)
    return f"✅ Account '{nome}' creato. ID: {result.get('id','?')}"


@mcp.tool()
def aggiorna_cliente(nome: str, telefono: str = "", email: str = "", indirizzo: str = "",
                     citta: str = "", cap: str = "", zona: str = "", tipo: str = "",
                     frequenza_visita_giorni: int = 0, note: str = "") -> str:
    """Aggiorna i dati di un Account esistente (ricerca per nome)."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Account '{nome}' non trovato."
    payload: dict = {}
    if telefono: payload["phoneNumber"] = telefono
    if email: payload["emailAddress"] = email
    if indirizzo: payload["billingAddressStreet"] = indirizzo
    if citta: payload["billingAddressCity"] = citta
    if cap: payload["billingAddressPostalCode"] = cap
    if zona: payload["zona"] = zona
    if tipo: payload["tipoAccount"] = tipo
    if frequenza_visita_giorni: payload["frequenzaVisitaGiorni"] = frequenza_visita_giorni
    if note: payload["description"] = note
    if not payload:
        return "Nessun campo da aggiornare."
    _patch("Account", accounts[0]["id"], payload)
    return f"✅ Account '{accounts[0]['name']}' aggiornato: {', '.join(payload.keys())}"


@mcp.tool()
def cerca_account(nome: str) -> str:
    """Cerca clienti/fornitori per nome e restituisce i dati principali."""
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,billingAddressStreet,"
                             "billingAddressCity,billingAddressPostalCode,zona,tipoAccount,"
                             "referente,priorita,condizioniPagamento,frequenzaVisitaGiorni,"
                             "ultimaVisita,ultimaChiamata,website,description",
                      max_size=10)
    if not results:
        return f"Nessun account trovato per '{nome}'."
    lines = []
    for c in results:
        addr = ", ".join(filter(None, [c.get("billingAddressStreet",""),
                                       c.get("billingAddressPostalCode",""),
                                       c.get("billingAddressCity","")])) or "—"
        lines.append(
            f"• {c['name']} [{c.get('tipoAccount','—')}]\n"
            f"  📞 {c.get('phoneNumber','—')} | ✉️ {c.get('emailAddress','—')}\n"
            f"  📍 {addr} | zona: {c.get('zona','—')}\n"
            f"  👤 {c.get('referente','—')} | 💳 {c.get('condizioniPagamento','—')}\n"
            f"  🗓 Visita: {c.get('ultimaVisita','mai')} | Chiamata: {c.get('ultimaChiamata','mai')}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def dettaglio_account(nome: str) -> str:
    """Mostra anagrafica completa + sconti configurati per un account."""
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,billingAddressStreet,"
                             "billingAddressCity,billingAddressState,billingAddressPostalCode,"
                             "zona,tipoAccount,referente,priorita,condizioniPagamento,"
                             "frequenzaVisitaGiorni,ultimaVisita,ultimaChiamata,website,description",
                      max_size=1)
    if not results:
        return f"Account '{nome}' non trovato."
    c = results[0]
    addr = ", ".join(filter(None, [c.get("billingAddressStreet",""),
                                   c.get("billingAddressPostalCode",""),
                                   c.get("billingAddressCity",""),
                                   c.get("billingAddressState","")])) or "—"
    lines = [
        f"📋 {c['name']} [{c.get('tipoAccount','—')}]",
        f"📞 {c.get('phoneNumber','—')} | ✉️ {c.get('emailAddress','—')}",
        f"📍 {addr} | zona: {c.get('zona','—')}",
        f"👤 {c.get('referente','—')} | 💳 {c.get('condizioniPagamento','—')} | ⭐ {c.get('priorita','—')}",
        f"🗓 Visita: {c.get('ultimaVisita','mai')} | Chiamata: {c.get('ultimaChiamata','mai')}",
        f"🔄 Ogni {c.get('frequenzaVisitaGiorni',30)}gg",
    ]
    if c.get("description"):
        lines.append(f"📝 {c['description']}")

    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "accountId", "value": c["id"]}],
                     select="fornitoreName,tipoCliente,scontoPct,note", max_size=20)
    if sconti:
        lines.append("\n💰 Sconti:")
        for s in sconti:
            sc = f" {s.get('scontoPct',0)}%" if s.get('scontoPct') else ""
            lines.append(f"  • {s.get('fornitoreName','?')} | {s.get('tipoCliente','?')}{sc}")
    return "\n".join(lines)


@mcp.tool()
def lista_clienti(zona: str = "", tipo: str = "", limit: int = 30) -> str:
    """Elenca account. Filtra per zona e/o tipo (cliente/fornitore)."""
    where = []
    if zona: where.append({"type": "contains", "attribute": "zona", "value": zona})
    if tipo: where.append({"type": "equals", "attribute": "tipoAccount", "value": tipo})
    results = _search("Account", where,
                      select="name,phoneNumber,billingAddressCity,zona,frequenzaVisitaGiorni",
                      max_size=limit)
    if not results:
        return "Nessun account trovato."
    lines = [f"Trovati {len(results)} account:"]
    for c in results:
        lines.append(f"• {c['name']} | {c.get('billingAddressCity','—')} | "
                     f"📞 {c.get('phoneNumber','—')} | zona: {c.get('zona','—')}")
    return "\n".join(lines)


@mcp.tool()
def lista_fornitori() -> str:
    """Elenca tutti i fornitori con contatti."""
    results = _search("Account",
                      [{"type": "equals", "attribute": "tipoAccount", "value": "fornitore"}],
                      select="name,emailAddress,phoneNumber,billingAddressCity,referente",
                      max_size=50)
    if not results:
        return "Nessun fornitore trovato."
    lines = [f"🏭 Fornitori ({len(results)}):"]
    for f in results:
        lines.append(f"• {f['name']} | 📞 {f.get('phoneNumber','—')} | "
                     f"✉️ {f.get('emailAddress','—')} | 👤 {f.get('referente','—')}")
    return "\n".join(lines)


@mcp.tool()
def lista_zone() -> str:
    """Elenca zone con conteggio clienti per zona."""
    results = _search("Account", [], select="zona", max_size=500)
    zone: dict = {}
    for c in results:
        z = (c.get("zona") or "").strip()
        if z:
            zone[z] = zone.get(z, 0) + 1
    if not zone:
        return "Nessuna zona trovata."
    return "Zone:\n" + "\n".join(f"• {z}: {n}" for z, n in sorted(zone.items(), key=lambda x: -x[1]))


@mcp.tool()
def clienti_zona(zona: str) -> str:
    """Clienti di una zona ordinati per urgenza visita, con link Google Maps."""
    results = _search("Account", [{"type": "contains", "attribute": "zona", "value": zona}],
                      select="id,name,phoneNumber,latitudine,longitudine,frequenzaVisitaGiorni,ultimaVisita",
                      max_size=50)
    if not results:
        return f"Nessun cliente in zona '{zona}'."
    today = date.today()

    def urgency(c: dict) -> int:
        ultima = c.get("ultimaVisita")
        freq = int(c.get("frequenzaVisitaGiorni") or 30)
        if not ultima:
            return 9999
        try:
            return freq - (today - datetime.strptime(ultima[:10], "%Y-%m-%d").date()).days
        except Exception:
            return 9999

    lines = [f"Clienti zona {zona}:"]
    waypoints = []
    for i, c in enumerate(sorted(results, key=urgency)[:20], 1):
        ultima = c.get("ultimaVisita","")
        if ultima:
            try:
                giorni_fa = (today - datetime.strptime(ultima[:10], "%Y-%m-%d").date()).days
                nota = f"{giorni_fa}gg fa"
            except Exception:
                nota = ultima[:10]
        else:
            nota = "mai 🆕"
        scaduto = "⚠️" if urgency(c) < 0 else ""
        lines.append(f"{i}. {c['name']} | 📞 {c.get('phoneNumber','—')} | ultima: {nota} {scaduto}")
        lat, lng = c.get("latitudine"), c.get("longitudine")
        if lat and lng and len(waypoints) < 10:
            waypoints.append(f"{lat},{lng}")
    if waypoints:
        lines.append(f"\n📍 Maps: https://www.google.com/maps/dir/" + "/".join(waypoints))
    return "\n".join(lines)


@mcp.tool()
def registra_visita(nome_cliente: str, note: str = "", data: str = "") -> str:
    """Registra una visita (Meeting) per un cliente. data: YYYY-MM-DD, default oggi."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    d = data or date.today().isoformat()
    result = _post("Meeting", {
        "name": f"Visita {a['name']}", "dateStart": f"{d} 09:00:00", "dateEnd": f"{d} 09:30:00",
        "status": "Held", "description": note, "parentType": "Account", "parentId": a["id"],
    })
    _patch("Account", a["id"], {"ultimaVisita": d})
    return f"✅ Visita registrata per {a['name']} il {d}."


@mcp.tool()
def registra_chiamata(nome_cliente: str, durata_minuti: int = 5, note: str = "", data: str = "") -> str:
    """Registra una chiamata (Call) per un cliente. data: YYYY-MM-DD, default oggi."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    d = data or date.today().isoformat()
    _post("Call", {
        "name": f"Chiamata {a['name']}", "dateStart": f"{d} 09:00:00",
        "duration": durata_minuti * 60, "status": "Held", "direction": "Outbound",
        "description": note, "parentType": "Account", "parentId": a["id"],
    })
    _patch("Account", a["id"], {"ultimaChiamata": d})
    return f"✅ Chiamata registrata per {a['name']} ({durata_minuti} min) il {d}."


@mcp.tool()
def aggiungi_nota(nome_cliente: str, testo: str) -> str:
    """Aggiunge una nota a un cliente in EspoCRM."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    _post("Note", {"post": testo, "parentType": "Account", "parentId": a["id"]})
    return f"✅ Nota aggiunta per {a['name']}."


@mcp.tool()
def sconti_cliente(nome_cliente: str) -> str:
    """Mostra gli sconti configurati per un cliente (per fornitore)."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "accountId", "value": a["id"]}],
                     select="fornitoreName,tipoCliente,scontoPct,note", max_size=50)
    if not sconti:
        return f"Nessuno sconto configurato per {a['name']}."
    lines = [f"💰 Sconti di {a['name']}:"]
    for s in sconti:
        sc = f" {s.get('scontoPct',0)}%" if s.get('scontoPct') else ""
        lines.append(f"  • {s.get('fornitoreName','?')} | {s.get('tipoCliente','?')}{sc} | {s.get('note','')}")
    return "\n".join(lines)


@mcp.tool()
def aggiungi_sconto(nome_cliente: str, nome_fornitore: str,
                    tipo_cliente: str = "rivenditore", sconto_pct: float = 0.0,
                    note: str = "") -> str:
    """Configura lo sconto base di un cliente per un fornitore.
    tipo_cliente: rivenditore | installatore
    sconto_pct: percentuale extra sconto (es. 5.0 = 5%)
    """
    ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                 select="id,name", max_size=1)
    af = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_fornitore}],
                 select="id,name", max_size=1)
    if not ac: return f"Cliente '{nome_cliente}' non trovato."
    if not af: return f"Fornitore '{nome_fornitore}' non trovato."
    payload = {
        "name": f"{ac[0]['name']} – {af[0]['name']}",
        "accountId": ac[0]["id"],
        "fornitoreId": af[0]["id"],
        "tipoCliente": tipo_cliente,
        "scontoPct": sconto_pct,
    }
    if note: payload["note"] = note
    _post("CScontoCliente", payload)
    return f"✅ Sconto salvato: {ac[0]['name']} | {af[0]['name']} | {tipo_cliente} | {sconto_pct}%"


@mcp.tool()
def clienti_per_fornitore(nome_fornitore: str) -> str:
    """Elenca tutti i clienti associati a un fornitore (per campagne mirate)."""
    fornitori = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_fornitore}],
                        select="id,name", max_size=1)
    if not fornitori:
        return f"Fornitore '{nome_fornitore}' non trovato."
    f = fornitori[0]

    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "fornitoreId", "value": f["id"]}],
                     select="accountId,accountName,tipoCliente,scontoPct", max_size=200)
    if not sconti:
        return f"Nessun cliente associato a {f['name']}."

    lines = [f"👥 Clienti {f['name']} ({len(sconti)}):"]
    for s in sconti:
        sc = f" -{s['scontoPct']}%" if s.get("scontoPct") else ""
        lines.append(f"  • {s.get('accountName','?')} | {s.get('tipoCliente','?')}{sc}")
    return "\n".join(lines)


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
