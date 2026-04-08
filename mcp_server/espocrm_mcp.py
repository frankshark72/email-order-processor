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
import sys
import json
import logging
import warnings
from datetime import date, datetime, timedelta
from typing import Optional

# MCP stdio: stdout è riservato al protocollo JSON-RPC.
# Qualsiasi output su stdout corrompe lo stream → tutto su stderr.
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
warnings.filterwarnings("ignore")

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


def _encode_where(params: dict, conditions: list, prefix: str = "where") -> None:
    """Serializza condizioni WHERE ricorsivamente (supporta OR/AND annidati)."""
    for i, condition in enumerate(conditions):
        key_prefix = f"{prefix}[{i}]"
        for key, val in condition.items():
            if key == "value" and isinstance(val, list):
                if val and isinstance(val[0], dict):
                    # Condizioni annidate (OR/AND)
                    _encode_where(params, val, f"{key_prefix}[value]")
                else:
                    for j, v in enumerate(val):
                        params[f"{key_prefix}[{key}][{j}]"] = v
            else:
                params[f"{key_prefix}[{key}]"] = val


def _search(entity: str, where: list, select: str = "", max_size: int = 50) -> list:
    """Ricerca con filtri WHERE (formato EspoCRM). Ritorna [] se entità non esiste (404)."""
    params: dict = {"maxSize": max_size}
    if select:
        params["select"] = select
    _encode_where(params, where)

    r = requests.get(f"{API_BASE}/{entity}", headers=_headers(), params=params, timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    return data.get("list", [])


# ── Tool: clienti ─────────────────────────────────────────────────────────────

@mcp.tool()
def crea_cliente(
    nome: str,
    telefono: str = "",
    email: str = "",
    indirizzo: str = "",
    citta: str = "",
    cap: str = "",
    zona: str = "",
    tipo: str = "Cliente",
    frequenza_visita_giorni: int = 30,
    note: str = "",
) -> str:
    """
    Crea un nuovo cliente (Account) in EspoCRM.
    tipo: 'cliente' o 'fornitore'
    frequenza_visita_giorni: ogni quanti giorni visitarlo (default 30)
    """
    payload: dict = {"name": nome}
    if telefono:
        payload["phoneNumber"] = telefono
    if email:
        payload["emailAddress"] = email
    if indirizzo:
        payload["billingAddressStreet"] = indirizzo
    if citta:
        payload["billingAddressCity"] = citta
    if cap:
        payload["billingAddressPostalCode"] = cap
    if zona:
        payload["zona"] = zona
    if tipo:
        payload["tipoAccount"] = tipo
    if frequenza_visita_giorni:
        payload["frequenzaVisitaGiorni"] = frequenza_visita_giorni
    if note:
        payload["description"] = note

    result = _post("Account", payload)
    record_id = result.get("id", "?")
    return (
        f"✅ Cliente '{nome}' creato in EspoCRM.\n"
        f"   ID: {record_id}\n"
        f"   📞 {telefono or '—'} | ✉️ {email or '—'}\n"
        f"   📍 {', '.join(filter(None,[indirizzo,cap,citta])) or '—'} | zona: {zona or '—'}"
    )


@mcp.tool()
def aggiorna_cliente(
    nome: str,
    telefono: str = "",
    email: str = "",
    indirizzo: str = "",
    citta: str = "",
    cap: str = "",
    zona: str = "",
    tipo: str = "",
    frequenza_visita_giorni: int = 0,
    note: str = "",
) -> str:
    """
    Aggiorna i dati di un cliente esistente in EspoCRM (ricerca per nome).
    Passa solo i campi che vuoi modificare.
    """
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome}' non trovato in EspoCRM."
    account = accounts[0]

    payload: dict = {}
    if telefono:
        payload["phoneNumber"] = telefono
    if email:
        payload["emailAddress"] = email
    if indirizzo:
        payload["billingAddressStreet"] = indirizzo
    if citta:
        payload["billingAddressCity"] = citta
    if cap:
        payload["billingAddressPostalCode"] = cap
    if zona:
        payload["zona"] = zona
    if tipo:
        payload["tipoAccount"] = tipo
    if frequenza_visita_giorni:
        payload["frequenzaVisitaGiorni"] = frequenza_visita_giorni
    if note:
        payload["description"] = note

    if not payload:
        return "Nessun campo da aggiornare specificato."

    _patch("Account", account["id"], payload)
    campi = ", ".join(payload.keys())
    return f"✅ Cliente '{account['name']}' aggiornato. Campi modificati: {campi}"

