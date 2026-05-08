"""EspoCRM MCP — server unico, codice modulare."""
import sys
import os
import requests
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from _common import (ESPOCRM_URL, ESPOCRM_API_KEY, API_BASE,
                     _headers, _post, _patch, _search, _check_api_key)

mcp = FastMCP("espocrm")

# ── CLIENTI ──────────────────────────────────────────────────────────────────

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
    return f"✅ '{accounts[0]['name']}' aggiornato: {', '.join(payload.keys())}"


@mcp.tool()
def cerca_account(nome: str) -> str:
    """Cerca clienti/fornitori per nome."""
    results = _search("Account", [{"type": "contains", "attribute": "name", "value": nome}],
                      select="id,name,emailAddress,phoneNumber,billingAddressStreet,"
                             "billingAddressCity,billingAddressPostalCode,zona,tipoAccount,"
                             "referente,priorita,condizioniPagamento,frequenzaVisitaGiorni,"
                             "ultimaVisita,ultimaChiamata,website",
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
            f"  🗓 Visita: {c.get('ultimaVisita','mai')} | Tel: {c.get('ultimaChiamata','mai')}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def dettaglio_account(nome: str) -> str:
    """Anagrafica completa + sconti per un account."""
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
                                   c.get("billingAddressCity","")])) or "—"
    lines = [
        f"📋 {c['name']} [{c.get('tipoAccount','—')}]",
        f"📞 {c.get('phoneNumber','—')} | ✉️ {c.get('emailAddress','—')}",
        f"📍 {addr} | zona: {c.get('zona','—')}",
        f"👤 {c.get('referente','—')} | 💳 {c.get('condizioniPagamento','—')} | ⭐ {c.get('priorita','—')}",
        f"🗓 Visita: {c.get('ultimaVisita','mai')} | Tel: {c.get('ultimaChiamata','mai')} | ogni {c.get('frequenzaVisitaGiorni',30)}gg",
    ]
    if c.get("description"):
        lines.append(f"📝 {c['description']}")
    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "accountId", "value": c["id"]}],
                     select="fornitoreName,tipoCliente,scontoPct", max_size=20)
    if sconti:
        lines.append("💰 Sconti:")
        for s in sconti:
            sc = f" -{s.get('scontoPct',0)}%" if s.get('scontoPct') else ""
            lines.append(f"  • {s.get('fornitoreName','?')} | {s.get('tipoCliente','?')}{sc}")
    return "\n".join(lines)


@mcp.tool()
def lista_clienti(zona: str = "", tipo: str = "", limit: int = 30) -> str:
    """Elenca account. Filtra per zona e/o tipo."""
    where = []
    if zona: where.append({"type": "contains", "attribute": "zona", "value": zona})
    if tipo: where.append({"type": "equals", "attribute": "tipoAccount", "value": tipo})
    results = _search("Account", where,
                      select="name,phoneNumber,billingAddressCity,zona,frequenzaVisitaGiorni",
                      max_size=limit)
    if not results:
        return "Nessun account trovato."
    lines = [f"Trovati {len(results)}:"]
    for c in results:
        lines.append(f"• {c['name']} | {c.get('billingAddressCity','—')} | "
                     f"📞 {c.get('phoneNumber','—')} | zona: {c.get('zona','—')}")
    return "\n".join(lines)


@mcp.tool()
def lista_zone() -> str:
    """Elenca zone con conteggio clienti."""
    results = _search("Account", [], select="zona", max_size=500)
    zone: dict = {}
    for c in results:
        z = (c.get("zona") or "").strip()
        if z: zone[z] = zone.get(z, 0) + 1
    if not zone:
        return "Nessuna zona trovata."
    return "Zone:\n" + "\n".join(f"• {z}: {n}" for z, n in sorted(zone.items(), key=lambda x: -x[1]))


