"""Utilities condivise per tutti i moduli MCP EspoCRM."""
import os
import sys
import logging
import warnings

import requests

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
warnings.filterwarnings("ignore")

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "")
API_BASE = f"{ESPOCRM_URL}/api/v1"


def _headers() -> dict:
    return {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}


def _post(entity: str, payload: dict) -> dict:
    r = requests.post(f"{API_BASE}/{entity}", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def _patch(entity: str, record_id: str, payload: dict) -> dict:
    r = requests.patch(f"{API_BASE}/{entity}/{record_id}", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def _encode_where(params: dict, conditions: list, prefix: str = "where") -> None:
    for i, condition in enumerate(conditions):
        key_prefix = f"{prefix}[{i}]"
        for key, val in condition.items():
            if key == "value" and isinstance(val, list):
                if val and isinstance(val[0], dict):
                    _encode_where(params, val, f"{key_prefix}[value]")
                else:
                    for j, v in enumerate(val):
                        params[f"{key_prefix}[{key}][{j}]"] = v
            else:
                params[f"{key_prefix}[{key}]"] = val


def _search(entity: str, where: list, select: str = "", max_size: int = 50,
            order_by: str = "", order_direction: str = "asc") -> list:
    params: dict = {"maxSize": max_size}
    if select:
        params["select"] = select
    if order_by:
        params["orderBy"] = order_by
        params["order"] = order_direction
    _encode_where(params, where)
    r = requests.get(f"{API_BASE}/{entity}", headers=_headers(), params=params, timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("list", [])


def _check_api_key() -> None:
    if not ESPOCRM_API_KEY:
        print("Errore: ESPOCRM_API_KEY non impostata.", file=sys.stderr)
        sys.exit(1)