@mcp.tool()
def cerca_account(nome: str) -> str:
    """
    Cerca qualsiasi account in EspoCRM per nome (clienti, fornitori, prospect).
    Restituisce tutti i campi principali.
    """
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,billingAddressStreet,billingAddressCity,"
                             "billingAddressState,billingAddressPostalCode,zona,tipoAccount,"
                             "referente,priorita,condizioniPagamento,frequenzaVisitaGiorni,"
                             "ultimaVisita,ultimaChiamata,sicCode,website,description",
                      max_size=10)
    if not results:
        return f"Nessun account trovato con nome '{nome}'."
    lines = []
    for c in results:
        tipo = c.get("tipoAccount") or "—"
        tel = c.get("phoneNumber") or "—"
        email = c.get("emailAddress") or "—"
        via = c.get("billingAddressStreet") or ""
        citta = c.get("billingAddressCity") or ""
        prov = c.get("billingAddressState") or ""
        cap = c.get("billingAddressPostalCode") or ""
        indirizzo = ", ".join(filter(None, [via, cap, citta, prov])) or "—"
        zona = c.get("zona") or "—"
        referente = c.get("referente") or "—"
        piva = c.get("sicCode") or "—"
        pagamento = c.get("condizioniPagamento") or "—"
        ultima_visita = c.get("ultimaVisita") or "—"
        ultima_chiamata = c.get("ultimaChiamata") or "—"
        lines.append(
            f"• {c['name']} [{tipo}]\n"
            f"  📞 {tel} | ✉️ {email}\n"
            f"  📍 {indirizzo} | zona: {zona}\n"
            f"  👤 {referente} | P.IVA: {piva}\n"
            f"  💳 {pagamento}\n"
            f"  🗓 Ultima visita: {ultima_visita} | Ultima chiamata: {ultima_chiamata}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def lista_fornitori() -> str:
    """Elenca tutti i fornitori con contatti e categorie prodotti."""
    results = _search("Account",
                      [{"type": "equals", "attribute": "tipoAccount", "value": "Fornitore"}],
                      select="id,name,emailAddress,phoneNumber,billingAddressCity,"
                             "referente,website,sicCode,description",
                      max_size=50)
    if not results:
        return "Nessun fornitore trovato in EspoCRM."
    lines = [f"🏭 Fornitori ({len(results)}):"]
    for f in results:
        tel = f.get("phoneNumber") or "—"
        email = f.get("emailAddress") or "—"
        citta = f.get("billingAddressCity") or "—"
        referente = f.get("referente") or "—"
        note = f.get("description") or ""
        lines.append(
            f"\n• {f['name']}\n"
            f"  📞 {tel} | ✉️ {email} | 📍 {citta}\n"
            f"  👤 {referente}"
            + (f"\n  📝 {note}" if note else "")
        )
    return "\n".join(lines)


@mcp.tool()
def dettaglio_account(nome: str) -> str:
    """
    Mostra tutti i dettagli di un account: anagrafica completa,
    sconti configurati, ultima visita e ultima chiamata.
    """
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,billingAddressStreet,"
                             "billingAddressCity,billingAddressState,billingAddressPostalCode,"
                             "zona,tipoAccount,referente,priorita,condizioniPagamento,"
                             "frequenzaVisitaGiorni,ultimaVisita,ultimaChiamata,"
                             "sicCode,codiceFiscale,website,description",
                      max_size=1)
    if not results:
        return f"Account '{nome}' non trovato."
    c = results[0]

    # Sconti configurati
    sconti = _search("ScontoCliente",
                     [{"type": "equals", "attribute": "clienteId", "value": c["id"]}],
                     select="accountName,categoria,tipoPrezzo,sconto", max_size=20)

    lines = [
        f"📋 {c['name']} [{c.get('tipoAccount','—')}]",
        f"",
        f"📞 Tel: {c.get('phoneNumber') or '—'}",
        f"✉️  Email: {c.get('emailAddress') or '—'}",
        f"🌐 Web: {c.get('website') or '—'}",
        f"📍 {', '.join(filter(None,[c.get('billingAddressStreet',''), c.get('billingAddressPostalCode',''), c.get('billingAddressCity',''), c.get('billingAddressState','')]))}",
        f"🗺  Zona: {c.get('zona') or '—'}",
        f"",
        f"👤 Referente: {c.get('referente') or '—'}",
        f"🏷  P.IVA: {c.get('sicCode') or '—'}",
        f"💳 Pagamento: {c.get('condizioniPagamento') or '—'}",
        f"⭐ Priorità: {c.get('priorita') or '—'}",
        f"",
        f"🗓 Ultima visita: {c.get('ultimaVisita') or 'mai'}",
        f"📞 Ultima chiamata: {c.get('ultimaChiamata') or 'mai'}",
        f"🔄 Frequenza visita: ogni {c.get('frequenzaVisitaGiorni') or 30} giorni",
    ]

    if c.get("description"):
        lines += ["", f"📝 Note: {c['description']}"]

    if sconti:
        lines += ["", "💰 Contratti prezzi:"]
        for s in sconti:
            fornitore = s.get("accountName") or "?"
            tipo = s.get("tipoPrezzo") or "?"
            sconto = s.get("sconto") or 0
            cat = s.get("categoria") or ""
            cat_str = f" [{cat}]" if cat else ""
            sconto_str = f" {sconto}%" if tipo == "sconto_percentuale" and sconto else ""
            lines.append(f"  • {fornitore}{cat_str}: {tipo}{sconto_str}")

    return "\n".join(lines)