@mcp.tool()
def clienti_zona(zona: str) -> str:
    """Clienti di una zona ordinati per urgenza visita + link Maps."""
    results = _search("Account", [{"type": "contains", "attribute": "zona", "value": zona}],
                      select="id,name,phoneNumber,latitudine,longitudine,frequenzaVisitaGiorni,ultimaVisita",
                      max_size=50)
    if not results:
        return f"Nessun cliente in zona '{zona}'."
    today = date.today()

    def urgency(c: dict) -> int:
        ultima = c.get("ultimaVisita")
        freq = int(c.get("frequenzaVisitaGiorni") or 30)
        if not ultima: return 9999
        try:
            return freq - (today - datetime.strptime(ultima[:10], "%Y-%m-%d").date()).days
        except Exception:
            return 9999

    lines = [f"Zona {zona}:"]
    waypoints = []
    for i, c in enumerate(sorted(results, key=urgency)[:20], 1):
        ultima = c.get("ultimaVisita","")
        try:
            nota = f"{(today - datetime.strptime(ultima[:10],'%Y-%m-%d').date()).days}gg fa" if ultima else "mai 🆕"
        except Exception:
            nota = ultima[:10]
        lines.append(f"{i}. {c['name']} | {c.get('phoneNumber','—')} | {nota} {'⚠️' if urgency(c)<0 else ''}")
        lat, lng = c.get("latitudine"), c.get("longitudine")
        if lat and lng and len(waypoints) < 10:
            waypoints.append(f"{lat},{lng}")
    if waypoints:
        lines.append(f"\n📍 Maps: https://www.google.com/maps/dir/" + "/".join(waypoints))
    return "\n".join(lines)


@mcp.tool()
def clienti_per_fornitore(nome_fornitore: str) -> str:
    """Elenca clienti associati a un fornitore (per campagne mirate)."""
    fornitori = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_fornitore}],
                        select="id,name", max_size=1)
    if not fornitori:
        return f"Fornitore '{nome_fornitore}' non trovato."
    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "fornitoreId", "value": fornitori[0]["id"]}],
                     select="accountName,tipoCliente,scontoPct", max_size=200)
    if not sconti:
        return f"Nessun cliente associato a {fornitori[0]['name']}."
    lines = [f"👥 Clienti {fornitori[0]['name']} ({len(sconti)}):"]
    for s in sconti:
        sc = f" -{s['scontoPct']}%" if s.get("scontoPct") else ""
        lines.append(f"  • {s.get('accountName','?')} | {s.get('tipoCliente','?')}{sc}")
    return "\n".join(lines)


@mcp.tool()
def registra_visita(nome_cliente: str, note: str = "", data: str = "") -> str:
    """Registra una visita per un cliente. data: YYYY-MM-DD, default oggi."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    d = data or date.today().isoformat()
    _post("Meeting", {"name": f"Visita {a['name']}", "dateStart": f"{d} 09:00:00",
                      "dateEnd": f"{d} 09:30:00", "status": "Held", "description": note,
                      "parentType": "Account", "parentId": a["id"]})
    _patch("Account", a["id"], {"ultimaVisita": d})
    return f"✅ Visita registrata per {a['name']} il {d}."


@mcp.tool()
def registra_chiamata(nome_cliente: str, durata_minuti: int = 5, note: str = "", data: str = "") -> str:
    """Registra una chiamata per un cliente. data: YYYY-MM-DD, default oggi."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    a = accounts[0]
    d = data or date.today().isoformat()
    _post("Call", {"name": f"Chiamata {a['name']}", "dateStart": f"{d} 09:00:00",
                   "duration": durata_minuti * 60, "status": "Held", "direction": "Outbound",
                   "description": note, "parentType": "Account", "parentId": a["id"]})
    _patch("Account", a["id"], {"ultimaChiamata": d})
    return f"✅ Chiamata registrata per {a['name']} ({durata_minuti} min) il {d}."


@mcp.tool()
def aggiungi_nota(nome_cliente: str, testo: str) -> str:
    """Aggiunge una nota a un cliente."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    _post("Note", {"post": testo, "parentType": "Account", "parentId": accounts[0]["id"]})
    return f"✅ Nota aggiunta per {accounts[0]['name']}."


@mcp.tool()
def sconti_cliente(nome_cliente: str) -> str:
    """Mostra gli sconti configurati per un cliente."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Cliente '{nome_cliente}' non trovato."
    sconti = _search("CScontoCliente",
                     [{"type": "equals", "attribute": "accountId", "value": accounts[0]["id"]}],
                     select="fornitoreName,tipoCliente,scontoPct,note", max_size=50)
    if not sconti:
        return f"Nessuno sconto per {accounts[0]['name']}."
    lines = [f"💰 Sconti di {accounts[0]['name']}:"]
    for s in sconti:
        sc = f" {s.get('scontoPct',0)}%" if s.get('scontoPct') else ""
        lines.append(f"  • {s.get('fornitoreName','?')} | {s.get('tipoCliente','?')}{sc}")
    return "\n".join(lines)


