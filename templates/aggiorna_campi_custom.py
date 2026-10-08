#!/usr/bin/env python3
"""
Aggiorna i campi custom degli account EspoCRM dal CSV convertito.
Utile quando l'import non ha mappato i campi custom (zona, condizioniPagamento, ecc.)

Uso su Windows CMD:
  set ESPOCRM_URL=http://100.79.250.23:8080
  set ESPOCRM_API_KEY=42f83e62ee977187aa76d2e701bb6fcc
  python templates\aggiorna_campi_custom.py percorso\import_espocrm_clienti.csv
"""

import sys
import csv
import os
import time
import requests

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "42f83e62ee977187aa76d2e701bb6fcc")
API_BASE = f"{ESPOCRM_URL}/api/v1"
HEADERS = {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}

# Campi da aggiornare: colonna CSV → campo EspoCRM
CAMPI = {
    "zona":                  "zona",
    "tipoAccount":           "tipoAccount",
    "referente":             "referente",
    "condizioniPagamento":   "condizioniPagamento",
    "priorita":              "priorita",
    "frequenzaVisitaGiorni": "frequenzaVisitaGiorni",
    "partitaIva":            "sicCode",
}


def cerca_account(nome: str) -> str | None:
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
    lst = r.json().get("list", [])
    return lst[0]["id"] if lst else None


def main():
    if len(sys.argv) < 2:
        print("Uso: python templates\\aggiorna_campi_custom.py <import_espocrm_clienti.csv>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Rileva separatore
    righe = []
    for sep in ["\t", ";", ","]:
        with open(input_file, encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=sep)
            righe = list(reader)
            if len(righe) > 0 and len(righe[0]) > 3:
                print(f"Separatore: {repr(sep)}")
                break

    print(f"Righe da processare: {len(righe)}")

    ok = 0
    skip = 0
    non_trovati = 0

    for i, r in enumerate(righe):
        nome = (r.get("name") or "").strip()
        if not nome:
            skip += 1
            continue

        # Costruisci payload con i campi non vuoti
        payload = {}
        for col, campo in CAMPI.items():
            val = (r.get(col) or "").strip()
            if val:
                # frequenzaVisitaGiorni deve essere intero
                if campo == "frequenzaVisitaGiorni":
                    try:
                        payload[campo] = int(val)
                    except ValueError:
                        pass
                else:
                    payload[campo] = val

        if not payload:
            skip += 1
            continue

        account_id = cerca_account(nome)
        if not account_id:
            print(f"  ⚠️  Non trovato: {nome}")
            non_trovati += 1
            continue

        r2 = requests.patch(f"{API_BASE}/Account/{account_id}",
                            headers=HEADERS,
                            json=payload,
                            timeout=10)
        if r2.ok:
            campi_str = ", ".join(f"{k}={v}" for k, v in payload.items() if k != "frequenzaVisitaGiorni")
            print(f"  ✅ {nome} | {campi_str}")
            ok += 1
        else:
            print(f"  ❌ {nome} — HTTP {r2.status_code}: {r2.text[:150]}")
            skip += 1

        if i % 10 == 0:
            time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"✅ Aggiornati: {ok}")
    print(f"⚠️  Non trovati: {non_trovati}")
    print(f"❌ Errori/saltati: {skip}")


if __name__ == "__main__":
    main()
