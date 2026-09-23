#!/usr/bin/env python3
"""
Email → Task Processor

Reads emails from configured IMAP mailboxes, classifies them with Claude AI,
creates tasks in EspoCRM, and sends notifications via Telegram + WhatsApp.

Commands:
  python process_tasks.py              → Process all mailboxes once
  python process_tasks.py loop         → Continuous polling (every N seconds)
  python process_tasks.py test         → Test connections (IMAP + EspoCRM + notifications)
  python process_tasks.py test-classify → Classify latest unread email without creating tasks
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config_tasks.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"❌ Config non trovato: {CONFIG_PATH}")
        print(f"   Copia config_tasks.example.yaml → config_tasks.yaml e compilalo")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_process(cfg: dict) -> None:
    from agent.task_processor import processor_from_config
    proc = processor_from_config(cfg)
    n = proc.process_all()
    print(f"\n✅ Processate {n} email → task creati in EspoCRM")


def cmd_loop(cfg: dict) -> None:
    from agent.task_processor import processor_from_config
    proc = processor_from_config(cfg)
    interval = cfg.get("agent", {}).get("poll_interval_seconds", 120)
    print(f"🔄 Polling ogni {interval} secondi. Ctrl+C per fermare.")

    while True:
        try:
            n = proc.process_all()
            if n:
                print(f"  → {n} nuovi task creati")
        except Exception as e:
            logger.error("Errore nel ciclo: %s", e)
        time.sleep(interval)


def cmd_test(cfg: dict) -> None:
    from agent.email_reader import IMAPReader
    from agent.espocrm_client import client_from_config
    from agent.openclaw_notifier import notifier_from_config

    print("=== Test connessioni ===\n")

    # Test IMAP
    for mb in cfg["mailboxes"]:
        label = mb.get("label", mb["username"])
        try:
            reader = IMAPReader(
                host=mb["host"], port=int(mb.get("port", 993)),
                username=mb["username"], password=mb["password"],
            )
            with reader:
                uids = reader.get_unread_uids()
                print(f"✅ IMAP {label}: {len(uids)} email non lette")
        except Exception as e:
            print(f"❌ IMAP {label}: {e}")

    # Test EspoCRM
    try:
        espo = client_from_config(cfg)
        users = espo.get_users()
        print(f"✅ EspoCRM: connesso ({len(users)} utenti attivi)")
    except Exception as e:
        print(f"❌ EspoCRM: {e}")

    # Test notifications
    notifier = notifier_from_config(cfg)
    if notifier.telegram_target:
        print(f"📱 Telegram target: {notifier.telegram_target}")
        notifier.notify("✅ Test notifica da Email→Task Processor")
        print("  → Messaggio di test inviato su Telegram")
    if notifier.whatsapp_target:
        print(f"📱 WhatsApp target: {notifier.whatsapp_target}")

    print("\n=== Test completato ===")


def cmd_test_classify(cfg: dict) -> None:
    from agent.email_reader import IMAPReader
    from agent.email_classifier import classifier_from_config
    import json

    classifier = classifier_from_config(cfg)
    mb = cfg["mailboxes"][0]
    label = mb.get("label", mb["username"])

    reader = IMAPReader(
        host=mb["host"], port=int(mb.get("port", 993)),
        username=mb["username"], password=mb["password"],
    )
    with reader:
        uids = reader.get_unread_uids()
        if not uids:
            print(f"Nessuna email non letta in {label}")
            return

        msg = reader.fetch_message(uids[-1])
        if not msg:
            print("Errore nel fetch del messaggio")
            return

        print(f"📧 Da: {msg.from_addr}")
        print(f"   Oggetto: {msg.subject}")
        print(f"   Data: {msg.date}\n")
        print("🤖 Classificazione in corso...\n")

        result = classifier.classify(msg, label)

        print(f"   Categoria:  {result.categoria}")
        print(f"   Priorità:   {result.priorita}")
        print(f"   Cliente:    {result.cliente_nome or '—'}")
        print(f"   Mandante:   {result.mandante or '—'}")
        print(f"   Riassunto:  {result.riassunto}")
        print(f"   Azione:     {result.azione_suggerita}")
        print(f"   Prodotti:   {', '.join(result.prodotti) if result.prodotti else '—'}")
        print(f"   Confidenza: {result.confidenza}")


def main():
    cfg = load_config()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "process"

    commands = {
        "process": cmd_process,
        "loop": cmd_loop,
        "test": cmd_test,
        "test-classify": cmd_test_classify,
    }

    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return

    if cmd not in commands:
        print(f"Comando sconosciuto: {cmd}")
        print(__doc__)
        sys.exit(1)

    commands[cmd](cfg)


if __name__ == "__main__":
    main()