@mcp.tool()
def aggiungi_sconto(nome_cliente: str, nome_fornitore: str,
                    tipo_cliente: str = "rivenditore", sconto_pct: float = 0.0,
                    note: str = "") -> str:
    """Configura sconto base cliente/fornitore. tipo_cliente: rivenditore|installatore."""
    ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                 select="id,name", max_size=1)
    af = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_fornitore}],
                 select="id,name", max_size=1)
    if not ac: return f"Cliente '{nome_cliente}' non trovato."
    if not af: return f"Fornitore '{nome_fornitore}' non trovato."
    payload = {"name": f"{ac[0]['name']} – {af[0]['name']}", "accountId": ac[0]["id"],
               "fornitoreId": af[0]["id"], "tipoCliente": tipo_cliente, "scontoPct": sconto_pct}
    if note: payload["note"] = note
    _post("CScontoCliente", payload)
    return f"✅ Sconto: {ac[0]['name']} | {af[0]['name']} | {tipo_cliente} | {sconto_pct}%"


# ── PRODOTTI ──────────────────────────────────────────────────────────────────

@mcp.tool()
def cerca_prodotti(testo: str = "", categoria: str = "", fornitore: str = "",
                   solo_attivi: bool = False, limit: int = 50) -> str:
    """Cerca prodotti per testo (codice/nome/descrizione), categoria o fornitore. Elenca TUTTI i risultati trovati senza riassumere."""
    where = []
    if testo:
        # Ogni parola deve essere presente (AND), cercata su nome/codice/descrizione (OR)
        for parola in testo.split():
            if len(parola) >= 1:
                where.append({"type": "or", "value": [
                    {"type": "contains", "attribute": "name", "value": parola},
                    {"type": "contains", "attribute": "codice", "value": parola},
                    {"type": "contains", "attribute": "descrizioneEstesa", "value": parola},
                ]})
    if categoria: where.append({"type": "contains", "attribute": "categoria", "value": categoria})
    if fornitore: where.append({"type": "contains", "attribute": "accountName", "value": fornitore})
    if solo_attivi: where.append({"type": "isTrue", "attribute": "attivo"})
    if not where: where.append({"type": "isTrue", "attribute": "attivo"})

    # Prima ottieni il totale
    import requests as req
    from _common import _encode_where as ew
    count_params: dict = {"maxSize": 1}
    ew(count_params, where)
    r = req.get(f"{API_BASE}/CProdotto", headers=_headers(), params=count_params, timeout=10)
    totale = r.json().get("total", 0) if r.status_code == 200 else 0

    prodotti = _search("CProdotto", where,
                       select="name,codice,categoria,prezzoListino,unitaMisura,accountName",
                       max_size=limit, order_by="name", order_direction="asc")
    if not prodotti:
        return "Nessun prodotto trovato."

    lines = [f"📦 {totale} prodotti trovati — mostro i primi {len(prodotti)}:"]
    for p in prodotti:
        prezzo = p.get("prezzoListino")
        prezzo_str = f"€{float(prezzo):.2f}" if prezzo else "—"
        lines.append(f"• [{p.get('codice','—')}] {p['name']} | {p.get('accountName','—')} | {prezzo_str}/{p.get('unitaMisura','pz')}")

    if totale > limit:
        lines.append(f"\n⚠️ Ci sono altri {totale - limit} prodotti. Affina la ricerca (es. aggiungi categoria o fornitore).")
    return "\n".join(lines)


@mcp.tool()
def lista_categorie_prodotti() -> str:
    """Elenca categorie prodotti con conteggio."""
    prodotti = _search("CProdotto", [{"type": "isTrue", "attribute": "attivo"}],
                       select="categoria", max_size=5000)
    conteggio: dict = {}
    for p in prodotti:
        cat = p.get("categoria") or "Senza categoria"
        conteggio[cat] = conteggio.get(cat, 0) + 1
    if not conteggio:
        return "Nessun prodotto."
    return "📂 Categorie:\n" + "\n".join(
        f"  • {cat}: {n}" for cat, n in sorted(conteggio.items(), key=lambda x: -x[1]))