@mcp.tool()
def lista_clienti(zona: Optional[str] = None, tipo: Optional[str] = None, limit: int = 30) -> str:
    """
    Elenca i clienti. Filtra opzionalmente per zona (es. 'Barese') e/o tipo ('Cliente','Fornitore','Installatore','Rivenditore','Prospect').
    """
    where = []
    if zona:
        where.append({"type": "contains", "attribute": "zona", "value": zona})
    if tipo:
        where.append({"type": "equals", "attribute": "tipoAccount", "value": tipo})

    results = _search("Account", where,
                      select="id,name,emailAddress,phoneNumber,billingAddressCity,zona,frequenzaVisitaGiorni",
                      max_size=limit)
    if not results:
        return "Nessun cliente trovato."
    lines = []
    for c in results:
        zona_c = c.get("zona") or "—"
        tel = c.get("phoneNumber") or "—"
        email = c.get("emailAddress") or "—"
        citta = c.get("billingAddressCity") or "—"
        freq = c.get("frequenzaVisitaGiorni") or 30
        lines.append(f"• {c['name']} | {citta} | 📞 {tel} | ✉️ {email} | zona: {zona_c} | ogni {freq}gg")
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
    _patch("Account", account["id"], {"ultimaChiamata": call_date})
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
    # Verifica che l'entità esista prima di cercare
    r = requests.get(f"{API_BASE}/OrdineEmail", headers=_headers(),
                     params={"maxSize": 1}, timeout=10)
    if r.status_code == 404:
        return "ℹ️ Entità OrdineEmail non ancora configurata (sarà attiva con il parser email)."
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


# ── Tool: prezzi e sconti ────────────────────────────────────────────────────

