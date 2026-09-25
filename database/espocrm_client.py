"""
EspoCRM REST API client.

Supports authentication via:
  - API key (X-Api-Key header) — recommended
  - Basic auth (username + password)

EspoCRM REST API reference:
  https://docs.espocrm.com/development/api/
"""

from __future__ import annotations

import base64
from typing import Optional

import requests


class EspoCRMError(Exception):
    pass


class EspoCRMClient:
    def __init__(self, url: str, api_key: str = None,
                 username: str = None, password: str = None):
        self.base_url = url.rstrip("/") + "/api/v1"
        self._api_key = api_key
        self._username = username
        self._password = password

        if not api_key and not (username and password):
            raise ValueError(
                "EspoCRM: fornisci api_key oppure username+password"
            )

    def _headers(self) -> dict:
        if self._api_key:
            return {"X-Api-Key": self._api_key, "Content-Type": "application/json"}
        creds = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()
        return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str,
                 params: dict = None, json: dict = None) -> dict | list:
        url = f"{self.base_url}/{path}"
        resp = requests.request(
            method, url,
            headers=self._headers(),
            params=params,
            json=json,
            timeout=15,
        )
        if not resp.ok:
            raise EspoCRMError(
                f"EspoCRM {method} {path} → {resp.status_code}: {resp.text[:300]}"
            )
        if resp.content:
            return resp.json()
        return {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get_list(self, entity: str, where: list = None,
                 select: str = None, order_by: str = None,
                 max_size: int = 50) -> list[dict]:
        """Return a list of records matching the given filters."""
        params = {"maxSize": max_size}
        if select:
            params["select"] = select
        if order_by:
            params["orderBy"] = order_by
        if where:
            for i, clause in enumerate(where):
                for k, v in clause.items():
                    params[f"where[{i}][{k}]"] = v

        data = self._request("GET", entity, params=params)
        return data.get("list", [])

    def get(self, entity: str, record_id: str) -> Optional[dict]:
        """Return a single record by ID, or None if not found."""
        try:
            return self._request("GET", f"{entity}/{record_id}")
        except EspoCRMError as e:
            if "404" in str(e):
                return None
            raise

    def create(self, entity: str, data: dict) -> dict:
        """Create a record and return the created record (with id)."""
        return self._request("POST", entity, json=data)

    def update(self, entity: str, record_id: str, data: dict) -> dict:
        """Update a record and return the updated record."""
        return self._request("PUT", f"{entity}/{record_id}", json=data)

    def delete(self, entity: str, record_id: str) -> None:
        """Delete a record."""
        self._request("DELETE", f"{entity}/{record_id}")

    def search_one(self, entity: str, field: str, value: str,
                   select: str = None) -> Optional[dict]:
        """Convenience: search for the first record where field == value."""
        results = self.get_list(
            entity,
            where=[{"type": "equals", "field": field, "value": value}],
            select=select,
            max_size=1,
        )
        return results[0] if results else None

    def search_like(self, entity: str, field: str, value: str,
                    select: str = None) -> Optional[dict]:
        """Convenience: search for the first record where field LIKE %value%."""
        results = self.get_list(
            entity,
            where=[{"type": "contains", "field": field, "value": value}],
            select=select,
            max_size=1,
        )
        return results[0] if results else None