@mcp.tool()
def calcola_prezzo(nome_prodotto: str, quantita: int = 1, nome_cliente: str = "") -> str:
    """Calcola prezzo netto per prodotto e quantità, usando il contratto cliente se disponibile."""
    prodotti = _search("CProdotto",
                       [{"type": "or", "value": [
                           {"type": "contains", "attribute": "name", "value": nome_prodotto},
                           {"type": "contains", "attribute": "codice", "value": nome_prodotto},
                       ]}],
                       select="id,name,codice,accountName,accountId,unitaMisura", max_size=1)
    if not prodotti:
        return f"Prodotto '{nome_prodotto}' non trovato."
    p = prodotti[0]
    um = p.get("unitaMisura") or "pz"
    tipo_cliente = "rivenditore"
    sconto_pct = 0.0
    contratto_info = ""

    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id,name", max_size=1)
        if ac:
            sconti = _search("CScontoCliente",
                             [{"type": "equals", "attribute": "accountId", "value": ac[0]["id"]},
                              {"type": "equals", "attribute": "fornitoreId", "value": p.get("accountId","")}],
                             select="tipoCliente,scontoPct", max_size=1)
            if sconti:
                tipo_cliente = sconti[0].get("tipoCliente") or "rivenditore"
                sconto_pct = float(sconti[0].get("scontoPct") or 0)
                contratto_info = f"Contratto: {tipo_cliente}" + (f" -{sconto_pct}%" if sconto_pct else "")
            else:
                contratto_info = f"⚠️ Nessun contratto per {ac[0]['name']} / {p.get('accountName','?')}"

    righe = _search("RigaListino",
                    [{"type": "equals", "attribute": "prodottoId", "value": p["id"]},
                     {"type": "equals", "attribute": "tipoCliente", "value": tipo_cliente}],
                    select="quantitaMinima,prezzoNetto", max_size=20)

    prezzo_base = None
    scaglione = 0
    for r in sorted(righe, key=lambda x: x.get("quantitaMinima", 0), reverse=True):
        if (r.get("quantitaMinima") or 0) <= quantita:
            prezzo_base = r.get("prezzoNetto")
            scaglione = r.get("quantitaMinima", 1)
            break

    if prezzo_base is None:
        tutti = _search("RigaListino",
                        [{"type": "equals", "attribute": "prodottoId", "value": p["id"]}],
                        select="tipoCliente,quantitaMinima,prezzoNetto", max_size=20)
        if tutti:
            sc = "\n".join(f"  {r.get('tipoCliente','?')} qtà≥{r.get('quantitaMinima','?')}: €{r.get('prezzoNetto','?')}"
                           for r in sorted(tutti, key=lambda x: (x.get("tipoCliente",""), x.get("quantitaMinima",0))))
            return f"Nessun prezzo {tipo_cliente} per qtà {quantita}.\nScaglioni:\n{sc}"
        return f"Nessun prezzo in listino per '{p['name']}'."

    prezzo_finale = prezzo_base * (1 - sconto_pct / 100) if sconto_pct else prezzo_base
    lines = [
        f"📦 [{p.get('codice','—')}] {p['name']} × {quantita} {um}",
        f"   {p.get('accountName','—')} | {tipo_cliente} qtà≥{scaglione}",
        f"   Prezzo netto: €{prezzo_base:.4f}/{um}",
    ]
    if contratto_info: lines.append(f"   {contratto_info}")
    if sconto_pct: lines.append(f"   Sconto: -{sconto_pct}% → €{prezzo_finale:.4f}/{um}")
    lines.append(f"   💰 Totale: €{prezzo_finale * quantita:.2f}")
    return "\n".join(lines)


# ── TASK ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def crea_task(titolo: str, nome_cliente: str = "", scadenza: str = "",
              priorita: str = "Normal", nota: str = "") -> str:
    """Crea un task. scadenza: YYYY-MM-DD. priorita: Low|Normal|High|Urgent."""
    due = scadenza or (date.today() + timedelta(days=1)).isoformat()
    payload: dict = {"name": titolo, "status": "Not Started",
                     "priority": priorita, "dateEnd": f"{due} 09:00:00"}
    if nota: payload["description"] = nota
    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id", max_size=1)
        if ac:
            payload["parentType"] = "Account"
            payload["parentId"] = ac[0]["id"]
    result = _post("Task", payload)
    return f"✅ Task '{titolo}' creato. Scadenza: {due}."


