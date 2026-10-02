"""
Notifications via OpenClaw (Telegram + WhatsApp).
Uses the openclaw CLI to send messages through configured channels.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def send_openclaw_message(channel: str, target: str, message: str) -> bool:
    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", channel,
                "--target", target,
                "--message", message,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("[%s] Message sent to %s", channel.upper(), target)
            return True
        else:
            logger.error("[%s] Send failed: %s", channel.upper(), result.stderr)
            return False
    except FileNotFoundError:
        logger.error("openclaw CLI not found")
        return False
    except subprocess.TimeoutExpired:
        logger.error("[%s] Send timed out", channel.upper())
        return False


def notify_telegram(target: str, message: str) -> bool:
    return send_openclaw_message("telegram", target, message)


def notify_whatsapp(target: str, message: str) -> bool:
    return send_openclaw_message("whatsapp", target, message)


def format_task_notification(
    categoria: str,
    oggetto: str,
    cliente: str,
    mandante: str,
    riassunto: str,
    azione: str,
    mailbox: str = "",
) -> str:
    EMOJI = {
        "ordine": "📦",
        "preventivo": "📋",
        "transito": "📨",
        "risposta": "📩",
        "informativa": "ℹ️",
        "altro": "📧",
    }
    emoji = EMOJI.get(categoria, "📧")
    tipo = categoria.upper()

    parts = [
        f"{emoji} *NUOVO TASK: {tipo}*",
        f"📌 {oggetto}",
    ]
    if cliente:
        parts.append(f"👤 Cliente: {cliente}")
    if mandante:
        parts.append(f"🏭 Mandante: {mandante}")
    if mailbox:
        parts.append(f"📬 Casella: {mailbox}")
    parts.append(f"\n{riassunto}")
    if azione:
        parts.append(f"\n➡️ *Azione:* {azione}")

    return "\n".join(parts)


class OpenClawNotifier:

    def __init__(self, telegram_target: str = None, whatsapp_target: str = None):
        self.telegram_target = telegram_target
        self.whatsapp_target = whatsapp_target

    def notify(self, message: str) -> None:
        if self.telegram_target:
            notify_telegram(self.telegram_target, message)
        if self.whatsapp_target:
            notify_whatsapp(self.whatsapp_target, message)

    def notify_new_task(
        self,
        categoria: str,
        oggetto: str,
        cliente: str = "",
        mandante: str = "",
        riassunto: str = "",
        azione: str = "",
        mailbox: str = "",
    ) -> None:
        msg = format_task_notification(
            categoria, oggetto, cliente, mandante, riassunto, azione, mailbox
        )
        self.notify(msg)


def notifier_from_config(cfg: dict) -> OpenClawNotifier:
    notify_cfg = cfg.get("notifications", {})
    return OpenClawNotifier(
        telegram_target=notify_cfg.get("telegram_target"),
        whatsapp_target=notify_cfg.get("whatsapp_target"),
    )
