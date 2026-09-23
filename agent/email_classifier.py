"""
Email classifier using Anthropic Claude API.

Classifies incoming emails into actionable categories:
  - ordine:       Client order to process
  - preventivo:   Quote/estimate request
  - transito:     Order in transit (CC copy)
  - risposta:     Response from mandante/supplier
  - informativa:  Informational, no action needed
  - altro:        Other / unclear

Also extracts key metadata: client name, mandante, urgency, summary.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

from .email_reader import EmailMessage

logger = logging.getLogger(__name__)


@dataclass
class EmailClassification:
    categoria: str  # ordine, preventivo, transito, risposta, informativa, altro
    priorita: str   # alta, normale, bassa
    cliente_nome: Optional[str] = None
    cliente_email: Optional[str] = None
    mandante: Optional[str] = None
    oggetto_breve: str = ""
    riassunto: str = ""
    azione_suggerita: str = ""
    prodotti: list[str] = field(default_factory=list)
    confidenza: str = "alta"
    raw_json: dict = field(default_factory=dict)


_SYSTEM_PROMPT = """Sei un assistente per un agente di commercio italiano (FC Rappresentanze).
L'agente rappresenta diverse aziende mandanti e riceve email da clienti e mandanti.

Analizza l'email e restituisci SOLO un JSON (nessun testo aggiuntivo, nessun markdown) con questa struttura:

{
  "categoria": "ordine | preventivo | transito | risposta | informativa | altro",
  "priorita": "alta | normale | bassa",
  "cliente_nome": "nome del cliente o azienda cliente (null se non identificabile)",
  "cliente_email": "email del cliente (null se non identificabile)",
  "mandante": "nome dell'azienda mandante/fornitore coinvolta (null se non chiaro)",
  "oggetto_breve": "riassunto in max 10 parole dell'oggetto della mail",
  "riassunto": "riassunto in 2-3 frasi del contenuto rilevante",
  "azione_suggerita": "cosa deve fare l'agente (es: 'Creare preventivo per cliente X', 'Verificare ordine e inoltrare a mandante Y')",
  "prodotti": ["lista", "dei", "prodotti", "menzionati"],
  "confidenza": "alta | media | bassa"
}

Regole di classificazione:
- "ordine": il cliente ordina dei prodotti (parole chiave: ordine, ordinare, voglio, confermo, vi prego di spedire)
- "preventivo": il cliente chiede un preventivo/offerta/quotazione (parole chiave: preventivo, quotazione, prezzo, listino, quanto costa)
- "transito": email dove l'agente è in CC/CCN, ordine già inviato alla mandante
- "risposta": la mandante/fornitore risponde a un ordine o preventivo precedente (conferma spedizione, tempi, ecc.)
- "informativa": newsletter, promozioni, comunicazioni generali senza azione richiesta
- "altro": non rientra nelle categorie sopra

Priorità:
- "alta": ordine urgente, cliente importante, scadenza vicina
- "normale": ordine/preventivo standard
- "bassa": informativa, nessuna urgenza
"""


class EmailClassifier:

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"

    def classify(self, msg: EmailMessage, mailbox_name: str = "") -> EmailClassification:
        prompt_parts = [
            f"Casella email: {mailbox_name}" if mailbox_name else "",
            f"Da: {msg.from_addr}",
            f"A: {msg.to_addr}",
            f"Oggetto: {msg.subject}",
            f"Data: {msg.date}",
            "",
            "=== CORPO EMAIL ===",
            msg.body_plain or _strip_html(msg.body_html) or "(vuoto)",
        ]

        if msg.attachments:
            prompt_parts.append(f"\n[{len(msg.attachments)} allegati: {', '.join(a.filename for a in msg.attachments)}]")

        user_content = "\n".join(prompt_parts)

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": _SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_content}],
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Claude API error: %s", e)
            return EmailClassification(
                categoria="altro",
                priorita="normale",
                oggetto_breve=msg.subject[:60],
                riassunto=f"Errore classificazione: {e}",
                azione_suggerita="Verificare manualmente",
                confidenza="bassa",
            )

        raw_text = resp.json()["content"][0]["text"].strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            data = _extract_json(raw_text)
            if not data:
                return EmailClassification(
                    categoria="altro",
                    priorita="normale",
                    oggetto_breve=msg.subject[:60],
                    riassunto=f"Risposta non parsabile: {raw_text[:200]}",
                    azione_suggerita="Verificare manualmente",
                    confidenza="bassa",
                )

        return EmailClassification(
            categoria=data.get("categoria", "altro"),
            priorita=data.get("priorita", "normale"),
            cliente_nome=data.get("cliente_nome"),
            cliente_email=data.get("cliente_email"),
            mandante=data.get("mandante"),
            oggetto_breve=data.get("oggetto_breve", msg.subject[:60]),
            riassunto=data.get("riassunto", ""),
            azione_suggerita=data.get("azione_suggerita", ""),
            prodotti=data.get("prodotti", []),
            confidenza=data.get("confidenza", "media"),
            raw_json=data,
        )


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_json(text: str) -> Optional[dict]:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def classifier_from_config(cfg: dict) -> EmailClassifier:
    return EmailClassifier(
        api_key=cfg["anthropic"]["api_key"],
        model=cfg["anthropic"].get("model", "claude-haiku-4-5-20251001"),
    )
