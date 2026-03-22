"""
Database CRUD operations for the email order processor.
"""

from __future__ import annotations

import json
from typing import Optional
from .models import get_connection


# ── Clienti ──────────────────────────────────────────────────────────────────

def get_cliente_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM clienti WHERE lower(email) = lower(?)", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_cliente_by_nome(nome: str) -> Optional[dict]:
    """Fuzzy search by name (LIKE)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM clienti WHERE lower(nome) LIKE lower(?) OR lower(azienda) LIKE lower(?)",
        (f"%{nome}%", f"%{nome}%")
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_clienti() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clienti ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_cliente(codice: str, nome: str, email: str = None,
                   azienda: str = None, note: str = None) -> int:
    conn = get_connection()
    conn.execute("""
        INSERT INTO clienti (codice, nome, email, azienda, note)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(codice) DO UPDATE SET
            nome    = excluded.nome,
            email   = excluded.email,
            azienda = excluded.azienda,
            note    = excluded.note
    """, (codice, nome, email, azienda, note))
    conn.commit()
    row = conn.execute("SELECT id FROM clienti WHERE codice = ?", (codice,)).fetchone()
    conn.close()
    return row["id"]


# ── Articoli ──────────────────────────────────────────────────────────────────

def get_articolo_by_codice(codice: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM articoli WHERE lower(codice) = lower(?)", (codice,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_articolo_by_descrizione(descrizione: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM articoli WHERE lower(descrizione) LIKE lower(?)",
        (f"%{descrizione}%",)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_articoli() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM articoli ORDER BY codice").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_articolo(codice: str, descrizione: str, unita: str = "pz",
                    note: str = None) -> int:
    conn = get_connection()
    conn.execute("""
        INSERT INTO articoli (codice, descrizione, unita, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(codice) DO UPDATE SET
            descrizione = excluded.descrizione,
            unita       = excluded.unita,
            note        = excluded.note
    """, (codice, descrizione, unita, note))
    conn.commit()
    row = conn.execute("SELECT id FROM articoli WHERE codice = ?", (codice,)).fetchone()
    conn.close()
    return row["id"]


# ── Listini ───────────────────────────────────────────────────────────────────

def get_prezzo(cliente_id: int, articolo_id: int,
               data: str = None) -> Optional[float]:
    """
    Return the price for a given customer/article pair.
    If data is provided, only return prices valid on that date.
    """
    conn = get_connection()
    query = """
        SELECT prezzo, sconto_pct FROM listini
        WHERE cliente_id = ? AND articolo_id = ?
    """
    params: list = [cliente_id, articolo_id]

    if data:
        query += """
          AND (valido_dal IS NULL OR valido_dal <= ?)
          AND (valido_al  IS NULL OR valido_al  >= ?)
        """
        params += [data, data]

    row = conn.execute(query, params).fetchone()
    conn.close()

    if not row:
        return None

    prezzo = row["prezzo"]
    sconto = row["sconto_pct"] or 0
    return round(prezzo * (1 - sconto / 100), 4)


def get_listino_cliente(cliente_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT l.*, a.codice AS articolo_codice, a.descrizione AS articolo_desc
        FROM listini l
        JOIN articoli a ON a.id = l.articolo_id
        WHERE l.cliente_id = ?
    """, (cliente_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_listino(cliente_id: int, articolo_id: int, prezzo: float,
                   sconto_pct: float = 0, valido_dal: str = None,
                   valido_al: str = None) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO listini (cliente_id, articolo_id, prezzo, sconto_pct, valido_dal, valido_al)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(cliente_id, articolo_id) DO UPDATE SET
            prezzo      = excluded.prezzo,
            sconto_pct  = excluded.sconto_pct,
            valido_dal  = excluded.valido_dal,
            valido_al   = excluded.valido_al
    """, (cliente_id, articolo_id, prezzo, sconto_pct, valido_dal, valido_al))
    conn.commit()
    conn.close()


# ── Aziende ───────────────────────────────────────────────────────────────────

def get_all_aziende() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM aziende ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_azienda(nome: str, email: str, note: str = None) -> int:
    conn = get_connection()
    conn.execute("""
        INSERT INTO aziende (nome, email, note)
        VALUES (?, ?, ?)
        ON CONFLICT DO NOTHING
    """, (nome, email, note))
    conn.commit()
    row = conn.execute("SELECT id FROM aziende WHERE nome = ?", (nome,)).fetchone()
    conn.close()
    return row["id"] if row else None


# ── Ordini ────────────────────────────────────────────────────────────────────

def crea_ordine(email_uid: str, email_da: str, email_oggetto: str,
                email_data: str, cliente_id: int = None,
                azienda_id: int = None, note_agente: str = None,
                json_ordine: str = None) -> int:
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO ordini
            (email_uid, email_da, email_oggetto, email_data,
             cliente_id, azienda_id, note_agente, json_ordine)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email_uid) DO NOTHING
    """, (email_uid, email_da, email_oggetto, email_data,
          cliente_id, azienda_id, note_agente, json_ordine))
    conn.commit()

    if cur.lastrowid:
        ordine_id = cur.lastrowid
    else:
        ordine_id = conn.execute(
            "SELECT id FROM ordini WHERE email_uid = ?", (email_uid,)
        ).fetchone()["id"]

    conn.close()
    return ordine_id


def aggiungi_riga(ordine_id: int, descrizione: str, quantita: float,
                  prezzo_ricevuto: float = None, prezzo_corretto: float = None,
                  codice_articolo: str = None) -> None:
    differenza = None
    ok = 0

    if prezzo_ricevuto is not None and prezzo_corretto is not None:
        differenza = round(prezzo_ricevuto - prezzo_corretto, 4)
        ok = 1 if abs(differenza) < 0.01 else 0

    conn = get_connection()
    conn.execute("""
        INSERT INTO righe_ordine
            (ordine_id, codice_articolo, descrizione, quantita,
             prezzo_ricevuto, prezzo_corretto, differenza, ok)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ordine_id, codice_articolo, descrizione, quantita,
          prezzo_ricevuto, prezzo_corretto, differenza, ok))
    conn.commit()
    conn.close()


def get_ordine(ordine_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM ordini WHERE id = ?", (ordine_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_righe_ordine(ordine_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM righe_ordine WHERE ordine_id = ?", (ordine_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def aggiorna_stato_ordine(ordine_id: int, stato: str) -> None:
    conn = get_connection()
    conn.execute("""
        UPDATE ordini SET stato = ?, aggiornato_il = datetime('now')
        WHERE id = ?
    """, (stato, ordine_id))
    conn.commit()
    conn.close()


def email_uid_esiste(uid: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM ordini WHERE email_uid = ?", (uid,)
    ).fetchone()
    conn.close()
    return row is not None


# ── Telegram pending ──────────────────────────────────────────────────────────

def salva_pending(ordine_id: int, message_id: int, chat_id: int) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO telegram_pending (ordine_id, message_id, chat_id)
        VALUES (?, ?, ?)
    """, (ordine_id, message_id, chat_id))
    conn.commit()
    conn.close()


def get_pending_by_ordine(ordine_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM telegram_pending WHERE ordine_id = ?", (ordine_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def rimuovi_pending(ordine_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM telegram_pending WHERE ordine_id = ?", (ordine_id,))
    conn.commit()
    conn.close()