@mcp.tool()
def task_oggi() -> str:
    """Task in scadenza oggi o scaduti (non completati)."""
    today = date.today().isoformat()
    where = [
        {"type": "or", "value": [
            {"type": "equals", "attribute": "dateEnd", "value": today},
            {"type": "before", "attribute": "dateEnd", "value": today},
        ]},
        {"type": "notEquals", "attribute": "status", "value": "Completed"},
    ]
    results = _search("Task", where, select="name,status,dateEnd,parentName,priority", max_size=20)
    if not results:
        return "✅ Nessun task in scadenza."
    lines = [f"📋 Task ({len(results)}):"]
    for t in results:
        scad = t.get("dateEnd","")[:10]
        parent = f" — {t['parentName']}" if t.get("parentName") else ""
        lines.append(f"• [{t.get('priority','N')}] {t['name']}{parent} | {scad}{'⚠️' if scad < today else ''}")
    return "\n".join(lines)


@mcp.tool()
def lista_task(solo_aperti: bool = True, nome_cliente: str = "", limit: int = 20) -> str:
    """Elenca task. solo_aperti: esclude completati/cancellati."""
    where = []
    if solo_aperti:
        where.append({"type": "notIn", "attribute": "status", "value": ["Completed", "Canceled"]})
    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id", max_size=1)
        if ac:
            where.append({"type": "equals", "attribute": "parentId", "value": ac[0]["id"]})
    tasks = _search("Task", where, select="name,status,priority,dateEnd,parentName", max_size=limit)
    if not tasks:
        return "Nessun task trovato."
    lines = [f"📋 Task ({len(tasks)}):"]
    for t in tasks:
        parent = f" | {t['parentName']}" if t.get("parentName") else ""
        lines.append(f"• [{t.get('priority','N')}] {t['name']} | {t.get('status','—')} | "
                     f"{(t.get('dateEnd','—'))[:10]}{parent}")
    return "\n".join(lines)


@mcp.tool()
def completa_task(titolo: str) -> str:
    """Segna un task come completato (cerca per titolo)."""
    tasks = _search("Task", [{"type": "contains", "attribute": "name", "value": titolo}],
                    select="id,name", max_size=1)
    if not tasks:
        return f"Task '{titolo}' non trovato."
    _patch("Task", tasks[0]["id"], {"status": "Completed"})
    return f"✅ Task '{tasks[0]['name']}' completato."


# ── ORDINI ────────────────────────────────────────────────────────────────────

@mcp.tool()
def ordini_in_attesa() -> str:
    """Elenca ordini email con stato in_attesa."""
    r = requests.get(f"{API_BASE}/OrdineEmail", headers=_headers(),
                     params={"maxSize": 1}, timeout=10)
    if r.status_code == 404:
        return "ℹ️ Entità OrdineEmail non ancora configurata."
    results = _search("OrdineEmail",
                      [{"type": "equals", "attribute": "stato", "value": "in_attesa"}],
                      select="id,emailDa,emailOggetto,emailData", max_size=20)
    if not results:
        return "✅ Nessun ordine in attesa."
    today = date.today()
    lines = [f"💰 Ordini in attesa ({len(results)}):"]
    for o in results:
        try:
            giorni = (today - datetime.strptime(o.get("emailData","")[:10], "%Y-%m-%d").date()).days
            data_str = f"{giorni}gg fa"
        except Exception:
            data_str = o.get("emailData","?")[:10]
        lines.append(f"• {o.get('emailDa','?')} | {o.get('emailOggetto','?')} | {data_str}")
    return "\n".join(lines)


