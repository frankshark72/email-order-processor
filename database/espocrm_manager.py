"""
EspoCRM backend manager.

Implements the same public interface as database/manager.py but stores
and retrieves data via EspoCRM REST API instead of SQLite.

Entity mapping (all names are configurable in config.yaml under espocrm.entities):

  SQLite table    | EspoCRM entity (default)
  ----------------+-------------------------
  clienti         | Account          (standard entity)
  articoli        | Prodotto         (custom entity)
  listini         | Listino          (custom entity)
  aziende         | Fornitore        (custom entity)
  ordini          | OrdineEmail      (custom entity)
  righe_ordine    | RigaOrdine       (custom entity)

The telegram_pending table is intentionally kept in SQLite (see manager.py)
because it is purely internal transient state (telegram message IDs).

Minimum required custom fields per entity — create these in EspoCRM Admin:

  Prodotto:
    cUnita        (varchar)  — unit of measure

  Listino:
    accountId     (link → Account)
    prodottoId    (link → Prodotto)
    prezzo        (float)
    scontoPct     (float, default 0)
    validoDal     (date, nullable)
    validoAl      (date, nullable)

  Fornitore:
    emailAddress  (email)

  OrdineEmail:
    emailUid      (varchar, unique) — IMAP UID for deduplication
    emailDa       (varchar)
    emailOggetto  (varchar)
    emailData     (varchar)
    accountId     (link → Account)
    fornitoreId   (link → Fornitore)
    stato         (enum: in_attesa, confermato, rifiutato, inviato)
    noteAgente    (text)
    jsonOrdine    (text)

  RigaOrdine:
    ordineEmailId (link → OrdineEmail)
    codiceArticolo(varchar)
    descrizione   (varchar)
    quantita      (float)
    prezzoRicevuto(float)
    prezzoCorretto(float)
    differenza    (float)
    ok            (bool)
"""

from __future__ import annotations

from typing import Optional
from datetime import date

from .espocrm_client import EspoCRMClient

# ── Module-level state ────────────────────────────────────────────────────────

_client: Optional[EspoCRMClient] = None

DEFAULT_ENTITIES = {
    "clienti":     "Account",
    "articoli":    "Prodotto",
    "listini":     "Listino",
    "aziende":     "Fornitore",
    "ordini":      "OrdineEmail",
    "righe_ordine": "RigaOrdine",
}

_entities: dict = dict(DEFAULT_ENTITIES)


def init(cfg: dict) -> None:
    """Initialise the EspoCRM client from the config block."""
    global _client, _entities
    _client = EspoCRMClient(
        url=cfg["url"],
        api_key=cfg.get("api_key"),
        username=cfg.get("username"),
        password=cfg.get("password"),
    )
    _entities = {**DEFAULT_ENTITIES, **cfg.get("entities", {})}
    print(f"[EspoCRM] Connesso a {cfg['url']}")


def _e(key: str) -> str:
    """Resolve entity name from config."""
    return _entities[key]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _account_to_cliente(row: dict) -> dict:
    """Map an EspoCRM Account record to the internal clienti dict."""
    return {
        "id":      row.get("id"),
        "codice":  row.get("name", ""),
        "nome":    row.get("name", ""),
        "email":   row.get("emailAddress") or row.get("emailAddressList", [{}])[0].get("emailAddress", "") if row.get("emailAddressList") else row.get("emailAddress", ""),
        "azienda": row.get("name", ""),
        "note":    row.get("description", ""),
    }


def _prodotto_to_articolo(row: dict) -> dict:
    return {
        "id":          row.get("id"),
        "codice":      row.get("name", ""),
        "descrizione": row.get("description", ""),
        "unita":       row.get("cUnita") or row.get("unita") or "pz",
    }


def _listino_row(row: dict) -> dict:
    return {
        "id":          row.get("id"),
        "cliente_id":  row.get("accountId"),
        "articolo_id": row.get("prodottoId"),
        "prezzo":      row.get("prezzo") or row.get("price") or 0.0,
        "sconto_pct":  row.get("scontoPct") or row.get("discountPercent") or 0.0,
        "valido_dal":  row.get("validoDal"),
        "valido_al":   row.get("validoAl"),
        "articolo_codice": row.get("prodottoName", ""),
        "articolo_desc":   row.get("prodottoName", ""),
    }


