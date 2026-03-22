"""
Order extractor using Ollama (local LLM).

Given an email (body + attachments), extracts:
  - customer info (name, company, email)
  - ordered items (code, description, quantity, unit price)
  - delivery/shipping address
  - order date and notes

Works with:
  - Plain text emails
  - HTML emails
  - PDF attachments (via pdfplumber)
  - Excel/CSV attachments (via openpyxl / csv)

Requires Ollama running locally: https://ollama.com
Default model: mistral:7b
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

# Optional imports — only fail at usage time if not installed
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import openpyxl
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

from .email_reader import EmailMessage, Attachment


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RigaOrdine:
    descrizione: str
    quantita: float
    prezzo_unitario: Optional[float] = None
    codice: Optional[str] = None
    unita: str = "pz"
    note: Optional[str] = None


@dataclass
class OrdineEstratto:
    cliente_nome: Optional[str] = None
    cliente_azienda: Optional[str] = None
    cliente_email: Optional[str] = None
    data_ordine: Optional[str] = None
    note: Optional[str] = None
    righe: list[RigaOrdine] = field(default_factory=list)
    raw_json: dict = field(default_factory=dict)
    confidenza: str = "alta"   # alta / media / bassa
    avvisi: list[str] = field(default_factory=list)


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
Sei un assistente specializzato nell'estrazione di ordini da email commerciali in lingua italiana.

Il tuo compito è analizzare il contenuto di un'email (corpo e/o allegati) e restituire
un JSON strutturato con le informazioni dell'ordine.

Regole:
1. Restituisci SOLO il JSON, senza testo aggiuntivo, markdown o backtick.
2. Se un campo non è presente nell'email, usa null.
3. I prezzi devono essere numeri (float), non stringhe.
4. Le quantità devono essere numeri (float).
5. Indica la confidenza: "alta" se i dati sono chiari, "media" se ci sono ambiguità, "bassa" se stai ipotizzando.
6. In "avvisi" segnala qualsiasi anomalia: prezzi mancanti, quantità non chiare, articoli ambigui, ecc.

Schema JSON atteso:
{
  "cliente_nome": "string | null",
  "cliente_azienda": "string | null",
  "cliente_email": "string | null",
  "data_ordine": "YYYY-MM-DD | null",
  "note": "string | null",
  "confidenza": "alta | media | bassa",
  "avvisi": ["string"],
  "righe": [
    {
      "codice": "string | null",
      "descrizione": "string",
      "quantita": number,
      "unita": "pz | kg | mt | l | ...",
      "prezzo_unitario": number | null,
      "note": "string | null"
    }
  ]
}
""".strip()


# ── Extractor class ───────────────────────────────────────────────────────────

class OrderExtractor:
    """
    Uses a local Ollama model to extract structured order data from emails.
    Ollama must be running: https://ollama.com
    """

    def __init__(self, model: str = None, ollama_url: str = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "mistral:7b")
        self.ollama_url = (ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")

    def extract(self, msg: EmailMessage) -> OrdineEstratto:
        """Extract order information from an EmailMessage."""
        prompt_parts = []

        # --- Email body ---
        body = msg.body_plain or _strip_html(msg.body_html) or ""
        if body.strip():
            prompt_parts.append(f"=== CORPO EMAIL ===\nOggetto: {msg.subject}\nDa: {msg.from_addr}\nData: {msg.date}\n\n{body.strip()}")

        # --- Attachments ---
        for att in msg.attachments:
            text = _extract_attachment_text(att)
            if text:
                prompt_parts.append(f"=== ALLEGATO: {att.filename} ===\n{text}")

        if not prompt_parts:
            return OrdineEstratto(
                avvisi=["Email vuota, nessun contenuto da analizzare"],
                confidenza="bassa"
            )

        full_prompt = "\n\n".join(prompt_parts)

        # --- Call Ollama ---
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": full_prompt},
                    ],
                    "options": {"temperature": 0.1},
                },
                timeout=120,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return OrdineEstratto(
                avvisi=["Ollama non raggiungibile. Assicurati che sia in esecuzione: ollama serve"],
                confidenza="bassa"
            )
        except requests.exceptions.RequestException as e:
            return OrdineEstratto(
                avvisi=[f"Errore chiamata Ollama: {e}"],
                confidenza="bassa"
            )

        raw_text = response.json().get("message", {}).get("content", "").strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            data = _extract_json_from_text(raw_text)
            if not data:
                return OrdineEstratto(
                    avvisi=[f"Impossibile parsare la risposta del modello: {raw_text[:200]}"],
                    confidenza="bassa"
                )

        return _dict_to_ordine(data)

    def extract_batch(self, messages: list[EmailMessage]) -> list[tuple[EmailMessage, OrdineEstratto]]:
        """Extract orders from multiple emails."""
        results = []
        for msg in messages:
            try:
                ordine = self.extract(msg)
            except Exception as e:
                ordine = OrdineEstratto(
                    avvisi=[f"Errore durante l'estrazione: {e}"],
                    confidenza="bassa"
                )
            results.append((msg, ordine))
        return results


# ── Private helpers ───────────────────────────────────────────────────────────

def _extract_json_from_text(text: str) -> Optional[dict]:
    """Try to find and parse JSON inside a text string."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _dict_to_ordine(data: dict) -> OrdineEstratto:
    """Convert extracted JSON dict to OrdineEstratto dataclass."""
    righe = []
    for r in data.get("righe", []):
        righe.append(RigaOrdine(
            codice=r.get("codice"),
            descrizione=r.get("descrizione", ""),
            quantita=float(r.get("quantita", 1)),
            unita=r.get("unita", "pz"),
            prezzo_unitario=float(r["prezzo_unitario"]) if r.get("prezzo_unitario") is not None else None,
            note=r.get("note"),
        ))

    return OrdineEstratto(
        cliente_nome=data.get("cliente_nome"),
        cliente_azienda=data.get("cliente_azienda"),
        cliente_email=data.get("cliente_email"),
        data_ordine=data.get("data_ordine"),
        note=data.get("note"),
        confidenza=data.get("confidenza", "media"),
        avvisi=data.get("avvisi", []),
        righe=righe,
        raw_json=data,
    )


def _strip_html(html: str) -> str:
    """Very basic HTML stripper."""
    if not html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_attachment_text(att: Attachment) -> str:
    """Extract text from a PDF, Excel or CSV attachment."""
    fname = att.filename.lower()

    if fname.endswith(".pdf"):
        return _extract_pdf_text(att.data)
    elif fname.endswith((".xlsx", ".xls")):
        return _extract_excel_text(att.data)
    elif fname.endswith(".csv"):
        return _extract_csv_text(att.data)
    elif fname.endswith(".txt"):
        return att.data.decode("utf-8", errors="replace")

    return ""


def _extract_pdf_text(data: bytes) -> str:
    if not HAS_PDF:
        return "[Allegato PDF - installa pdfplumber per leggerlo: pip install pdfplumber]"
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except Exception as e:
        return f"[Errore lettura PDF: {e}]"


def _extract_excel_text(data: bytes) -> str:
    if not HAS_EXCEL:
        return "[Allegato Excel - installa openpyxl per leggerlo: pip install openpyxl]"
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for sheet in wb.worksheets:
            lines.append(f"[Foglio: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    lines.append("\t".join(str(c) if c is not None else "" for c in row))
        return "\n".join(lines)
    except Exception as e:
        return f"[Errore lettura Excel: {e}]"


def _extract_csv_text(data: bytes) -> str:
    import csv
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join("\t".join(row) for row in reader)
    except Exception as e:
        return f"[Errore lettura CSV: {e}]"
