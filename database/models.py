"""
Database models and schema for the email order processor.
Uses SQLite via the standard library.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "orders.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        -- Clienti (customers)
        CREATE TABLE IF NOT EXISTS clienti (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            codice      TEXT    UNIQUE NOT NULL,  -- internal code
            nome        TEXT    NOT NULL,
            email       TEXT,                     -- customer email (sender)
            azienda     TEXT,                     -- company name
            note        TEXT,
            creato_il   TEXT    DEFAULT (datetime('now'))
        );

        -- Articoli (items/products)
        CREATE TABLE IF NOT EXISTS articoli (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            codice      TEXT    UNIQUE NOT NULL,
            descrizione TEXT    NOT NULL,
            unita       TEXT    DEFAULT 'pz',     -- unit of measure
            note        TEXT
        );

        -- Listini prezzi per cliente (price lists per customer)
        CREATE TABLE IF NOT EXISTS listini (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id      INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
            articolo_id     INTEGER NOT NULL REFERENCES articoli(id) ON DELETE CASCADE,
            prezzo          REAL    NOT NULL,     -- price in EUR
            sconto_pct      REAL    DEFAULT 0,    -- discount %
            valido_dal      TEXT,                 -- valid from date (ISO)
            valido_al       TEXT,                 -- valid to date (ISO)
            UNIQUE(cliente_id, articolo_id)
        );

        -- Aziende destinatarie (companies to forward orders to)
        CREATE TABLE IF NOT EXISTS aziende (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            email       TEXT    NOT NULL,         -- forward orders here
            note        TEXT
        );

        -- Ordini estratti (extracted orders)
        CREATE TABLE IF NOT EXISTS ordini (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email_uid       TEXT    UNIQUE,       -- IMAP UID
            email_da        TEXT,
            email_oggetto   TEXT,
            email_data      TEXT,
            cliente_id      INTEGER REFERENCES clienti(id),
            azienda_id      INTEGER REFERENCES aziende(id),
            stato           TEXT    DEFAULT 'in_attesa',  -- in_attesa, confermato, rifiutato, inviato
            note_agente     TEXT,                -- AI extraction notes
            json_ordine     TEXT,                -- full extracted JSON
            creato_il       TEXT    DEFAULT (datetime('now')),
            aggiornato_il   TEXT    DEFAULT (datetime('now'))
        );

        -- Righe ordine (order lines)
        CREATE TABLE IF NOT EXISTS righe_ordine (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ordine_id       INTEGER NOT NULL REFERENCES ordini(id) ON DELETE CASCADE,
            codice_articolo TEXT,
            descrizione     TEXT    NOT NULL,
            quantita        REAL    NOT NULL DEFAULT 1,
            prezzo_ricevuto REAL,               -- price as in the email
            prezzo_corretto REAL,               -- price from our price list
            differenza      REAL,               -- prezzo_ricevuto - prezzo_corretto
            ok              INTEGER DEFAULT 0   -- 1 = price matches
        );

        -- Log Telegram (pending confirmations)
        CREATE TABLE IF NOT EXISTS telegram_pending (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ordine_id       INTEGER NOT NULL REFERENCES ordini(id) ON DELETE CASCADE,
            message_id      INTEGER,            -- Telegram message ID
            chat_id         INTEGER,
            creato_il       TEXT    DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database inizializzato: {DB_PATH}")


def init_pending_db() -> None:
    """
    Create only the telegram_pending table in SQLite.
    Used when EspoCRM is the main backend but we still need to track
    Telegram message IDs locally (transient internal state).
    The ordine_id column is TEXT to support both SQLite integer IDs
    and EspoCRM UUID string IDs.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telegram_pending (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ordine_id  TEXT    NOT NULL,
            message_id INTEGER,
            chat_id    INTEGER,
            creato_il  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