@mcp.tool()
def briefing() -> str:
    """Briefing mattutino: task, ordini in attesa, top 5 clienti urgenti."""
    today = date.today()
    giorni_it = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
    mesi_it = ["","gennaio","febbraio","marzo","aprile","maggio","giugno",
               "luglio","agosto","settembre","ottobre","novembre","dicembre"]
    sezioni = [f"☀️ {giorni_it[today.weekday()]} {today.day} {mesi_it[today.month]} {today.year}\n"]

    today_str = today.isoformat()
    tasks = _search("Task", [
        {"type": "or", "value": [
            {"type": "equals", "attribute": "dateEnd", "value": today_str},
            {"type": "before", "attribute": "dateEnd", "value": today_str},
        ]},
        {"type": "notEquals", "attribute": "status", "value": "Completed"},
    ], select="name,dateEnd", max_size=10)

    if tasks:
        sezioni.append(f"📋 Task ({len(tasks)}):")
        for t in tasks:
            scad = t.get("dateEnd","")[:10]
            sezioni.append(f"  • {t['name']} {'⚠️' if scad < today_str else ''}")
    else:
        sezioni.append("📋 Nessun task in scadenza.")

    sezioni.append("\n" + ordini_in_attesa())

    all_clients = _search("Account", [],
                          select="name,zona,frequenzaVisitaGiorni,ultimaVisita", max_size=200)
    urgenti = []
    for c in all_clients:
        ultima = c.get("ultimaVisita")
        freq = int(c.get("frequenzaVisitaGiorni") or 30)
        try:
            ritardo = (today - datetime.strptime(ultima[:10], "%Y-%m-%d").date()).days - freq if ultima else 9999
        except Exception:
            ritardo = 9999
        if ritardo > 0:
            urgenti.append((ritardo, c))

    urgenti.sort(key=lambda x: -x[0])
    if urgenti[:5]:
        sezioni.append("\n📞 Da ricontattare:")
        for ritardo, c in urgenti[:5]:
            ultima = c.get("ultimaVisita")
            try:
                nota = f"{(today - datetime.strptime(ultima[:10],'%Y-%m-%d').date()).days}gg fa" if ultima else "mai 🆕"
            except Exception:
                nota = "?"
            sezioni.append(f"  • {c['name']} ({c.get('zona','—')}) — {nota}")
        zone: dict = {}
        for _, c in urgenti[:5]:
            z = (c.get("zona") or "").strip()
            if z: zone[z] = zone.get(z, 0) + 1
        if zone:
            zona_top = max(zone, key=lambda z: zone[z])
            sezioni.append(f"\n📍 Zona consigliata: {zona_top}")
    else:
        sezioni.append("\n📞 Tutti i clienti aggiornati ✅")

    return "\n".join(sezioni)


# ── CHIAMATE TASKER ───────────────────────────────────────────────────────────

@mcp.tool()
def log_chiamata_tasker(numero: str, durata_secondi: int = 0,
                        direzione: str = "Outbound", data: str = "") -> str:
    """Registra una chiamata da Tasker Android. numero: telefono, direzione: Outbound|Inbound."""
    d = data or date.today().isoformat()
    accounts = _search("Account", [{"type": "equals", "attribute": "phoneNumber", "value": numero}],
                       select="id,name", max_size=1)
    payload = {"name": f"Chiamata {direzione} {numero}", "dateStart": f"{d} 09:00:00",
               "duration": durata_secondi or 60, "status": "Held", "direction": direzione,
               "description": f"Da Tasker. Numero: {numero}"}
    if accounts:
        payload["parentType"] = "Account"
        payload["parentId"] = accounts[0]["id"]
        _patch("Account", accounts[0]["id"], {"ultimaChiamata": d})
        nome = accounts[0]["name"]
    else:
        nome = numero
    _post("Call", payload)
    return f"✅ Chiamata {direzione} con {nome} ({max(1, durata_secondi//60)} min) registrata."


# ── CONTATTI ─────────────────────────────────────────────────────────────────

@mcp.tool()
def aggiungi_contatto(nome_account: str, nome: str, cognome: str,
                      telefono: str = "", email: str = "", ruolo: str = "") -> str:
    """Aggiunge un contatto a un account esistente in EspoCRM."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_account}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Account '{nome_account}' non trovato."
    a = accounts[0]
    payload: dict = {"firstName": nome, "lastName": cognome, "accountId": a["id"]}
    if telefono: payload["phoneNumber"] = telefono
    if email: payload["emailAddress"] = email
    if ruolo: payload["title"] = ruolo
    result = _post("Contact", payload)
    return f"✅ Contatto '{nome} {cognome}' aggiunto a {a['name']}. ID: {result.get('id','?')}"


@mcp.tool()
def contatti_account(nome_account: str) -> str:
    """Mostra i contatti di un account."""
    accounts = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_account}],
                       select="id,name", max_size=1)
    if not accounts:
        return f"Account '{nome_account}' non trovato."
    contatti = _search("Contact",
                       [{"type": "equals", "attribute": "accountId", "value": accounts[0]["id"]}],
                       select="firstName,lastName,emailAddress,phoneNumber,title", max_size=20)
    if not contatti:
        return f"Nessun contatto per {accounts[0]['name']}."
    lines = [f"👤 Contatti {accounts[0]['name']}:"]
    for c in contatti:
        nome_c = f"{c.get('firstName','')} {c.get('lastName','')}".strip()
        ruolo = f" — {c['title']}" if c.get("title") else ""
        lines.append(f"  • {nome_c}{ruolo} | 📞 {c.get('phoneNumber','—')} | ✉️ {c.get('emailAddress','—')}")
    return "\n".join(lines)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
