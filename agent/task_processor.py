"""
Main email-to-task processing pipeline.

Reads emails from multiple IMAP mailboxes, classifies them with AI,
creates tasks in EspoCRM, and sends notifications via OpenClaw.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .email_reader import IMAPReader, EmailMessage, get_sender_email
from .email_classifier import EmailClassifier, EmailClassification
from .espocrm_client import EspoCRMClient
from .openclaw_notifier import OpenClawNotifier

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "processed_emails.db"


def _init_tracking_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mailbox     TEXT NOT NULL,
            uid         TEXT NOT NULL,
            from_addr   TEXT,
            subject     TEXT,
            categoria   TEXT,
            task_id     TEXT,
            processed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(mailbox, uid)
        )
    """)
    conn.commit()
    conn.close()


def _is_processed(mailbox: str, uid: str) -> bool:
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT 1 FROM processed_emails WHERE mailbox = ? AND uid = ?",
        (mailbox, uid),
    ).fetchone()
    conn.close()
    return row is not None


def _mark_processed(mailbox: str, uid: str, from_addr: str,
                    subject: str, categoria: str, task_id: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT OR IGNORE INTO processed_emails
           (mailbox, uid, from_addr, subject, categoria, task_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (mailbox, uid, from_addr, subject, categoria, task_id),
    )
    conn.commit()
    conn.close()


TASK_NAME_TEMPLATES = {
    "ordine": "[ORD] Ordine da {cliente} - {oggetto}",
    "preventivo": "[PREV] Preventivo per {cliente} - {oggetto}",
    "transito": "[TRANS] Ordine in transito - {oggetto}",
    "risposta": "[RISP] Risposta {mandante} - {oggetto}",
    "informativa": "[INFO] Info - {oggetto}",
    "altro": "[EMAIL] Email - {oggetto}",
}

PRIORITY_MAP = {
    "alta": "Urgent",
    "normale": "Normal",
    "bassa": "Low",
}

SKIP_CATEGORIES = {"informativa"}


class TaskProcessor:

    def __init__(
        self,
        mailboxes: list[dict],
        classifier: EmailClassifier,
        espocrm: EspoCRMClient,
        notifier: OpenClawNotifier,
        skip_informativa: bool = True,
        mark_as_read: bool = True,
    ):
        self.mailboxes = mailboxes
        self.classifier = classifier
        self.espocrm = espocrm
        self.notifier = notifier
        self.skip_informativa = skip_informativa
        self.mark_as_read = mark_as_read
        _init_tracking_db()

    def process_all(self) -> int:
        total = 0
        for mb in self.mailboxes:
            try:
                n = self._process_mailbox(mb)
                total += n
            except Exception as e:
                logger.error("Error processing mailbox %s: %s", mb["username"], e)
        return total

    def _process_mailbox(self, mb: dict) -> int:
        reader = IMAPReader(
            host=mb["host"],
            port=int(mb.get("port", 993)),
            username=mb["username"],
            password=mb["password"],
            mailbox=mb.get("mailbox", "INBOX"),
        )
        mailbox_label = mb.get("label", mb["username"])
        processed = 0

        with reader:
            messages = reader.fetch_all_unread()
            for msg in messages:
                if _is_processed(mailbox_label, msg.uid):
                    continue

                try:
                    task_id = self._process_message(msg, mailbox_label, reader)
                    if task_id is not None:
                        processed += 1
                except Exception as e:
                    logger.error("Error processing email %s: %s", msg.uid, e)

        return processed

    def _process_message(self, msg: EmailMessage, mailbox: str,
                         reader: IMAPReader) -> Optional[str]:
        logger.info("[%s] Classifying: %s", mailbox, msg.subject)
        classification = self.classifier.classify(msg, mailbox)

        if self.skip_informativa and classification.categoria in SKIP_CATEGORIES:
            logger.info("[%s] Skipping informativa: %s", mailbox, msg.subject)
            _mark_processed(mailbox, msg.uid, msg.from_addr,
                            msg.subject, classification.categoria, "")
            if self.mark_as_read:
                reader.mark_as_read(msg.uid)
            return ""

        cliente = classification.cliente_nome or get_sender_email(msg)
        mandante = classification.mandante or ""
        oggetto = classification.oggetto_breve or msg.subject[:60]

        template = TASK_NAME_TEMPLATES.get(
            classification.categoria, TASK_NAME_TEMPLATES["altro"]
        )
        task_name = template.format(
            cliente=cliente, mandante=mandante, oggetto=oggetto
        )

        description_parts = [
            f"**Classificazione:** {classification.categoria}",
            f"**Casella:** {mailbox}",
            f"**Da:** {msg.from_addr}",
            f"**Oggetto:** {msg.subject}",
            f"**Data:** {msg.date}",
            "",
            f"**Riassunto:** {classification.riassunto}",
            "",
            f"**Azione suggerita:** {classification.azione_suggerita}",
        ]
        if classification.prodotti:
            description_parts.append(f"\n**Prodotti:** {', '.join(classification.prodotti)}")
        if classification.mandante:
            description_parts.append(f"**Mandante:** {classification.mandante}")

        description = "\n".join(description_parts)

        account_id = None
        try:
            if classification.cliente_email:
                account = self.espocrm.find_account_by_email(classification.cliente_email)
                if account:
                    account_id = account["id"]
            if not account_id and classification.cliente_nome:
                account = self.espocrm.find_account_by_name(classification.cliente_nome)
                if account:
                    account_id = account["id"]
        except Exception as e:
            logger.warning("Account lookup failed, continuing without: %s", e)

        try:
            task_id = self.espocrm.create_task(
                name=task_name[:150],
                description=description,
                priority=PRIORITY_MAP.get(classification.priorita, "Normal"),
                account_id=account_id,
            )
        except Exception as e:
            logger.error("Task creation failed: %s", e)
            _mark_processed(mailbox, msg.uid, msg.from_addr,
                            msg.subject, classification.categoria, "ERROR")
            return None

        logger.info("[%s] Created Task %s: %s", mailbox, task_id, task_name)

        try:
            self.notifier.notify_new_task(
                categoria=classification.categoria,
                oggetto=oggetto,
                cliente=cliente,
                mandante=mandante,
                riassunto=classification.riassunto,
                azione=classification.azione_suggerita,
                mailbox=mailbox,
            )
        except Exception as e:
            logger.warning("Notification failed: %s", e)

        _mark_processed(mailbox, msg.uid, msg.from_addr,
                        msg.subject, classification.categoria, task_id)

        if self.mark_as_read:
            reader.mark_as_read(msg.uid)

        return task_id


def processor_from_config(cfg: dict) -> TaskProcessor:
    from .email_classifier import classifier_from_config
    from .espocrm_client import client_from_config
    from .openclaw_notifier import notifier_from_config

    return TaskProcessor(
        mailboxes=cfg["mailboxes"],
        classifier=classifier_from_config(cfg),
        espocrm=client_from_config(cfg),
        notifier=notifier_from_config(cfg),
        skip_informativa=cfg.get("agent", {}).get("skip_informativa", True),
        mark_as_read=cfg.get("agent", {}).get("segna_come_letta", True),
    )
