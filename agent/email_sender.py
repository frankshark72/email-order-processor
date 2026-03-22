"""
Email sender module.

Forwards a confirmed order to the target company via SMTP.
The forwarded email is sent FROM your own address TO the company,
with the original email attached or quoted in the body.

Supports:
  - Gmail SMTP (with App Password)
  - Outlook/Exchange SMTP
  - Generic SMTP with TLS
"""

from __future__ import annotations

import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .email_reader import EmailMessage
from .order_extractor import OrdineEstratto
from .price_checker import RapportoVerifica


# ── SMTP presets ──────────────────────────────────────────────────────────────

SMTP_PRESETS = {
    "gmail":   {"host": "smtp.gmail.com",             "port": 587, "tls": True},
    "outlook": {"host": "smtp.office365.com",          "port": 587, "tls": True},
    "aruba":   {"host": "smtps.aruba.it",              "port": 465, "ssl": True},
    "libero":  {"host": "smtp.libero.it",              "port": 587, "tls": True},
    "tiscali": {"host": "smtp.tiscali.it",             "port": 587, "tls": True},
}


# ── EmailSender class ─────────────────────────────────────────────────────────

class EmailSender:
    """
    Sends emails via SMTP.

    smtp:
      host: smtp.gmail.com
      port: 587
      username: tu@gmail.com
      password: app_password
      from_name: "Il Mio Negozio"
    """

    def __init__(self, host: str, port: int, username: str, password: str,
                 from_name: str = None, use_tls: bool = True, use_ssl: bool = False):
        self.host      = host
        self.port      = port
        self.username  = username
        self.password  = password
        self.from_name = from_name or username
        self.use_tls   = use_tls
        self.use_ssl   = use_ssl

    def invia(self, to: str, subject: str, body: str,
              cc: list[str] = None, attachments: list[tuple[str, bytes]] = None) -> None:
        """
        Send an email.

        Args:
            to: recipient email address
            subject: email subject
            body: plain text body
            cc: optional CC list
            attachments: list of (filename, data) tuples
        """
        msg = MIMEMultipart("mixed")
        msg["From"]    = f"{self.from_name} <{self.username}>"
        msg["To"]      = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        # Body
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attachments
        for filename, data in (attachments or []):
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )
            msg.attach(part)

        recipients = [to] + (cc or [])
        raw = msg.as_bytes()

        if self.use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.host, self.port, context=ctx) as server:
                server.login(self.username, self.password)
                server.sendmail(self.username, recipients, raw)
        else:
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls(context=ssl.create_default_context())
                server.login(self.username, self.password)
                server.sendmail(self.username, recipients, raw)

        print(f"[EMAIL INVIATA] A: {to} | Oggetto: {subject}")


# ── Order forwarding ──────────────────────────────────────────────────────────

def prepara_email_ordine(
    original_msg: EmailMessage,
    ordine: OrdineEstratto,
    rapporto: RapportoVerifica,
    azienda_nome: str,
) -> tuple[str, str]:
    """
    Build the subject and body for the forwarded order email.
    Returns (subject, body).
    """
    subject = f"ORDINE: {original_msg.subject}"

    cliente_str = ""
    if rapporto.cliente:
        c = rapporto.cliente
        cliente_str = f"{c.get('nome', '')} ({c.get('azienda', '')})"
    elif ordine.cliente_nome or ordine.cliente_azienda:
        cliente_str = f"{ordine.cliente_nome or ''} {ordine.cliente_azienda or ''}".strip()
    else:
        cliente_str = original_msg.from_addr

    lines = [
        f"Gentile {azienda_nome},",
        "",
        "Si trasmette il seguente ordine ricevuto via email:",
        "",
        f"  Da:     {original_msg.from_addr}",
        f"  Data:   {original_msg.date}",
        f"  Oggetto: {original_msg.subject}",
        f"  Cliente: {cliente_str}",
        "",
        "═══════════════════════════════════════",
        "DETTAGLIO ORDINE",
        "═══════════════════════════════════════",
    ]

    for rv in rapporto.righe:
        r = rv.riga
        qty  = f"{r.quantita:.0f}" if r.quantita == int(r.quantita) else f"{r.quantita}"
        codice_str = f"[{r.codice}] " if r.codice else ""
        prezzo_str = f"{rv.prezzo_corretto:.2f} €" if rv.prezzo_corretto is not None else \
                     (f"{r.prezzo_unitario:.2f} €" if r.prezzo_unitario is not None else "—")
        totale = (rv.prezzo_corretto or r.prezzo_unitario or 0) * r.quantita
        totale_str = f"{totale:.2f} €" if (rv.prezzo_corretto or r.prezzo_unitario) else "—"

        lines.append(
            f"  {codice_str}{r.descrizione}"
            f"\n    Qty: {qty} {r.unita} | Prezzo: {prezzo_str} | Totale: {totale_str}"
        )

    if rapporto.totale_corretto > 0:
        lines += [
            "",
            "───────────────────────────────────────",
            f"  TOTALE ORDINE: {rapporto.totale_corretto:.2f} €",
            "───────────────────────────────────────",
        ]

    if ordine.note:
        lines += ["", f"NOTE: {ordine.note}"]

    lines += [
        "",
        "═══════════════════════════════════════",
        "TESTO ORIGINALE EMAIL",
        "═══════════════════════════════════════",
        original_msg.body_plain or "(corpo email non disponibile)",
    ]

    return subject, "\n".join(lines)


def invia_ordine(
    sender: EmailSender,
    original_msg: EmailMessage,
    ordine: OrdineEstratto,
    rapporto: RapportoVerifica,
    azienda_email: str,
    azienda_nome: str,
) -> None:
    """
    Forward a confirmed order to the target company.
    Also re-attaches any attachments from the original email.
    """
    subject, body = prepara_email_ordine(original_msg, ordine, rapporto, azienda_nome)

    attachments = [
        (att.filename, att.data) for att in original_msg.attachments
    ]

    sender.invia(
        to=azienda_email,
        subject=subject,
        body=body,
        attachments=attachments if attachments else None,
    )


# ── Factory from config ───────────────────────────────────────────────────────

def sender_from_config(cfg: dict) -> EmailSender:
    """
    Build an EmailSender from a config dict:

        smtp:
          host: smtp.gmail.com
          port: 587
          username: tu@gmail.com
          password: app_password
          from_name: "Il Mio Negozio"
          tls: true
    """
    sc = cfg.get("smtp", cfg.get("email", {}))
    return EmailSender(
        host=sc["host"],
        port=int(sc.get("port", 587)),
        username=sc["username"],
        password=sc["password"],
        from_name=sc.get("from_name", sc["username"]),
        use_tls=sc.get("tls", True),
        use_ssl=sc.get("ssl", False),
    )