def _ordine_row(row: dict) -> dict:
    return {
        "id":            row.get("id"),
        "email_uid":     row.get("emailUid", ""),
        "email_da":      row.get("emailDa", ""),
        "email_oggetto": row.get("emailOggetto", ""),
        "email_data":    row.get("emailData", ""),
        "cliente_id":    row.get("accountId"),
        "azienda_id":    row.get("fornitoreId"),
        "stato":         row.get("stato", "in_attesa"),
        "note_agente":   row.get("noteAgente", ""),
        "json_ordine":   row.get("jsonOrdine", ""),
        "creato_il":     row.get("createdAt", ""),
        "aggiornato_il": row.get("modifiedAt", ""),
        # expose nested name fields too
        "nome":          row.get("accountName", ""),
        "azienda":       row.get("accountName", ""),
    }


def _riga_row(row: dict) -> dict:
    return {
        "id":              row.get("id"),
        "ordine_id":       row.get("ordineEmailId"),
        "codice_articolo": row.get("codiceArticolo", ""),
        "descrizione":     row.get("descrizione", ""),
        "quantita":        row.get("quantita") or 1.0,
        "prezzo_ricevuto": row.get("prezzoRicevuto"),
        "prezzo_corretto": row.get("prezzoCorretto"),
        "differenza":      row.get("differenza"),
        "ok":              1 if row.get("ok") else 0,
    }


# ── Clienti ───────────────────────────────────────────────────────────────────

def get_cliente_by_email(email: str) -> Optional[dict]:
    row = _client.search_one(_e("clienti"), "emailAddress", email)
    return _account_to_cliente(row) if row else None


def get_cliente_by_nome(nome: str) -> Optional[dict]:
    row = _client.search_like(_e("clienti"), "name", nome)
    return _account_to_cliente(row) if row else None


def get_all_clienti() -> list[dict]:
    rows = _client.get_list(_e("clienti"), order_by="name", max_size=200)
    return [_account_to_cliente(r) for r in rows]


def upsert_cliente(codice: str, nome: str, email: str = None,
                   azienda: str = None, note: str = None) -> str:
    existing = _client.search_one(_e("clienti"), "name", codice)
    payload = {
        "name":         azienda or nome or codice,
        "emailAddress": email or "",
        "description":  note or "",
    }
    if existing:
        _client.update(_e("clienti"), existing["id"], payload)
        return existing["id"]
    created = _client.create(_e("clienti"), payload)
    return created["id"]


# ── Articoli ──────────────────────────────────────────────────────────────────

def get_articolo_by_codice(codice: str) -> Optional[dict]:
    row = _client.search_one(_e("articoli"), "name", codice)
    return _prodotto_to_articolo(row) if row else None


def get_articolo_by_descrizione(descrizione: str) -> Optional[dict]:
    row = _client.search_like(_e("articoli"), "description", descrizione)
    return _prodotto_to_articolo(row) if row else None


def get_all_articoli() -> list[dict]:
    rows = _client.get_list(_e("articoli"), order_by="name", max_size=500)
    return [_prodotto_to_articolo(r) for r in rows]


def upsert_articolo(codice: str, descrizione: str, unita: str = "pz",
                    note: str = None) -> str:
    existing = _client.search_one(_e("articoli"), "name", codice)
    payload = {
        "name":        codice,
        "description": descrizione,
        "cUnita":      unita,
    }
    if existing:
        _client.update(_e("articoli"), existing["id"], payload)
        return existing["id"]
    created = _client.create(_e("articoli"), payload)
    return created["id"]


# ── Listini ───────────────────────────────────────────────────────────────────

def get_prezzo(cliente_id: str, articolo_id: str,
               data: str = None) -> Optional[float]:
    rows = _client.get_list(
        _e("listini"),
        where=[
            {"type": "equals", "field": "accountId",  "value": cliente_id},
            {"type": "equals", "field": "prodottoId", "value": articolo_id},
        ],
        max_size=10,
    )

    if not rows:
        return None

    today = data or str(date.today())
    valid = []
    for r in rows:
        dal = r.get("validoDal")
        al  = r.get("validoAl")
        if dal and dal > today:
            continue
        if al and al < today:
            continue
        valid.append(r)

    row = valid[0] if valid else rows[0]
    prezzo    = float(row.get("prezzo") or row.get("price") or 0)
    sconto    = float(row.get("scontoPct") or row.get("discountPercent") or 0)
    return round(prezzo * (1 - sconto / 100), 4)