@mcp.tool()
def sconti_cliente(nome_cliente: str) -> str:
    """Mostra tutti gli sconti configurati per un cliente (per fornitore e categoria)."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    account = accounts[0]

    sconti = _search("ScontoCliente",
                     [{"type": "equals", "attribute": "clienteId", "value": account["id"]}],
                     select="fornitore,accountName,categoria,sconto,validoDal,validoAl,note",
                     max_size=50)
    if not sconti:
        return f"Nessuno sconto configurato per {account['name']}."

    lines = [f"💰 Sconti di {account['name']}:"]
    for s in sconti:
        fornitore = s.get("accountName") or "?"
        categoria = s.get("categoria") or "tutte"
        sconto = s.get("sconto") or 0
        val_dal = s.get("validoDal") or ""
        val_al = s.get("validoAl") or ""
        validita = f" | valido {val_dal}→{val_al}" if val_dal else ""
        lines.append(f"  • {fornitore} / {categoria}: {sconto}%{validita}")
    return "\n".join(lines)


@mcp.tool()
def aggiungi_sconto(nome_cliente: str, nome_fornitore: str,
                    tipo_prezzo: str = "netto_rivenditore",
                    sconto: float = 0.0,
                    categoria: str = "",
                    valido_dal: str = "", valido_al: str = "",
                    note: str = "") -> str:
    """
    Configura il contratto prezzi per un cliente su un fornitore.
    tipo_prezzo: 'sconto_percentuale' | 'netto_rivenditore' | 'netto_installatore'
    sconto: percentuale (es. 20.0) — solo se tipo_prezzo=sconto_percentuale
    categoria: opzionale, per contratti specifici per categoria
    Il sistema ricorderà questa scelta per i calcoli futuri.
    """
    accounts_c = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                         select="id,name", max_size=1)
    accounts_f = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_fornitore}],
                         select="id,name", max_size=1)
    if not accounts_c:
        return f"Cliente '{nome_cliente}' non trovato."
    if not accounts_f:
        return f"Fornitore '{nome_fornitore}' non trovato."

    cliente = accounts_c[0]
    fornitore = accounts_f[0]

    label = " – ".join(filter(None, [cliente["name"], fornitore["name"], categoria]))
    payload: dict = {
        "name": label,
        "clienteId": cliente["id"],
        "accountId": fornitore["id"],
        "tipoPrezzo": tipo_prezzo,
        "sconto": sconto,
    }
    if categoria:
        payload["categoria"] = categoria
    if valido_dal:
        payload["validoDal"] = valido_dal
    if valido_al:
        payload["validoAl"] = valido_al
    if note:
        payload["note"] = note

    _post("ScontoCliente", payload)
    sconto_str = f" ({sconto}%)" if tipo_prezzo == "sconto_percentuale" and sconto else ""
    cat_str = f" | cat: {categoria}" if categoria else ""
    return (f"✅ Contratto salvato:\n"
            f"   {cliente['name']} | {fornitore['name']}{cat_str}\n"
            f"   Tipo prezzo: {tipo_prezzo}{sconto_str}\n"
            f"   Verrà usato automaticamente nei calcoli futuri.")


@mcp.tool()
def calcola_prezzo(nome_prodotto: str, quantita: int, nome_cliente: str = "") -> str:
    """
    Calcola il prezzo netto per un prodotto con la quantità indicata.
    Se specificato il cliente, usa il tipo prezzo e sconto configurati in ScontoCliente
    (sconto_percentuale / netto_rivenditore / netto_installatore).
    Ricorda automaticamente la scelta fatta per ogni cliente+fornitore.
    """
    # Trova prodotto
    prodotti = _search("CProdotto",
                       [{"type": "contains", "attribute": "name", "value": nome_prodotto}],
                       select="id,name,categoria,accountName,accountId,unitaMisura",
                       max_size=1)
    if not prodotti:
        return f"Prodotto '{nome_prodotto}' non trovato."
    prodotto = prodotti[0]
    fornitore_id = prodotto.get("accountId") or ""
    fornitore_nome = prodotto.get("accountName") or ""
    um = prodotto.get("unitaMisura") or "pz"

    # Determina tipo prezzo e sconto dal contratto cliente
    tipo_prezzo = "netto_rivenditore"  # default
    sconto_pct = 0.0
    contratto_info = ""
    tipo_cliente = "rivenditore"

    if nome_cliente:
        accounts = _search("Account",
                           [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                           select="id,name", max_size=1)
        if accounts:
            cliente = accounts[0]
            sconti = _search("ScontoCliente",
                             [{"type": "equals", "attribute": "clienteId", "value": cliente["id"]},
                              {"type": "equals", "attribute": "accountId", "value": fornitore_id}],
                             select="tipoPrezzo,sconto,categoria,note", max_size=10)
            if sconti:
                # Usa il contratto più specifico (con categoria) se disponibile
                categoria = prodotto.get("categoria") or ""
                contratto = next(
                    (s for s in sconti if (s.get("categoria") or "").lower() == categoria.lower()),
                    sconti[0]
                )
                tipo_prezzo = contratto.get("tipoPrezzo") or "netto_rivenditore"
                sconto_pct = float(contratto.get("sconto") or 0)
                note_contratto = contratto.get("note") or ""
                contratto_info = f"   📋 Contratto: {tipo_prezzo}"
                if note_contratto:
                    contratto_info += f" — {note_contratto}"
                tipo_cliente = "installatore" if tipo_prezzo == "netto_installatore" else "rivenditore"
            else:
                contratto_info = f"   ⚠️ Nessun contratto trovato per {nome_cliente} / {fornitore_nome}"

    # Trova prezzo da RigaListino filtrando per tipoCliente
    where_righe = [{"type": "equals", "attribute": "prodottoId", "value": prodotto["id"]}]
    if tipo_prezzo in ("netto_rivenditore", "netto_installatore"):
        where_righe.append({"type": "equals", "attribute": "tipoCliente", "value": tipo_cliente})

    righe = _search("RigaListino", where_righe,
                    select="tipoCliente,quantitaMinima,prezzoNetto,listinoName",
                    max_size=20)

    prezzo_base = None
    listino_nome = ""
    scaglione_usato = 0
    for r in sorted(righe, key=lambda x: x.get("quantitaMinima", 0), reverse=True):
        if (r.get("quantitaMinima") or 0) <= quantita:
            prezzo_base = r.get("prezzoNetto")
            listino_nome = r.get("listinoName") or ""
            scaglione_usato = r.get("quantitaMinima", 1)
            break

    if prezzo_base is None:
        # Mostra gli scaglioni disponibili per aiutare
        tutti = _search("RigaListino",
                        [{"type": "equals", "attribute": "prodottoId", "value": prodotto["id"]}],
                        select="tipoCliente,quantitaMinima,prezzoNetto", max_size=20)
        if tutti:
            scaglioni = "\n".join(
                f"   {r.get('tipoCliente','?')} qtà≥{r.get('quantitaMinima','?')}: €{r.get('prezzoNetto','?')}"
                for r in sorted(tutti, key=lambda x: (x.get("tipoCliente",""), x.get("quantitaMinima", 0)))
            )
            return f"Nessun prezzo {tipo_cliente} per qtà {quantita}.\nScaglioni disponibili:\n{scaglioni}"
        return f"Nessun prezzo trovato per '{prodotto['name']}'. Verifica le righe listino."

    prezzo_finale = prezzo_base * (1 - sconto_pct / 100) if tipo_prezzo == "sconto_percentuale" else prezzo_base
    totale = prezzo_finale * quantita

    lines = [
        f"📦 {prodotto['name']} × {quantita} {um}",
        f"   Fornitore: {fornitore_nome}",
        f"   Listino: {listino_nome} ({tipo_cliente}, da qtà {scaglione_usato})",
        f"   Prezzo {tipo_prezzo}: €{prezzo_base:.4f}/{um}",
    ]
    if contratto_info:
        lines.append(contratto_info)
    if tipo_prezzo == "sconto_percentuale" and sconto_pct:
        lines.append(f"   Sconto: -{sconto_pct}%  → €{prezzo_finale:.4f}/{um}")
    lines.append(f"   💰 Totale: €{totale:.2f}")
    return "\n".join(lines)


# ── Tool: prodotti ────────────────────────────────────────────────────────────

@mcp.tool()
def cerca_prodotti(
    testo: str = "",
    categoria: str = "",
    fornitore: str = "",
    solo_attivi: bool = True,
    limit: int = 30,
) -> str:
    """
    Cerca prodotti nel catalogo EspoCRM per testo libero, categoria o fornitore.
    testo: cerca in nome, codice e descrizione (es. 'doppia tecnologia esterno')
    categoria: filtra per categoria (es. 'Rivelatori', 'Centrali', 'Telecamere')
    fornitore: filtra per nome fornitore (es. 'Elmo', 'RIB', 'Prospecta')
    solo_attivi: se True mostra solo prodotti attivi (default True)
    """
    where = []

    if testo:
        # OR su nome, codice e descrizione
        where.append({
            "type": "or",
            "value": [
                {"type": "contains", "attribute": "name", "value": testo},
                {"type": "contains", "attribute": "codice", "value": testo},
                {"type": "contains", "attribute": "descrizioneEstesa", "value": testo},
            ]
        })

    if categoria:
        where.append({"type": "contains", "attribute": "categoria", "value": categoria})

    if fornitore:
        where.append({"type": "contains", "attribute": "accountName", "value": fornitore})

    if solo_attivi:
        where.append({"type": "isTrue", "attribute": "attivo"})

    if not where:
        where.append({"type": "isTrue", "attribute": "attivo"})

    prodotti = _search(
        "CProdotto", where,
        select="name,codice,categoria,descrizioneEstesa,prezzoListino,unitaMisura,accountName,attivo",
        max_size=limit,
    )

    if not prodotti:
        filtri = []
        if testo:
            filtri.append(f"testo='{testo}'")
        if categoria:
            filtri.append(f"categoria='{categoria}'")
        if fornitore:
            filtri.append(f"fornitore='{fornitore}'")
        return f"Nessun prodotto trovato con filtri: {', '.join(filtri) or 'nessuno'}."

    righe = [f"📦 Trovati {len(prodotti)} prodotti:\n"]
    for p in prodotti:
        prezzo = p.get("prezzoListino")
        prezzo_str = f"€{float(prezzo):.2f}" if prezzo else "su richiesta"
        um = p.get("unitaMisura") or "pz"
        fornitore_nome = p.get("accountName") or "—"
        categoria_nome = p.get("categoria") or "—"
        descr = p.get("descrizioneEstesa") or ""
        descr_breve = descr[:80] + "..." if len(descr) > 80 else descr

        righe.append(
            f"• [{p.get('codice','—')}] {p['name']}\n"
            f"  Fornitore: {fornitore_nome} | Cat: {categoria_nome} | {prezzo_str}/{um}"
        )
        if descr_breve:
            righe.append(f"  {descr_breve}")

    return "\n".join(righe)


@mcp.tool()
def lista_categorie_prodotti() -> str:
    """Elenca tutte le categorie di prodotti presenti nel catalogo con il conteggio."""
    prodotti = _search("CProdotto", [{"type": "isTrue", "attribute": "attivo"}],
                       select="categoria", max_size=5000)
    conteggio: dict = {}
    for p in prodotti:
        cat = p.get("categoria") or "Senza categoria"
        conteggio[cat] = conteggio.get(cat, 0) + 1

    if not conteggio:
        return "Nessun prodotto nel catalogo."

    righe = ["📂 Categorie prodotti:\n"]
    for cat, n in sorted(conteggio.items(), key=lambda x: -x[1]):
        righe.append(f"  • {cat}: {n} prodotti")
    return "\n".join(righe)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not ESPOCRM_API_KEY:
        print("Errore: variabile ESPOCRM_API_KEY non impostata.", file=sys.stderr)
        sys.exit(1)
    mcp.run(transport="stdio")
