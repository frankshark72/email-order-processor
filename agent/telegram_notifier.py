"""
Telegram bot notifier.

Sends order verification summaries to a Telegram chat with
inline keyboard buttons:
  ✅ Conferma & Invia   →  triggers email forwarding
  ✏️ Modifica prezzi    →  prompts user to edit (opens DB editor)
  ❌ Rifiuta           →  marks the order as rejected

Uses python-telegram-bot >= 20.x (async API).

Setup:
  1. Create a bot with @BotFather on Telegram → get TOKEN
  2. Send a message to your bot, then run:
       python -c "import requests; print(requests.get('https://api.telegram.org/bot<TOKEN>/getUpdates').json())"
     to find your CHAT_ID
  3. Add TOKEN and CHAT_ID to config.yaml
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)


# ── Callback data prefixes ────────────────────────────────────────────────────
# Format: "PREFIX:ordine_id"
CB_CONFERMA  = "CONFERMA"
CB_RIFIUTA   = "RIFIUTA"
CB_MODIFICA  = "MODIFICA"


# ── Inline keyboard ───────────────────────────────────────────────────────────

def _build_keyboard(ordine_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Conferma & Invia", callback_data=f"{CB_CONFERMA}:{ordine_id}"),
        ],
        [
            InlineKeyboardButton("✏️ Modifica prezzi",  callback_data=f"{CB_MODIFICA}:{ordine_id}"),
            InlineKeyboardButton("❌ Rifiuta",           callback_data=f"{CB_RIFIUTA}:{ordine_id}"),
        ],
    ])


# ── Send notification (one-shot, no polling) ──────────────────────────────────

async def invia_notifica_async(token: str, chat_id: int,
                                testo: str, ordine_id: int) -> int:
    """
    Send a notification message with inline buttons.
    Returns the Telegram message_id.
    """
    bot = Bot(token=token)
    msg = await bot.send_message(
        chat_id=chat_id,
        text=testo,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_build_keyboard(ordine_id),
    )
    return msg.message_id


def invia_notifica(token: str, chat_id: int, testo: str, ordine_id: int) -> int:
    """Synchronous wrapper around invia_notifica_async."""
    return asyncio.run(invia_notifica_async(token, chat_id, testo, ordine_id))


# ── Bot Application (long-running, handles callbacks) ────────────────────────

class OrderBot:
    """
    Long-running Telegram bot that handles button callbacks.

    Usage:
        bot = OrderBot(
            token="...",
            chat_id=12345678,
            on_conferma=handle_conferma,
            on_rifiuta=handle_rifiuta,
            on_modifica=handle_modifica,
        )
        bot.run()   # blocks until interrupted
    """

    def __init__(
        self,
        token: str,
        chat_id: int,
        on_conferma: Callable[[int], None],
        on_rifiuta:  Callable[[int], None],
        on_modifica: Optional[Callable[[int], None]] = None,
    ):
        self.token    = token
        self.chat_id  = int(chat_id)
        self.on_conferma = on_conferma
        self.on_rifiuta  = on_rifiuta
        self.on_modifica = on_modifica

    async def _callback_handler(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()

        data = query.data or ""
        if ":" not in data:
            return

        prefix, ordine_id_str = data.split(":", 1)
        try:
            ordine_id = int(ordine_id_str)
        except ValueError:
            return

        # Security: only react to messages in the authorised chat
        if query.message.chat_id != self.chat_id:
            await query.message.reply_text("⛔ Non autorizzato.")
            return

        if prefix == CB_CONFERMA:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"⏳ Invio ordine #{ordine_id} in corso…"
            )
            try:
                self.on_conferma(ordine_id)
                await query.message.reply_text(
                    f"✅ Ordine #{ordine_id} inviato con successo!"
                )
            except Exception as e:
                await query.message.reply_text(
                    f"❌ Errore invio ordine #{ordine_id}: {e}"
                )

        elif prefix == CB_RIFIUTA:
            await query.edit_message_reply_markup(reply_markup=None)
            try:
                self.on_rifiuta(ordine_id)
            except Exception as e:
                logger.error("Errore rifiuto ordine %s: %s", ordine_id, e)
            await query.message.reply_text(
                f"🗑️ Ordine #{ordine_id} rifiutato."
            )

        elif prefix == CB_MODIFICA:
            if self.on_modifica:
                try:
                    self.on_modifica(ordine_id)
                except Exception as e:
                    await query.message.reply_text(f"Errore: {e}")
                    return
            await query.message.reply_text(
                f"✏️ Per modificare i prezzi dell'ordine #{ordine_id}, "
                f"usa il comando:\n`python main.py modifica-prezzi {ordine_id}`",
                parse_mode=ParseMode.MARKDOWN,
            )

    async def _start_command(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "👋 Bot ordini attivo!\n"
            "Riceverai notifiche per ogni nuovo ordine estratto dalle email.\n"
            "Usa i bottoni per confermare o rifiutare gli ordini."
        )

    async def _status_command(self, update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("✅ Bot in esecuzione.")

    def run(self) -> None:
        """Start the bot (blocking)."""
        app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        app.add_handler(CommandHandler("start",  self._start_command))
        app.add_handler(CommandHandler("status", self._status_command))
        app.add_handler(CallbackQueryHandler(self._callback_handler))

        print(f"[TELEGRAM] Bot avviato. In ascolto su chat_id={self.chat_id}")
        app.run_polling(drop_pending_updates=True)


# ── Utility: send plain text message ─────────────────────────────────────────

async def _invia_testo_async(token: str, chat_id: int, testo: str) -> None:
    bot = Bot(token=token)
    await bot.send_message(
        chat_id=chat_id,
        text=testo,
        parse_mode=ParseMode.MARKDOWN,
    )


def invia_testo(token: str, chat_id: int, testo: str) -> None:
    asyncio.run(_invia_testo_async(token, chat_id, testo))
