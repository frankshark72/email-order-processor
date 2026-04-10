"""
EspoCRM API client for creating and sending emails.

IMPORTANT: When creating an email via EspoCRM REST API with status "Sent",
EspoCRM only stores the record — it does NOT actually send the email via SMTP.

The correct flow is:
  1. Create the email with status "Draft"
  2. Call POST /Email/{id}/action/send to actually dispatch it
  3. EspoCRM sends it through its configured SMTP and sets status to "Sent"
"""

from __future__ import annotations

import json
from typing import Optional

import requests


class EspoCrmClient:
    """
    Client for the EspoCRM REST API (v1).

    Config example (config.yaml):

        espocrm:
          url: "https://crm.example.com"
          api_key: "your-api-key-here"
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        })

    # ── Low-level helpers ────────────────────────────────────────────────────

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.api_url}/{endpoint}"
        resp = self.session.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def _put(self, endpoint: str, data: dict) -> dict:
        url = f"{self.api_url}/{endpoint}"
        resp = self.session.put(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.api_url}/{endpoint}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Email operations ─────────────────────────────────────────────────────

    def create_and_send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_address: str = None,
        from_name: str = None,
        cc: list[str] = None,
        is_html: bool = False,
        parent_type: str = None,
        parent_id: str = None,
    ) -> dict:
        """
        Create an email in EspoCRM and actually send it.

        This is the correct way to send emails via the EspoCRM API:
          1. Create email as Draft
          2. Call the send action to dispatch it via SMTP

        If you only POST with status="Sent", EspoCRM stores the record
        but does NOT deliver the email.

        Args:
            to: recipient email address
            subject: email subject
            body: email body (plain text or HTML)
            from_address: sender email address (uses EspoCRM default if None)
            from_name: sender display name
            cc: list of CC addresses
            is_html: whether body is HTML
            parent_type: link to CRM entity type (e.g. "Account", "Contact")
            parent_id: ID of the linked CRM entity

        Returns:
            The EspoCRM email record (dict) after sending.
        """
        # Step 1: Create the email as Draft
        email_data = {
            "status": "Draft",
            "subject": subject,
            "body": body,
            "isHtml": is_html,
            "to": to,
        }

        if from_address:
            email_data["from"] = from_address
        if from_name:
            email_data["fromName"] = from_name
        if cc:
            email_data["cc"] = ";".join(cc)
        if parent_type and parent_id:
            email_data["parentType"] = parent_type
            email_data["parentId"] = parent_id

        email_record = self._post("Email", email_data)
        email_id = email_record["id"]
        print(f"[ESPOCRM] Email draft creata: {email_id}")

        # Step 2: Send the email via EspoCRM's SMTP
        # This triggers actual SMTP delivery and updates status to "Sent"
        self._post(f"Email/{email_id}/action/send", {})
        print(f"[ESPOCRM] Email inviata: {email_id} → {to}")

        return email_record

    def create_email_record(
        self,
        to: str,
        subject: str,
        body: str,
        status: str = "Sent",
        from_address: str = None,
        from_name: str = None,
        is_html: bool = False,
        parent_type: str = None,
        parent_id: str = None,
    ) -> dict:
        """
        Create an email record in EspoCRM WITHOUT sending it.

        Use this only when the email has already been sent via external SMTP
        and you just want to log it in EspoCRM.

        Args:
            to: recipient email address
            subject: email subject
            body: email body
            status: email status ("Sent", "Draft", "Archived")
            from_address: sender email
            from_name: sender name
            is_html: whether body is HTML
            parent_type: link to CRM entity type
            parent_id: ID of the linked CRM entity

        Returns:
            The created EspoCRM email record (dict).
        """
        email_data = {
            "status": status,
            "subject": subject,
            "body": body,
            "isHtml": is_html,
            "to": to,
        }

        if from_address:
            email_data["from"] = from_address
        if from_name:
            email_data["fromName"] = from_name
        if parent_type and parent_id:
            email_data["parentType"] = parent_type
            email_data["parentId"] = parent_id

        record = self._post("Email", email_data)
        print(f"[ESPOCRM] Record email creato: {record['id']} (status={status})")
        return record


# ── Factory from config ──────────────────────────────────────────────────────

def espocrm_from_config(cfg: dict) -> Optional[EspoCrmClient]:
    """
    Build an EspoCrmClient from config, or return None if not configured.

        espocrm:
          url: "https://crm.example.com"
          api_key: "your-api-key"
    """
    espo_cfg = cfg.get("espocrm")
    if not espo_cfg:
        return None

    url = espo_cfg.get("url", "").strip()
    api_key = espo_cfg.get("api_key", "").strip()

    if not url or not api_key:
        return None

    return EspoCrmClient(base_url=url, api_key=api_key)
