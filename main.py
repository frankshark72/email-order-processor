#!/usr/bin/env python3
"""
Email Order Processor — Main Entry Point

Comandi disponibili:
  python main.py avvia          → Avvia il bot Telegram + polling email
  python main.py processa       → Elabora le email non lette (una sola volta)
  python main.py setup          → Wizard di configurazione guidato
  python main.py seed           → Inserisce dati di esempio nel database
  python main.py lista-clienti  → Mostra clienti nel database
  python main.py lista-articoli → Mostra articoli e listini
  python main.py lista-ordini   → Mostra ordini estratti
  python main.py modifica-prezzi <ordine_id> → Modifica prezzi interattivamente
  python main.py test-telegram  → Invia un messaggio di test su Telegram
  python main.py test-email     → Testa la connessione email
"""

from __future__ import annotations

import json
import os
import sys
import time
import threading
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# Add parent dir to path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

from database.models import init_db
from database import manager as db
from agent.email_reader import reader_from_config, get_sender_email
from agent.order_extractor import OrderExtractor
from agent.price_checker import verifica_ordine, format_rapporto_telegram
from agent.email_sender import sender_from_config, invia_ordine
from agent.espocrm_client import espocrm_from_config
from agent.telegram_notifier import (
    OrderBot, invia_notifica, invia_testo, SMTP_PRESETS
)


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config(path: str = None) -> dict:
    cfg_path = path or Path(__file__).parent / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Override with environment variables if set
    if os.environ.get("ANTHROPIC_API_KEY"):
        cfg.setdefault("anthropic", {})["api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        cfg.setdefault("telegram", {})["token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if os.environ.get("TELEGRAM_CHAT_ID"):
        cfg.setdefault("telegram", {})["chat_id"] = int(os.environ["TELEGRAM_CHAT_ID"])
    if os.environ.get("EMAIL_USERNAME"):
        cfg.setdefault("email", {})["username"] = os.environ["EMAIL_USERNAME"]
    if os.environ.get("EMAIL_PASSWORD"):
        cfg.setdefault("email", {})["password"] = os.environ["EMAIL_PASSWORD"]
    if os.environ.get("EMAIL_HOST"):
        cfg.setdefault("email", {})["host"] = os.environ["EMAIL_HOST"]
    if os.environ.get("SMTP_USERNAME"):
        cfg.setdefault("smtp", {})["username"] = os.environ["SMTP_USERNAME"]
    if os.environ.get("SMTP_PASSWORD"):
        cfg.setdefault("smtp", {})["password"] = os.environ["SMTP_PASSWORD"]
    if os.environ.get("SMTP_HOST"):
        cfg.setdefault("smtp", {})["host"] = os.environ["SMTP_HOST"]
    if os.environ.get("SMTP_FROM_NAME"):
        cfg.setdefault("smtp", {})["from_name"] = os.environ["SMTP_FROM_NAME"]
    if os.environ.get("ESPOCRM_URL"):
        cfg.setdefault("espocrm", {})["url"] = os.environ["ESPOCRM_URL"]
    if os.environ.get("ESPOCRM_API_KEY"):
        cfg.setdefault("espocrm", {})["api_key"] = os.environ["ESPOCRM_API_KEY"]

    return cfg


# ── Core processing pipeline ──────────────────────────────────────────────────

def processa_email(cfg: dict) -> int:
    """
    Check inbox, extract orders, verify prices, send Telegram notifications.
    Returns the number of new orders processed.
    """
    reader    = reader_from_config(cfg)
    extractor = OrderExtractor(api_key=cfg["anthropic"]["api_key"])
    tg_token  = cfg["telegram"]["token"]
    tg_chat   = int(cfg["telegram"]["chat_id"])
    ag_cfg    = cfg.get("agent", {})
    filtro    = ag_cfg.get("filtro_mittenti", [])

    processed = 0

    with reader:
        messages = reader.fetch_all_unread()

        for msg in messages:
            sender_email = get_sender_email(msg)

            # Apply sender filter if configured
            if filtro:
                allowed = any(
                    sender_email == f.lower() or sender_email.endswith(f.lower())
                    for f in filtro
                )
                if not allowed:
                    print(f"[SKIP] Email da {sender_email} non nel filtro mittenti")
                    continue

            # Skip already-processed emails
            if db.email_uid_esiste(msg.uid):
                print(f"[SKIP] Email UID {msg.uid} già elaborata")
                continue

            print(f"[PROCESSING] Email da {sender_email}: {msg.subject}")

            # 1. Extract order with Claude AI
            print("  → Estrazione ordine con Claude AI…")
            ordine = extractor.extract(msg)
            print(f"  → Estratte {len(ordine.righe)} righe | Confidenza: {ordine.confidenza}")

            if not ordine.righe:
                print("  → Nessuna riga ordine trovata, skip")
                continue

            # 2. Verify prices
            print("  → Verifica prezzi…")
            rapporto = verifica_ordine(ordine, sender_email, ordine.data_ordine)
            print(f"  → Prezzi ok: {rapporto.prezzi_ok} | Errati: {rapporto.prezzi_errati}")

            # 3. Find target company
            azienda = None
            if rapporto.cliente:
                # Use default azienda from config
                az_nome = ag_cfg.get("azienda_default", "")
                if az_nome:
                    aziende = db.get_all_aziende()
                    azienda = next((a for a in aziende if a["nome"] == az_nome), None)
            if not azienda:
                aziende = db.get_all_aziende()
                azienda = aziende[0] if aziende else None

            azienda_id = azienda["id"] if azienda else None

            # 4. Save order to DB
            ordine_id = db.crea_ordine(
                email_uid=msg.uid,
                email_da=msg.from_addr,
                email_oggetto=msg.subject,
                email_data=msg.date,
                cliente_id=rapporto.cliente["id"] if rapporto.cliente else None,
                azienda_id=azienda_id,
                note_agente="; ".join(ordine.avvisi + rapporto.avvisi) or None,
                json_ordine=json.dumps(ordine.raw_json, ensure_ascii=False),
            )

            for rv in rapporto.righe:
                db.aggiungi_riga(
                    ordine_id=ordine_id,
                    descrizione=rv.riga.descrizione,
                    quantita=rv.riga.quantita,
                    prezzo_ricevuto=rv.riga.prezzo_unitario,
                    prezzo_corretto=rv.prezzo_corretto,
                    codice_articolo=rv.riga.codice,
                )

            # 5. Send Telegram notification
            testo = format_rapporto_telegram(
                ordine, rapporto, msg.subject, msg.from_addr
            )
            print("  → Invio notifica Telegram…")
            tg_msg_id = invia_notifica(tg_token, tg_chat, testo, ordine_id)
            db.salva_pending(ordine_id, tg_msg_id, tg_chat)

            # 6. Mark email as read
            if ag_cfg.get("segna_come_letta", True):
                reader.mark_as_read(msg.uid)

            print(f"  ✅ Ordine #{ordine_id} salvato, notifica Telegram inviata")
            processed += 1

    return processed


# ── Callbacks for Telegram buttons ───────────────────────────────────────────

def _build_callbacks(cfg: dict):
    """Return (on_conferma, on_rifiuta) callback functions."""
    sender = sender_from_config(cfg)
    espocrm = espocrm_from_config(cfg)

    def on_conferma(ordine_id: int) -> None:
        ordine_row = db.get_ordine(ordine_id)
        if not ordine_row:
            raise ValueError(f"Ordine #{ordine_id} non trovato")

        # Get target company
        azienda = None
        if ordine_row["azienda_id"]:
            aziende = db.get_all_aziende()
            azienda = next((a for a in aziende if a["id"] == ordine_row["azienda_id"]), None)
        if not azienda:
            aziende = db.get_all_aziende()
            azienda = aziende[0] if aziende else None

        if not azienda:
            raise ValueError("Nessuna azienda destinataria configurata nel database")

        # Rebuild objects from DB
        from agent.order_extractor import OrdineEstratto, RigaOrdine
        from agent.price_checker import RapportoVerifica, RigaVerificata
        from agent.email_reader import EmailMessage

        righe_db = db.get_righe_ordine(ordine_id)

        righe_ordine = [
            RigaOrdine(
                descrizione=r["descrizione"],
                quantita=r["quantita"],
                prezzo_unitario=r["prezzo_ricevuto"],
                codice=r["codice_articolo"],
            )
            for r in righe_db
        ]

        righe_verificate = [
            RigaVerificata(
                riga=ro,
                prezzo_corretto=r["prezzo_corretto"],
                differenza=r["differenza"],
                ok=bool(r["ok"]),
                motivo="",
            )
            for ro, r in zip(righe_ordine, righe_db)
        ]

        totale_corretto = sum(
            (rv.prezzo_corretto or rv.riga.prezzo_unitario or 0) * rv.riga.quantita
            for rv in righe_verificate
        )

        ordine_est = OrdineEstratto(righe=righe_ordine)
        rapporto = RapportoVerifica(
            cliente=db.get_ordine(ordine_id),
            righe=righe_verificate,
            totale_corretto=totale_corretto,
        )

        # Build a minimal EmailMessage for forwarding
        email_msg = EmailMessage(
            uid=ordine_row["email_uid"] or "",
            from_addr=ordine_row["email_da"] or "",
            to_addr="",
            subject=ordine_row["email_oggetto"] or "",
            date=ordine_row["email_data"] or "",
            body_plain=ordine_row.get("json_ordine", ""),
            body_html="",
        )

        if espocrm:
            # Send via EspoCRM: create as Draft then call send action.
            # This ensures the email is actually delivered via SMTP,
            # not just stored as a record with status "Sent".
            from agent.email_sender import prepara_email_ordine
            subject, body = prepara_email_ordine(
                email_msg, ordine_est, rapporto, azienda["nome"]
            )
            smtp_cfg = cfg.get("smtp", cfg.get("email", {}))
            espocrm.create_and_send_email(
                to=azienda["email"],
                subject=subject,
                body=body,
                from_address=smtp_cfg.get("username"),
                from_name=smtp_cfg.get("from_name"),
            )
        else:
            # Fallback: send directly via SMTP
            invia_ordine(sender, email_msg, ordine_est, rapporto,
                         azienda["email"], azienda["nome"])
        db.aggiorna_stato_ordine(ordine_id, "inviato")
        db.rimuovi_pending(ordine_id)
        print(f"[ORDINE #{ordine_id}] Inviato a {azienda['email']}")

    def on_rifiuta(ordine_id: int) -> None:
        db.aggiorna_stato_ordine(ordine_id, "rifiutato")
        db.rimuovi_pending(ordine_id)
        print(f"[ORDINE #{ordine_id}] Rifiutato")

    return on_conferma, on_rifiuta


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_avvia(cfg: dict) -> None:
    """Start the Telegram bot + periodic email polling."""
    on_conferma, on_rifiuta = _build_callbacks(cfg)
    tg = cfg["telegram"]
    agent_cfg = cfg.get("agent", {})
    interval = int(agent_cfg.get("poll_interval_seconds", 120))

    def polling_loop():
        print(f"[POLLING] Controllo email ogni {interval}s")
        while True:
            try:
                n = processa_email(cfg)
                if n:
                    print(f"[POLLING] {n} nuovi ordini elaborati")
            except Exception as e:
                print(f"[POLLING ERROR] {e}")
            time.sleep(interval)

    # Start email polling in background thread
    t = threading.Thread(target=polling_loop, daemon=True)
    t.start()

    # Start Telegram bot (blocking)
    bot = OrderBot(
        token=tg["token"],
        chat_id=int(tg["chat_id"]),
        on_conferma=on_conferma,
        on_rifiuta=on_rifiuta,
    )
    bot.run()


def cmd_processa(cfg: dict) -> None:
    """Process unread emails once."""
    n = processa_email(cfg)
    print(f"\n✅ Elaborati {n} nuovi ordini")


def cmd_test_telegram(cfg: dict) -> None:
    """Send a test message on Telegram."""
    tg = cfg["telegram"]
    invia_testo(tg["token"], int(tg["chat_id"]),
                "✅ *Test connessione Telegram* — bot funzionante!")
    print("Messaggio di test inviato su Telegram.")


def cmd_test_email(cfg: dict) -> None:
    """Test IMAP connection."""
    reader = reader_from_config(cfg)
    with reader:
        uids = reader.get_unread_uids()
        print(f"✅ Connessione IMAP OK — {len(uids)} messaggi non letti")


def cmd_lista_clienti(cfg: dict) -> None:
    clienti = db.get_all_clienti()
    if not clienti:
        print("Nessun cliente nel database. Esegui: python main.py seed")
        return
    print(f"\n{'ID':<5} {'Codice':<10} {'Nome':<25} {'Email':<30} {'Azienda'}")
    print("─" * 90)
    for c in clienti:
        print(f"{c['id']:<5} {c['codice']:<10} {c['nome']:<25} "
              f"{c['email'] or '—':<30} {c['azienda'] or '—'}")


def cmd_lista_articoli(cfg: dict) -> None:
    articoli = db.get_all_articoli()
    if not articoli:
        print("Nessun articolo nel database.")
        return
    print(f"\n{'ID':<5} {'Codice':<10} {'Descrizione':<35} {'Unità'}")
    print("─" * 60)
    for a in articoli:
        print(f"{a['id']:<5} {a['codice']:<10} {a['descrizione']:<35} {a['unita']}")


def cmd_lista_ordini(cfg: dict) -> None:
    conn = __import__("database.models", fromlist=["get_connection"]).get_connection()
    rows = conn.execute("""
        SELECT o.id, o.email_da, o.email_oggetto, o.stato, o.creato_il,
               c.nome AS cliente_nome
        FROM ordini o
        LEFT JOIN clienti c ON c.id = o.cliente_id
        ORDER BY o.creato_il DESC
        LIMIT 20
    """).fetchall()
    conn.close()

    if not rows:
        print("Nessun ordine nel database.")
        return

    print(f"\n{'ID':<5} {'Stato':<12} {'Da':<30} {'Cliente':<20} {'Data'}")
    print("─" * 90)
    for r in rows:
        print(f"{r['id']:<5} {r['stato']:<12} {r['email_da']:<30} "
              f"{r['cliente_nome'] or '—':<20} {r['creato_il'][:16]}")


def cmd_seed(cfg: dict) -> None:
    from database.seed import seed
    seed()


# ── CLI entry point ───────────────────────────────────────────────────────────

COMMANDS = {
    "avvia":          cmd_avvia,
    "processa":       cmd_processa,
    "test-telegram":  cmd_test_telegram,
    "test-email":     cmd_test_email,
    "lista-clienti":  cmd_lista_clienti,
    "lista-articoli": cmd_lista_articoli,
    "lista-ordini":   cmd_lista_ordini,
    "seed":           cmd_seed,
}


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "setup":
        from setup.wizard import run_wizard
        run_wizard()
        return

    if cmd not in COMMANDS:
        print(f"Comando sconosciuto: {cmd}")
        print("Usa: python main.py help")
        sys.exit(1)

    # Init DB
    init_db()

    # Load config
    cfg_path = args[1] if len(args) > 1 and args[1].endswith(".yaml") else None
    try:
        cfg = load_config(cfg_path)
    except FileNotFoundError:
        print("❌ File config.yaml non trovato.")
        print("   Esegui prima: python main.py setup")
        sys.exit(1)

    COMMANDS[cmd](cfg)


if __name__ == "__main__":
    main()
