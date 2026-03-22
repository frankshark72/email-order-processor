"""
Price checker module.

Given an extracted order and the sender's email, this module:
1. Identifies the customer in the database
2. For each order line, looks up the correct price from the price list
3. Compares the received price vs the expected price
4. Returns a detailed verification report
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from database import manager as db
from .order_extractor import OrdineEstratto, RigaOrdine


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RigaVerificata:
    riga: RigaOrdine
    prezzo_corretto: Optional[float]
    differenza: Optional[float]        # ricevuto - corretto (negativo = cliente ha messo meno)
    ok: bool
    motivo: str                        # explanation


@dataclass
class RapportoVerifica:
    cliente: Optional[dict]            # DB row or None if not found
    righe: list[RigaVerificata] = field(default_factory=list)
    prezzi_ok: bool = True
    prezzi_mancanti: int = 0           # lines with no price in DB
    prezzi_errati: int = 0             # lines with wrong price
    totale_ricevuto: float = 0.0
    totale_corretto: float = 0.0
    totale_differenza: float = 0.0
    avvisi: list[str] = field(default_factory=list)


# ── Price checker ─────────────────────────────────────────────────────────────

def verifica_ordine(ordine: OrdineEstratto,
                    sender_email: str,
                    data_ordine: str = None) -> RapportoVerifica:
    """
    Verify an extracted order against the database price list.

    Steps:
    1. Find the customer by email (sender) or by name/company from the order
    2. For each line: find the article, get the expected price, compare
    3. Build and return the RapportoVerifica
    """
    rapporto = RapportoVerifica(cliente=None)

    # --- 1. Find the customer ---
    cliente = _trova_cliente(ordine, sender_email)
    rapporto.cliente = cliente

    if not cliente:
        rapporto.avvisi.append(
            f"Cliente non trovato nel database "
            f"(email mittente: {sender_email}, "
            f"nome estratto: {ordine.cliente_nome or 'n/d'})"
        )

    # --- 2. Verify each line ---
    for riga in ordine.righe:
        rv = _verifica_riga(riga, cliente, data_ordine)
        rapporto.righe.append(rv)

        if riga.prezzo_unitario is not None:
            rapporto.totale_ricevuto += riga.prezzo_unitario * riga.quantita

        if rv.prezzo_corretto is not None:
            rapporto.totale_corretto += rv.prezzo_corretto * riga.quantita

        if not rv.ok:
            rapporto.prezzi_ok = False
            if rv.prezzo_corretto is None:
                rapporto.prezzi_mancanti += 1
            else:
                rapporto.prezzi_errati += 1

    rapporto.totale_differenza = round(
        rapporto.totale_ricevuto - rapporto.totale_corretto, 4
    )

    # Global warnings
    if rapporto.prezzi_errati > 0:
        rapporto.avvisi.append(
            f"ATTENZIONE: {rapporto.prezzi_errati} riga/e con prezzi errati"
        )
    if rapporto.prezzi_mancanti > 0:
        rapporto.avvisi.append(
            f"INFO: {rapporto.prezzi_mancanti} riga/e senza prezzo in listino"
        )
    if abs(rapporto.totale_differenza) > 0.01:
        diff_str = f"{'+'if rapporto.totale_differenza > 0 else ''}{rapporto.totale_differenza:.2f}"
        rapporto.avvisi.append(
            f"Differenza totale ordine: {diff_str} EUR"
        )

    return rapporto


# ── Private helpers ───────────────────────────────────────────────────────────

def _trova_cliente(ordine: OrdineEstratto, sender_email: str) -> Optional[dict]:
    """Try multiple strategies to find the customer."""

    # Strategy 1: by sender email
    c = db.get_cliente_by_email(sender_email)
    if c:
        return c

    # Strategy 2: by extracted email (if different from sender)
    if ordine.cliente_email and ordine.cliente_email.lower() != sender_email.lower():
        c = db.get_cliente_by_email(ordine.cliente_email)
        if c:
            return c

    # Strategy 3: by azienda
    if ordine.cliente_azienda:
        c = db.get_cliente_by_nome(ordine.cliente_azienda)
        if c:
            return c

    # Strategy 4: by customer name
    if ordine.cliente_nome:
        c = db.get_cliente_by_nome(ordine.cliente_nome)
        if c:
            return c

    return None


def _verifica_riga(riga: RigaOrdine, cliente: Optional[dict],
                   data_ordine: str = None) -> RigaVerificata:
    """Verify a single order line against the price list."""

    prezzo_corretto = None

    if cliente:
        cliente_id = cliente["id"]

        # Try to find the article by code first
        articolo = None
        if riga.codice:
            articolo = db.get_articolo_by_codice(riga.codice)

        # Fallback: search by description
        if not articolo and riga.descrizione:
            articolo = db.get_articolo_by_descrizione(riga.descrizione)

        if articolo:
            prezzo_corretto = db.get_prezzo(
                cliente_id, articolo["id"], data=data_ordine
            )

    # --- Comparison ---
    if riga.prezzo_unitario is None and prezzo_corretto is None:
        return RigaVerificata(
            riga=riga,
            prezzo_corretto=None,
            differenza=None,
            ok=True,
            motivo="Nessun prezzo nell'ordine né in listino",
        )

    if riga.prezzo_unitario is None and prezzo_corretto is not None:
        return RigaVerificata(
            riga=riga,
            prezzo_corretto=prezzo_corretto,
            differenza=None,
            ok=False,
            motivo=f"Prezzo mancante nell'ordine (listino: {prezzo_corretto:.2f} €)",
        )

    if riga.prezzo_unitario is not None and prezzo_corretto is None:
        if not cliente:
            motivo = "Cliente non in database, impossibile verificare il prezzo"
        else:
            motivo = "Articolo non trovato in listino"
        return RigaVerificata(
            riga=riga,
            prezzo_corretto=None,
            differenza=None,
            ok=False,
            motivo=motivo,
        )

    # Both prices available
    differenza = round(riga.prezzo_unitario - prezzo_corretto, 4)
    ok = abs(differenza) < 0.01   # tolerance: 1 cent

    if ok:
        motivo = f"Prezzo corretto ({prezzo_corretto:.2f} €)"
    elif differenza > 0:
        motivo = (
            f"Prezzo MAGGIORE del listino: {riga.prezzo_unitario:.2f} € "
            f"vs {prezzo_corretto:.2f} € (+{differenza:.2f} €)"
        )
    else:
        motivo = (
            f"Prezzo MINORE del listino: {riga.prezzo_unitario:.2f} € "
            f"vs {prezzo_corretto:.2f} € ({differenza:.2f} €)"
        )

    return RigaVerificata(
        riga=riga,
        prezzo_corretto=prezzo_corretto,
        differenza=differenza,
        ok=ok,
        motivo=motivo,
    )


# ── Text summary for Telegram ─────────────────────────────────────────────────

def format_rapporto_telegram(ordine: OrdineEstratto,
                              rapporto: RapportoVerifica,
                              msg_subject: str,
                              msg_from: str) -> str:
    """Format the verification report as a Telegram message."""
    lines = []

    # Header
    stato_emoji = "✅" if rapporto.prezzi_ok else "⚠️"
    lines.append(f"{stato_emoji} *NUOVO ORDINE DA VERIFICARE*")
    lines.append("")

    # Email info
    lines.append(f"📧 *Da:* `{msg_from}`")
    lines.append(f"📋 *Oggetto:* {msg_subject}")
    if ordine.data_ordine:
        lines.append(f"📅 *Data ordine:* {ordine.data_ordine}")
    lines.append("")

    # Customer
    if rapporto.cliente:
        nome = rapporto.cliente.get("nome", "")
        az   = rapporto.cliente.get("azienda", "")
        lines.append(f"👤 *Cliente:* {nome}" + (f" ({az})" if az else ""))
    else:
        nome_est = ordine.cliente_nome or ordine.cliente_azienda or "Sconosciuto"
        lines.append(f"👤 *Cliente:* {nome_est} _(non in database)_")
    lines.append("")

    # Order lines
    lines.append("📦 *RIGHE ORDINE:*")
    for rv in rapporto.righe:
        r = rv.riga
        qty_str = f"{r.quantita:.0f}" if r.quantita == int(r.quantita) else f"{r.quantita}"
        price_str = f"{r.prezzo_unitario:.2f} €" if r.prezzo_unitario is not None else "—"

        if rv.ok:
            icon = "✅"
        elif rv.prezzo_corretto is None:
            icon = "❓"
        else:
            icon = "❌"

        line = f"{icon} `{r.codice or '—'}` {r.descrizione}"
        line += f"\n    Qty: {qty_str} {r.unita} | Prezzo: {price_str}"
        if not rv.ok and rv.prezzo_corretto is not None:
            line += f" | Listino: {rv.prezzo_corretto:.2f} €"
        lines.append(line)

    lines.append("")

    # Totals
    if rapporto.totale_ricevuto > 0:
        lines.append(f"💰 *Totale ricevuto:* {rapporto.totale_ricevuto:.2f} €")
    if rapporto.totale_corretto > 0:
        lines.append(f"💰 *Totale listino:* {rapporto.totale_corretto:.2f} €")
    if abs(rapporto.totale_differenza) > 0.01:
        diff = rapporto.totale_differenza
        diff_str = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
        lines.append(f"⚡ *Differenza:* {diff_str} €")

    # Warnings from AI extraction
    if ordine.avvisi:
        lines.append("")
        lines.append("🤖 *Note AI:*")
        for av in ordine.avvisi:
            lines.append(f"  • {av}")

    # Warnings from price check
    if rapporto.avvisi:
        lines.append("")
        lines.append("⚠️ *Avvisi prezzi:*")
        for av in rapporto.avvisi:
            lines.append(f"  • {av}")

    if ordine.note:
        lines.append("")
        lines.append(f"📝 *Note:* {ordine.note}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Vuoi inviare questo ordine all'azienda?")

    return "\n".join(lines)
