#!/usr/bin/env python3
"""
Aggiorna i numeri di telefono degli account gia importati in EspoCRM.
Legge il CSV originale e aggiorna solo il campo phoneNumber.

Uso su Windows CMD:
  set ESPOCRM_URL=http://100.79.250.23:8080
  set ESPOCRM_API_KEY=42f83e62ee977187aa76d2e701bb6fcc
  python templates\\aggiorna_telefoni.py percorso\\clienti_rib.csv

Uso su Linux/VPS:
  python3 templates/aggiorna_telefoni.py /percorso/clienti_rib.csv
"""

import sys
import csv
import json
import os
import time
import requests

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "42f83e62ee977187aa76d2e701bb6fcc")
API_BASE = f"{ESPOCRM_URL}/api/v1"
HEADERS = {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}


def pulisci_tel(tel: str) -> str:
    t = (tel or "").strip().replace(" ", "").replace("-", "").replace(".", "")
    if not t:
        return ""
    if t.startswith("+") or t.startswith("3"):
        return t
    if not t.startswith("0"):
        return "0" + t
    return t


def cerca_account(nome: str) -> str | None:
    """Cerca account per nome esatto, ritorna ID o None."""
    r = requests.get(f"{API_BASE}/Account",
                     headers=HEADERS,
                     params={
                         "maxSize": 1,
                         "select": "id,name",
                         "where[0][type]": "equals",
                         "where[0][attribute]": "name",
                         "where[0][value]": nome,
                     }, timeout=10)
    if not r.ok:
        return None
    data = r.json()
    lst = data.get("list", [])
    return lst[0]["id"] if lst else None


def aggiorna_telefono(account_id: str, tel_cell: str, tel_fisso: str) -> bool:
    """Aggiorna il campo phoneNumber con formato lista EspoCRM."""
    numeri = []
    if tel_cell:
        numeri.append({"value": tel_cell, "type": "mobile", "primary": True})
    if tel_fisso:
        numeri.append({"value": tel_fisso, "type": "office", "primary": not bool(tel_cell)})

    if not numeri:
        return False

    r = requests.patch(f"{API_BASE}/Account/{account_id}",
                       headers=HEADERS,
                       json={"phoneNumberData": numeri},
                       timeout=10)
    if not r.ok:
        print(f"    HTTP {r.status_code}: {r.text[:200]}")
    return r.ok


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 templates/aggiorna_telefoni.py <file.csv>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Rileva separatore
    separatori = ["\t", ";", ","]
    righe = []
    for sep in separatori:
        with open(input_file, encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=sep)
            righe = list(reader)
            if len(righe) > 0 and len(righe[0]) > 3:
                print(f"Separatore rilevato: {repr(sep)}")
                break

    print(f"Righe da processare: {len(righe)}")
    if righe:
        print(f"Colonne trovate: {list(righe[0].keys())}")

    ok = 0
    skip = 0
    non_trovati = 0
    senza_tel = 0

    for i, r in enumerate(righe):
        nome = (r.get("RagioneSociale") or "").strip()
        if not nome:
            skip += 1
            continue

        tel_fisso = pulisci_tel(r.get("Telefono1") or "")
        tel_cell  = pulisci_tel(r.get("Telcellulare") or "")

        if not tel_fisso and not tel_cell:
            senza_tel += 1
            continue

        # Cerca account in EspoCRM
        account_id = cerca_account(nome)
        if not account_id:
            print(f"  ⚠️  Non trovato: {nome}")
            non_trovati += 1
            continue

        # Aggiorna telefono
        if aggiorna_telefono(account_id, tel_cell, tel_fisso):
            print(f"  ✅ {nome} | cell: {tel_cell or '—'} | fisso: {tel_fisso or '—'}")
            ok += 1
        else:
            print(f"  ❌ Errore aggiornamento: {nome}")
            skip += 1

        # Pausa per non sovraccaricare EspoCRM
        if i % 10 == 0:
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"✅ Aggiornati: {ok}")
    print(f"⚠️  Non trovati: {non_trovati}")
    print(f"📵 Senza telefono: {senza_tel}")
    print(f"❌ Errori: {skip}")


if __name__ == "__main__":
    main()
