"""
Email reader via IMAP.
Supports Gmail, Outlook/Exchange and any generic IMAP server.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header
from typing import Optional


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes


@dataclass
class EmailMessage:
    uid: str
    from_addr: str
    to_addr: str
    subject: str
    date: str
    body_plain: str
    body_html: str
    attachments: list[Attachment] = field(default_factory=list)


# ── IMAP helper ───────────────────────────────────────────────────────────────

class IMAPReader:
    """
    Connects to an IMAP mailbox and fetches unread messages.

    Supported providers:
      - Gmail:   host=imap.gmail.com, port=993
      - Outlook: host=outlook.office365.com, port=993
      - Generic: any IMAP server with SSL

    For Gmail, use an App Password (not the main account password).
    Enable IMAP in Gmail settings first.
    """

    def __init__(self, host: str, port: int, username: str, password: str,
                 mailbox: str = "INBOX", use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.use_ssl = use_ssl
        self._conn: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        if self.use_ssl:
            context = ssl.create_default_context()
            self._conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
        else:
            self._conn = imaplib.IMAP4(self.host, self.port)

        self._conn.login(self.username, self.password)
        self._conn.select(self.mailbox)
        print(f"[EMAIL] Connesso a {self.host} come {self.username}")

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                self._conn.logout()
            except Exception:
                pass
        self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ── Fetching ──────────────────────────────────────────────────────────────

    def get_unread_uids(self) -> list[str]:
        """Return UIDs of unread (UNSEEN) messages."""
        _, data = self._conn.uid("search", None, "UNSEEN")
        if not data or not data[0]:
            return []
        return data[0].decode().split()

    def get_uids_since(self, since_date: datetime) -> list[str]:
        """Return UIDs of messages received since `since_date`."""
        date_str = since_date.strftime("%d-%b-%Y")
        _, data = self._conn.uid("search", None, f'SINCE "{date_str}"')
        if not data or not data[0]:
            return []
        return data[0].decode().split()

    def fetch_message(self, uid: str) -> Optional[EmailMessage]:
        """Fetch and parse a single message by UID."""
        _, data = self._conn.uid("fetch", uid, "(RFC822)")
        if not data or not data[0]:
            return None

        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        return EmailMessage(
            uid=uid,
            from_addr=_decode_header_str(msg.get("From", "")),
            to_addr=_decode_header_str(msg.get("To", "")),
            subject=_decode_header_str(msg.get("Subject", "(nessun oggetto)")),
            date=msg.get("Date", ""),
            body_plain=_extract_body(msg, "text/plain"),
            body_html=_extract_body(msg, "text/html"),
            attachments=_extract_attachments(msg),
        )

    def mark_as_read(self, uid: str) -> None:
        self._conn.uid("store", uid, "+FLAGS", "\\Seen")

    def fetch_all_unread(self) -> list[EmailMessage]:
        """Fetch all unread messages and return parsed EmailMessage list."""
        uids = self.get_unread_uids()
        messages = []
        for uid in uids:
            msg = self.fetch_message(uid)
            if msg:
                messages.append(msg)
        print(f"[EMAIL] {len(messages)} messaggi non letti trovati")
        return messages


# ── Private helpers ───────────────────────────────────────────────────────────

def _decode_header_str(value: str) -> str:
    """Decode MIME-encoded header values."""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg: email.message.Message, content_type: str) -> str:
    """Extract body of a given content type from the message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == content_type:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace") if payload else ""
    else:
        if msg.get_content_type() == content_type:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace") if payload else ""
    return ""


def _extract_attachments(msg: email.message.Message) -> list[Attachment]:
    """Extract all attachments from the message."""
    attachments = []
    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in content_disposition:
            continue

        filename = part.get_filename()
        if not filename:
            continue

        filename = _decode_header_str(filename)
        data = part.get_payload(decode=True)
        if data:
            attachments.append(Attachment(
                filename=filename,
                content_type=part.get_content_type(),
                data=data,
            ))

    return attachments


def _extract_email_address(full_addr: str) -> str:
    """Extract plain email address from 'Name <email>' format."""
    match = re.search(r"<([^>]+)>", full_addr)
    if match:
        return match.group(1).strip().lower()
    return full_addr.strip().lower()


def get_sender_email(msg: EmailMessage) -> str:
    return _extract_email_address(msg.from_addr)


# ── Factory from config ───────────────────────────────────────────────────────

def reader_from_config(cfg: dict) -> IMAPReader:
    """
    Build an IMAPReader from a config dict:

        email:
          host: imap.gmail.com
          port: 993
          username: tu@gmail.com
          password: app_password
          mailbox: INBOX
    """
    ec = cfg["email"]
    return IMAPReader(
        host=ec["host"],
        port=int(ec.get("port", 993)),
        username=ec["username"],
        password=ec["password"],
        mailbox=ec.get("mailbox", "INBOX"),
        use_ssl=ec.get("ssl", True),
    )


# ── Provider presets ──────────────────────────────────────────────────────────

IMAP_PRESETS = {
    "gmail":   {"host": "imap.gmail.com",             "port": 993},
    "outlook": {"host": "outlook.office365.com",      "port": 993},
    "yahoo":   {"host": "imap.mail.yahoo.com",        "port": 993},
    "aruba":   {"host": "imaps.aruba.it",             "port": 993},
    "libero":  {"host": "mail.libero.it",             "port": 993},
    "tiscali": {"host": "mail.tiscali.it",            "port": 993},
}