def get_listino_cliente(cliente_id: str) -> list[dict]:
    rows = _client.get_list(
        _e("listini"),
        where=[{"type": "equals", "field": "accountId", "value": cliente_id}],
        max_size=500,
    )
    return [_listino_row(r) for r in rows]


def upsert_listino(cliente_id: str, articolo_id: str, prezzo: float,
                   sconto_pct: float = 0, valido_dal: str = None,
                   valido_al: str = None) -> None:
    rows = _client.get_list(
        _e("listini"),
        where=[
            {"type": "equals", "field": "accountId",  "value": cliente_id},
            {"type": "equals", "field": "prodottoId", "value": articolo_id},
        ],
        max_size=1,
    )
    payload = {
        "accountId":  cliente_id,
        "prodottoId": articolo_id,
        "prezzo":     prezzo,
        "scontoPct":  sconto_pct,
        "validoDal":  valido_dal,
        "validoAl":   valido_al,
    }
    if rows:
        _client.update(_e("listini"), rows[0]["id"], payload)
    else:
        _client.create(_e("listini"), payload)


# ── Aziende ───────────────────────────────────────────────────────────────────

def get_all_aziende() -> list[dict]:
    rows = _client.get_list(_e("aziende"), order_by="name", max_size=100)
    return [
        {
            "id":    r.get("id"),
            "nome":  r.get("name", ""),
            "email": r.get("emailAddress", ""),
            "note":  r.get("description", ""),
        }
        for r in rows
    ]


def upsert_azienda(nome: str, email: str, note: str = None) -> Optional[str]:
    existing = _client.search_one(_e("aziende"), "name", nome)
    payload = {
        "name":         nome,
        "emailAddress": email,
        "description":  note or "",
    }
    if existing:
        _client.update(_e("aziende"), existing["id"], payload)
        return existing["id"]
    created = _client.create(_e("aziende"), payload)
    return created["id"]


# ── Ordini ────────────────────────────────────────────────────────────────────

def crea_ordine(email_uid: str, email_da: str, email_oggetto: str,
                email_data: str, cliente_id: str = None,
                azienda_id: str = None, note_agente: str = None,
                json_ordine: str = None) -> str:
    # Check for duplicate first
    existing = _client.search_one(_e("ordini"), "emailUid", email_uid)
    if existing:
        return existing["id"]

    payload = {
        "emailUid":     email_uid,
        "emailDa":      email_da,
        "emailOggetto": email_oggetto,
        "emailData":    email_data,
        "accountId":    cliente_id,
        "fornitoreId":  azienda_id,
        "stato":        "in_attesa",
        "noteAgente":   note_agente or "",
        "jsonOrdine":   json_ordine or "",
    }
    created = _client.create(_e("ordini"), payload)
    return created["id"]


def aggiungi_riga(ordine_id: str, descrizione: str, quantita: float,
                  prezzo_ricevuto: float = None, prezzo_corretto: float = None,
                  codice_articolo: str = None) -> None:
    differenza = None
    ok = False

    if prezzo_ricevuto is not None and prezzo_corretto is not None:
        differenza = round(prezzo_ricevuto - prezzo_corretto, 4)
        ok = abs(differenza) < 0.01

    _client.create(_e("righe_ordine"), {
        "ordineEmailId":  ordine_id,
        "codiceArticolo": codice_articolo or "",
        "descrizione":    descrizione,
        "quantita":       quantita,
        "prezzoRicevuto": prezzo_ricevuto,
        "prezzoCorretto": prezzo_corretto,
        "differenza":     differenza,
        "ok":             ok,
    })


def get_ordine(ordine_id: str) -> Optional[dict]:
    row = _client.get(_e("ordini"), ordine_id)
    return _ordine_row(row) if row else None


def get_righe_ordine(ordine_id: str) -> list[dict]:
    rows = _client.get_list(
        _e("righe_ordine"),
        where=[{"type": "equals", "field": "ordineEmailId", "value": ordine_id}],
        max_size=200,
    )
    return [_riga_row(r) for r in rows]


def aggiorna_stato_ordine(ordine_id: str, stato: str) -> None:
    _client.update(_e("ordini"), ordine_id, {"stato": stato})


def email_uid_esiste(uid: str) -> bool:
    row = _client.search_one(_e("ordini"), "emailUid", uid)
    return row is not None


# ── Telegram pending (delegated to SQLite manager) ────────────────────────────
# These functions are intentionally NOT implemented here.
# The facade in manager.py always routes telegram_pending to SQLite.
