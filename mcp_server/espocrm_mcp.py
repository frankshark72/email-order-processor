"""
EspoCRM MCP Server — espone le operazioni CRM come tool nativi per OpenClaw.

Avvio: python mcp_server/espocrm_mcp.py
Env richieste: ESPOCRM_URL, ESPOCRM_API_KEY

Registrazione in OpenClaw (~/.openclaw/openclaw.json):
  "mcpServers": {
    "espocrm": {
      "command": "python",
      "args": ["/path/to/mcp_server/espocrm_mcp.py"],
      "env": {
        "ESPOCRM_URL": "http://100.79.250.23:8080",
        "ESPOCRM_API_KEY": "<chiave>"
      }
    }
  }
"""

import os
import json
from datetime import date, datetime, timedelta
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

# ── Configurazione ────────────────────────────────────────────────────────────

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "")
API_BASE = f"{ESPOCRM_URL}/api/v1"

mcp = FastMCP("espocrm")


# ── Helper HTTP ───────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}


def _get(entity: str, params: dict | None = None) -> dict:
    r = requests.get(f"{API_BASE}/{entity}", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(entity: str, payload: dict) -> dict:
    r = requests.post(f"{API_BASE}/{entity}", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def _patch(entity: str, record_id: str, payload: dict) -> dict:
    r = requests.patch(f"{API_BASE}/{entity}/{record_id}", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def _search(entity: str, where: list, select: str = "", max_size: int = 50) -> list:
    """Ricerca con filtri WHERE (formato EspoCRM)."""
    params: dict = {"where": json.dumps(where), "maxSize": max_size}
    if select:
        params["select"] = select
    r = requests.get(f"{API_BASE}/{entity}", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("list", [])


# ── Tool: clienti ─────────────────────────────────────────────────────────────

@mcp.tool()
def cerca_cliente(nome: str) -> str:
    """Cerca un cliente/account in EspoCRM per nome (ricerca parziale)."""
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,zona,tipoAccount,frequenzaVisitaGiorni", max_size=10)
    if not results:
        return f"Nessun cliente trovato con nome '{nome}'."
    lines = []
    for c in results:
        zona = c.get("zona") or "—"
        tipo = c.get("tipoAccount") or "cliente"
        tel = c.get("phoneNumber") or "—"
        lines.append(f"• {c['name']} | zona: {zona} | tipo: {tipo} | tel: {tel} | id: {c['id']}")
    return "\n".join(lines)


@mcp.tool()
def lista_clienti(zona: Optional[str] = None, tipo: Optional[str] = None, limit: int = 30) -> str:
    """
    Elenca i clienti. Filtra opzionalmente per zona (es. 'Barese') e/o tipo ('cliente','fornitore').
    """
    where = []
    if zona:
        where.append({"type": "contains", "attribute": "zona", "value": zona})
    if tipo:
        where.append({"type": "equals", "attribute": "tipoAccount", "value": tipo})

    results = _search("Account", where,
                      select="id,name,zona,phoneNumber,frequenzaVisitaGiorni,lastActivityDate",
                      max_size=limit)
    if not results:
        return "Nessun cliente trovato."
    lines = []
    for c in results:
        zona_c = c.get("zona") or "—"
        tel = c.get("phoneNumber") or "—"
        freq = c.get("frequenzaVisitaGiorni") or 30
        lines.append(f"• {c['name']} | zona: {zona_c} | tel: {tel} | visita ogni {freq}gg | id: {c['id']}")
    return f"Trovati {len(results)} clienti:\n" + "\n".join(lines)


@mcp.tool()
def lista_zone() -> str:
    """Elenca tutte le zone presenti in EspoCRM con il numero di clienti per zona."""
    results = _search("Account", [], select="zona", max_size=500)
    zone: dict[str, int] = {}
    for c in results:
        z = (c.get("zona") or "").strip()
        if z:
            zone[z] = zone.get(z, 0) + 1
    if not zone:
        return "Nessuna zona trovata. Aggiungi il campo 'zona' agli account in EspoCRM."
    lines = sorted(zone.items(), key=lambda x: -x[1])
    return "Zone attive:\n" + "\n".join(f"• {z}: {n} clienti" for z, n in lines)


@mcp.tool()
def clienti_zona(zona: str) -> str:
    """
    Restituisce i clienti di una zona ordinati per urgenza di visita
    (ultimi visitati o mai visitati prima).
    Include link Google Maps con waypoint ottimizzati (max 10 fermate).
    """
    results = _search("Account", [{"type": "contains", "attribute": "zona", "value": zona}],
                      select="id,name,phoneNumber,latitudine,longitudine,frequenzaVisitaGiorni,ultimaVisita",
                      max_size=50)
    if not results:
        return f"Nessun cliente trovato nella zona '{zona}'."

    today = date.today()

    def urgency(c: dict) -> int:
        ultima = c.get("ultimaVisita")
        freq = int(c.get("frequenzaVisitaGiorni") or 30)
        if not ultima:
            return 9999  # mai visitato → massima urgenza
        try:
            d = datetime.strptime(ultima[:10], "%Y-%m-%d").date()
            giorni = (today - d).days
            return freq - giorni  # negativo = in ritardo
        except Exception:
            return 9999

    sorted_clients = sorted(results, key=urgency)

    lines = [f"Clienti zona {zona} (ordinati per urgenza visita):"]
    waypoints = []
    for i, c in enumerate(sorted_clients[:20], 1):
        ultima = c.get("ultimaVisita", "")
        if ultima:
            try:
                d = datetime.strptime(ultima[:10], "%Y-%m-%d").date()
                giorni_fa = (today - d).days
                nota_visita = f"{giorni_fa}gg fa"
            except Exception:
                nota_visita = ultima[:10]
        else:
            nota_visita = "mai visitato 🆕"
        tel = c.get("phoneNumber") or "—"
        freq = c.get("frequenzaVisitaGiorni") or 30
        scaduto = "⚠️" if urgency(c) < 0 else ""
        lines.append(f"{i}. {c['name']} | tel: {tel} | visita ogni {freq}gg | ultima: {nota_visita} {scaduto}")

        lat = c.get("latitudine")
        lng = c.get("longitudine")
        if lat and lng and len(waypoints) < 10:
            waypoints.append(f"{lat},{lng}")

    if waypoints:
        maps_url = "https://www.google.com/maps/dir/" + "/".join(waypoints)
        lines.append(f"\n📍 Google Maps ({len(waypoints)} fermate):\n{maps_url}")

    return "\n".join(lines)


@mcp.tool()
def ultima_visita(nome_cliente: str) -> str:
    """Mostra data e note dell'ultima visita/meeting registrata per un cliente."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    account = accounts[0]

    meetings = _search("Meeting", [{"type": "equals", "attribute": "parentId", "value": account["id"]}],
                       select="id,name,dateStart,description", max_size=5)
    if not meetings:
        return f"Nessuna visita registrata per {account['name']}."

    meetings.sort(key=lambda m: m.get("dateStart", ""), reverse=True)
    m = meetings[0]
    data = m.get("dateStart", "")[:10]
    note = m.get("description") or "—"
    return f"Ultima visita a {account['name']}: {data}\nNote: {note}"


# ── Tool: attività ────────────────────────────────────────────────────────────

@mcp.tool()
def registra_visita(nome_cliente: str, note: str = "", data: str = "") -> str:
    """
    Registra una visita (Meeting) per un cliente.
    data: formato YYYY-MM-DD, default oggi.
    """
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato in EspoCRM."
    account = accounts[0]

    visit_date = data if data else date.today().isoformat()
    payload = {
        "name": f"Visita {account['name']}",
        "dateStart": f"{visit_date} 09:00:00",
        "dateEnd": f"{visit_date} 09:30:00",
        "status": "Held",
        "description": note,
        "parentType": "Account",
        "parentId": account["id"],
    }
    result = _post("Meeting", payload)
    # Aggiorna ultimaVisita sull'account
    _patch("Account", account["id"], {"ultimaVisita": visit_date})
    return f"Visita registrata per {account['name']} in data {visit_date}. ID: {result.get('id', '?')}"


@mcp.tool()
def registra_chiamata(nome_cliente: str, durata_minuti: int = 5, note: str = "", data: str = "") -> str:
    """
    Registra una chiamata (Call) per un cliente.
    data: formato YYYY-MM-DD, default oggi.
    """
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato in EspoCRM."
    account = accounts[0]

    call_date = data if data else date.today().isoformat()
    payload = {
        "name": f"Chiamata {account['name']}",
        "dateStart": f"{call_date} 09:00:00",
        "duration": durata_minuti * 60,
        "status": "Held",
        "direction": "Outbound",
        "description": note,
        "parentType": "Account",
        "parentId": account["id"],
    }
    result = _post("Call", payload)
    return f"Chiamata registrata per {account['name']} ({durata_minuti} min) in data {call_date}. ID: {result.get('id', '?')}"


@mcp.tool()
def aggiungi_nota(nome_cliente: str, testo: str) -> str:
    """Aggiunge una nota (Note) associata a un cliente in EspoCRM."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato in EspoCRM."
    account = accounts[0]

    payload = {
        "post": testo,
        "parentType": "Account",
        "parentId": account["id"],
    }
    result = _post("Note", payload)
    return f"Nota aggiunta per {account['name']}. ID: {result.get('id', '?')}"


# ── Tool: task ────────────────────────────────────────────────────────────────

@mcp.tool()
def crea_task(titolo: str, nome_cliente: str = "", scadenza: str = "", nota: str = "") -> str:
    """
    Crea un task/reminder in EspoCRM.
    scadenza: formato YYYY-MM-DD, default domani.
    """
    due = scadenza if scadenza else (date.today() + timedelta(days=1)).isoformat()
    payload: dict = {
        "name": titolo,
        "status": "Not Started",
        "dateEnd": f"{due} 09:00:00",
        "description": nota,
    }
    if nome_cliente:
        accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                           select="id,name", max_size=1)
        if accounts:
            payload["parentType"] = "Account"
            payload["parentId"] = accounts[0]["id"]

    result = _post("Task", payload)
    return f"Task '{titolo}' creato con scadenza {due}. ID: {result.get('id', '?')}"


@mcp.tool()
def task_oggi() -> str:
    """Elenca tutti i task in scadenza oggi o già scaduti (non completati)."""
    today_str = date.today().isoformat()
    where = [
        {"type": "or", "value": [
            {"type": "equals", "attribute": "dateEnd", "value": today_str},
            {"type": "before", "attribute": "dateEnd", "value": today_str},
        ]},
        {"type": "notEquals", "attribute": "status", "value": "Completed"},
    ]
    results = _search("Task", where,
                      select="id,name,status,dateEnd,parentName,description", max_size=20)
    if not results:
        return "✅ Nessuna task in scadenza oggi."
    lines = [f"📋 Task in scadenza ({len(results)}):"]
    for t in results:
        scad = t.get("dateEnd", "")[:10]
        cliente = t.get("parentName") or ""
        cliente_str = f" — {cliente}" if cliente else ""
        stato = t.get("status", "")
        scaduto = "⚠️ SCADUTO" if scad < today_str else ""
        lines.append(f"• {t['name']}{cliente_str} | {scad} {scaduto} [{stato}]")
    return "\n".join(lines)


# ── Tool: ordini ──────────────────────────────────────────────────────────────

@mcp.tool()
def ordini_in_attesa() -> str:
    """Elenca gli ordini email con stato 'in_attesa' ancora da confermare."""
    results = _search("OrdineEmail",
                      [{"type": "equals", "attribute": "stato", "value": "in_attesa"}],
                      select="id,emailDa,emailOggetto,emailData,noteAgente", max_size=20)
    if not results:
        return "✅ Nessun ordine in attesa di conferma."
    today = date.today()
    lines = [f"💰 Ordini in attesa ({len(results)}):"]
    for o in results:
        mittente = o.get("emailDa") or "?"
        oggetto = o.get("emailOggetto") or "?"
        data_email = o.get("emailData") or ""
        if data_email:
            try:
                d = datetime.strptime(data_email[:10], "%Y-%m-%d").date()
                giorni = (today - d).days
                data_str = f"{giorni}gg fa"
            except Exception:
                data_str = data_email[:10]
        else:
            data_str = "?"
        lines.append(f"• Da: {mittente} | {oggetto} | in attesa da {data_str} | id: {o['id']}")
    return "\n".join(lines)


# ── Tool: briefing ────────────────────────────────────────────────────────────

@mcp.tool()
def briefing() -> str:
    """
    Genera il briefing mattutino completo: task di oggi, ordini in attesa,
    e top 5 clienti più urgenti da ricontattare.
    """
    today = date.today()
    oggi_it = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"][today.weekday()]
    mesi_it = ["","gennaio","febbraio","marzo","aprile","maggio","giugno",
               "luglio","agosto","settembre","ottobre","novembre","dicembre"]
    data_it = f"{oggi_it} {today.day} {mesi_it[today.month]} {today.year}"

    sezioni = [f"☀️ Buongiorno! Ecco il tuo briefing per oggi, {data_it}:\n"]

    # 1. Task
    sezioni.append(task_oggi())

    # 2. Ordini
    sezioni.append("\n" + ordini_in_attesa())

    # 3. Clienti urgenti
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
                d = datetime.strptime(ultima[:10], "%Y-%m-%d").date()
                ritardo = (today - d).days - freq
            except Exception:
                ritardo = 9999
        if ritardo > 0:
            urgenti.append((ritardo, c))

    urgenti.sort(key=lambda x: -x[0])
    top5 = urgenti[:5]

    if top5:
        sezioni.append("\n📞 CLIENTI DA RICONTATTARE (top 5):")
        for i, (ritardo, c) in enumerate(top5, 1):
            zona = c.get("zona") or "—"
            ultima = c.get("ultimaVisita")
            if ultima:
                try:
                    d = datetime.strptime(ultima[:10], "%Y-%m-%d").date()
                    giorni_fa = (today - d).days
                    nota = f"{giorni_fa} giorni fa ⚠️"
                except Exception:
                    nota = "?"
            else:
                nota = "mai visitato 🆕"
            sezioni.append(f"  {i}. {c['name']} ({zona}) — {nota}")
    else:
        sezioni.append("\n📞 CLIENTI DA RICONTATTARE:\n  ✅ Tutti i clienti sono aggiornati!")

    # Suggerimento zona
    if top5:
        zone_urgenti: dict[str, int] = {}
        for _, c in top5:
            z = (c.get("zona") or "").strip()
            if z:
                zone_urgenti[z] = zone_urgenti.get(z, 0) + 1
        if zone_urgenti:
            zona_top = max(zone_urgenti, key=lambda z: zone_urgenti[z])
            n_zona = zone_urgenti[zona_top]
            sezioni.append(f"\n📍 SUGGERIMENTO VISITA:\n  Zona {zona_top} ha {n_zona} clienti urgenti.\n  Scrivi '/giro {zona_top}' per il percorso ottimizzato.")

    return "\n".join(sezioni)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not ESPOCRM_API_KEY:
        raise SystemExit("Errore: variabile ESPOCRM_API_KEY non impostata.")
    mcp.run()
