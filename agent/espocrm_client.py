"""
EspoCRM API client for creating and managing Tasks and other entities.
Uses the REST API with API Key authentication.
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class EspoCRMClient:
    """
    Client for EspoCRM REST API.

    Usage:
        client = EspoCRMClient(url="http://100.79.250.23:8080", api_key="your-key")
        task_id = client.create_task(
            name="Processare ordine da Ferramenta Rossi",
            description="Ordine ricevuto via email...",
            account_id="abc123",
            priority="Normal",
        )
    """

    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        url = f"{self.base_url}/api/v1/{endpoint}"
        try:
            resp = self.session.request(method, url, json=data, timeout=30)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.exceptions.RequestException as e:
            logger.error("EspoCRM API error: %s %s → %s", method, endpoint, e)
            raise

    # ── Task operations ──────────────────────────────────────────

    def create_task(
        self,
        name: str,
        description: str = "",
        status: str = "Not Started",
        priority: str = "Normal",
        date_start: str = None,
        date_end: str = None,
        assigned_user_id: str = None,
        account_id: str = None,
        contact_id: str = None,
        parent_type: str = None,
        parent_id: str = None,
    ) -> str:
        payload = {
            "name": name,
            "status": status,
            "priority": priority,
        }
        if description:
            payload["description"] = description
        if date_start:
            payload["dateStart"] = date_start
        if date_end:
            payload["dateEnd"] = date_end
        else:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            payload["dateEnd"] = tomorrow
        if assigned_user_id:
            payload["assignedUserId"] = assigned_user_id
        if account_id:
            payload["parentType"] = "Account"
            payload["parentId"] = account_id
        if contact_id:
            payload["contactId"] = contact_id
        if parent_type and parent_id:
            payload["parentType"] = parent_type
            payload["parentId"] = parent_id

        result = self._request("POST", "Task", payload)
        task_id = result.get("id", "")
        logger.info("Created Task #%s: %s", task_id, name)
        return task_id

    def update_task(self, task_id: str, data: dict) -> dict:
        return self._request("PUT", f"Task/{task_id}", data)

    def get_task(self, task_id: str) -> dict:
        return self._request("GET", f"Task/{task_id}")

    # ── Account (client) lookup ──────────────────────────────────

    def find_account_by_email(self, email: str) -> Optional[dict]:
        endpoint = (
            "Account?where[0][type]=linkedWith&where[0][attribute]=emailAddresses"
            f"&where[0][value][]={email}&select=id,name"
        )
        result = self._request("GET", endpoint)
        records = result.get("list", [])
        return records[0] if records else None

    def find_account_by_name(self, name: str) -> Optional[dict]:
        endpoint = f"Account?where[0][type]=contains&where[0][attribute]=name&where[0][value]={name}&select=id,name"
        result = self._request("GET", endpoint)
        records = result.get("list", [])
        return records[0] if records else None

    def search_accounts(self, query: str) -> list[dict]:
        endpoint = f"Account?where[0][type]=textFilter&where[0][value]={query}&select=id,name&maxSize=5"
        result = self._request("GET", endpoint)
        return result.get("list", [])

    # ── Contact lookup ───────────────────────────────────────────

    def find_contact_by_email(self, email: str) -> Optional[dict]:
        endpoint = (
            "Contact?where[0][type]=linkedWith&where[0][attribute]=emailAddresses"
            f"&where[0][value][]={email}&select=id,name,accountId,accountName"
        )
        result = self._request("GET", endpoint)
        records = result.get("list", [])
        return records[0] if records else None

    # ── Generic entity operations ────────────────────────────────

    def create_entity(self, entity_type: str, data: dict) -> str:
        result = self._request("POST", entity_type, data)
        return result.get("id", "")

    def get_entity(self, entity_type: str, entity_id: str) -> dict:
        return self._request("GET", f"{entity_type}/{entity_id}")

    def list_entities(self, entity_type: str, where: dict = None,
                      select: str = None, max_size: int = 20) -> list[dict]:
        endpoint = f"{entity_type}?maxSize={max_size}"
        if select:
            endpoint += f"&select={select}"
        result = self._request("GET", endpoint)
        return result.get("list", [])

    # ── User lookup (for task assignment) ────────────────────────

    def get_users(self) -> list[dict]:
        result = self._request("GET", "User?where[0][type]=isTrue&where[0][attribute]=isActive&select=id,name,userName&maxSize=50")
        return result.get("list", [])


def client_from_config(cfg: dict) -> EspoCRMClient:
    espo = cfg["espocrm"]
    return EspoCRMClient(
        url=espo["url"],
        api_key=espo["api_key"],
    )
