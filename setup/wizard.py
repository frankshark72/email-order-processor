"""
Interactive setup wizard for the email order processor.
Run: python main.py setup
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure parent dir is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


IMAP_PRESETS = {
    "1": {"label": "Gmail",            "host": "imap.gmail.com",            "port": 993},
    "2": {"label": "Outlook/Office365","host": "outlook.office365.com",     "port": 993},
    "3": {"label": "Aruba",            "host": "imaps.aruba.it",            "port": 993},
    "4": {"label": "Libero",           "host": "mail.libero.it",            "port": 993},
    "5": {"label": "Tiscali",          "host": "mail.tiscali.it",           "port": 993},
    "6": {"label": "Altro (manuale)",  "host": "",                          "port": 993},
}

SMTP_PRESETS = {
    "1": {"label": "Gmail",            "host": "smtp.gmail.com",            "port": 587, "tls": True},
    "2": {"label": "Outlook/Office365","host": "smtp.office365.com",        "port": 587, "tls": True},
    "3": {"label": "Aruba",            "host": "smtps.aruba.it",            "port": 465, "ssl": True},
    "4": {"label": "Libero",           "host": "smtp.libero.it",            "port": 587, "tls": True},
    "5": {"label": "Stesso del IMAP",  "host": "__same__",                  "port": 587},
    "6": {"label": "Altro (manuale)",  "host": "",                          "port": 587},
}


def _ask(prompt: str, default: str = None) -> str:
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    value = input(full_prompt).strip()
    return value if value else (default or "")


def _ask_choice(prompt: str, choices: dict) -> str:
    print(f"\n{prompt}")
    for k, v in choices.items():
        print(f"  {k}) {v['label']}")
    while True:
        choice = input("Scelta: ").strip()
        if choice in choices:
            return choice
        print("Scelta non valida, riprova.")


def run_wizard():
    cfg_path = Path(__file__).parent.parent / "config.yaml"

    print("=" * 60)
    print("  EMAIL ORDER PROCESSOR — Setup guidato")
    print("=" * 60)
    print()
    print("Questo wizard creerà il file config.yaml.")
    print("Premi INVIO per accettare il valore predefinito.")
    print()

    # ── Email in entrata ─────────────────────────────────────────
    print("\n── 1. EMAIL IN ENTRATA (IMAP) ──────────────────────────")
    imap_choice = _ask_choice("Provider email:", IMAP_PRESETS)
    preset = IMAP_PRESETS[imap_choice]

    if imap_choice == "1":
        print()
        print("⚠️  GMAIL: devi usare un'App Password (non la password normale).")
        print("   Vai su: https://myaccount.google.com/apppasswords")
        print("   Crea una password per 'Posta' e usala qui sotto.")
        print()

    imap_host = preset["host"] or _ask("Host IMAP")
    imap_port = _ask("Porta IMAP", str(preset["port"]))
    imap_user = _ask("Email (username)")
    imap_pass = _ask("Password (o App Password)")

    # ── Email in uscita ──────────────────────────────────────────
    print("\n── 2. EMAIL IN USCITA (SMTP) ───────────────────────────")
    smtp_choice = _ask_choice("Provider SMTP:", SMTP_PRESETS)
    smtp_preset = SMTP_PRESETS[smtp_choice]

    if smtp_preset["host"] == "__same__":
        smtp_host = IMAP_PRESETS[imap_choice]["host"].replace("imap", "smtp")
        smtp_port = "587"
        smtp_tls  = True
        smtp_ssl  = False
        smtp_user = imap_user
        smtp_pass = imap_pass
    else:
        smtp_host = smtp_preset["host"] or _ask("Host SMTP")
        smtp_port = _ask("Porta SMTP", str(smtp_preset.get("port", 587)))
        smtp_tls  = smtp_preset.get("tls", True)
        smtp_ssl  = smtp_preset.get("ssl", False)
        smtp_user = _ask("Username SMTP", imap_user)
        if smtp_user == imap_user:
            smtp_pass = imap_pass
        else:
            smtp_pass = _ask("Password SMTP")

    from_name = _ask("Nome mittente (es. 'Il Mio Negozio')", smtp_user)

    # ── Telegram ──────────────────────────────────────────────────
    print("\n── 3. TELEGRAM BOT ─────────────────────────────────────")
    print("Per creare un bot:")
    print("  1. Apri Telegram e cerca @BotFather")
    print("  2. Invia il comando: /newbot")
    print("  3. Segui le istruzioni e copia il TOKEN che ti viene dato")
    print()
    tg_token = _ask("Token del bot Telegram")

    print()
    print("Per trovare il tuo Chat ID:")
    print("  1. Invia qualsiasi messaggio al tuo bot")
    print(f"  2. Apri: https://api.telegram.org/bot{tg_token}/getUpdates")
    print("  3. Cerca il numero 'id' dentro 'chat'")
    print()
    tg_chat_id = _ask("Il tuo Chat ID Telegram")

    # ── Anthropic API ─────────────────────────────────────────────
    print("\n── 4. CLAUDE AI (Anthropic) ────────────────────────────")
    print("Ottieni la chiave API da: https://console.anthropic.com")
    print()
    anthropic_key = _ask("Anthropic API Key")

    # ── Write config ──────────────────────────────────────────────
    config = f"""# Email Order Processor — Configurazione
# Generato dal wizard di setup

email:
  host: {imap_host}
  port: {imap_port}
  ssl: true
  username: {imap_user}
  password: "{imap_pass}"
  mailbox: INBOX
  filtro_mittenti: []

smtp:
  host: {smtp_host}
  port: {smtp_port}
  tls: {"true" if smtp_tls else "false"}
  ssl: {"true" if smtp_ssl else "false"}
  username: {smtp_user}
  password: "{smtp_pass}"
  from_name: "{from_name}"

telegram:
  token: "{tg_token}"
  chat_id: {tg_chat_id}

anthropic:
  api_key: "{anthropic_key}"
  model: "claude-opus-4-6"

agent:
  poll_interval_seconds: 120
  price_tolerance_eur: 0.01
  segna_come_letta: true
  notifica_sempre: true
  azienda_default: ""
"""

    cfg_path.write_text(config, encoding="utf-8")
    print(f"\n✅ Configurazione salvata in: {cfg_path}")

    # ── Init database & seed ──────────────────────────────────────
    print()
    do_seed = input("Vuoi inserire dati di esempio nel database? [S/n]: ").strip().lower()
    if do_seed != "n":
        from database.models import init_db
        from database.seed import seed
        init_db()
        seed()

    print()
    print("=" * 60)
    print("  Setup completato!")
    print("=" * 60)
    print()
    print("Prossimi passi:")
    print("  1. Aggiungi i tuoi clienti e listini:")
    print("       python main.py lista-clienti")
    print()
    print("  2. Testa la connessione Telegram:")
    print("       python main.py test-telegram")
    print()
    print("  3. Testa la connessione email:")
    print("       python main.py test-email")
    print()
    print("  4. Avvia l'agente:")
    print("       python main.py avvia")
    print()
