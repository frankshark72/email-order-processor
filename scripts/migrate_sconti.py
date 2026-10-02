#!/usr/bin/env python3
"""
Migra i record CScontoCliente esistenti: popola scontiClienteId e scontiMandanteId
estraendo cliente e mandante dal campo 'name' (formato "CLIENTE - MANDANTE").

Uso:
  python3 scripts/migrate_sconti.py          # dry-run (mostra cosa farebbe)
  python3 scripts/migrate_sconti.py --apply  # applica le modifiche
"""

import sys
import requests

API_BASE = "http://100.79.250.23:8080/api/v1"
API_KEY = "42f83e62ee977187aa76d2e701bb6fcc"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

apply = "--apply" in sys.argv


def search(entity, where, select="id,name", max_size=200):
    params = {"select": select, "maxSize": max_size}
    for i, w in enumerate(where):
        for k, v in w.items():
            params[f"where[{i}][{k}]"] = v
    r = requests.get(f"{API_BASE}/{entity}", headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("list", [])


def patch(entity, record_id, data):
    r = requests.put(f"{API_BASE}/{entity}/{record_id}", headers=HEADERS, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


print("Caricamento account...")
all_accounts = search("Account", [], select="id,name", max_size=500)
account_map = {}
for a in all_accounts:
    account_map[a["name"].strip().lower()] = a

print(f"  {len(all_accounts)} account caricati\n")

print("Caricamento sconti...")
sconti = search("CScontoCliente", [],
                select="id,name,scontiClienteId,scontiMandanteId,tipoCliente,scontoPct",
                max_size=200)
print(f"  {len(sconti)} sconti trovati\n")

ok = 0
skip = 0
err = 0

for s in sconti:
    name = s.get("name", "")
    has_client = s.get("scontiClienteId")
    has_mandante = s.get("scontiMandanteId")

    if has_client and has_mandante:
        print(f"  SKIP {name} (già collegato)")
        skip += 1
        continue

    parts = name.split(" – ")
    if len(parts) != 2:
        parts = name.split(" - ")
    if len(parts) != 2:
        print(f"  ERR  {name} — formato nome non riconosciuto (atteso 'CLIENTE - MANDANTE')")
        err += 1
        continue

    cliente_name = parts[0].strip()
    mandante_name = parts[1].strip()

    cliente = account_map.get(cliente_name.lower())
    mandante = account_map.get(mandante_name.lower())

    if not cliente:
        for key, acc in account_map.items():
            if cliente_name.lower() in key or key in cliente_name.lower():
                cliente = acc
                break

    if not mandante:
        for key, acc in account_map.items():
            if mandante_name.lower() in key or key in mandante_name.lower():
                mandante = acc
                break

    updates = {}
    notes = []

    if not has_client and cliente:
        updates["scontiClienteId"] = cliente["id"]
        notes.append(f"cliente={cliente['name']}")
    elif not has_client:
        notes.append(f"cliente '{cliente_name}' NON TROVATO")

    if not has_mandante and mandante:
        updates["scontiMandanteId"] = mandante["id"]
        notes.append(f"mandante={mandante['name']}")
    elif not has_mandante:
        notes.append(f"mandante '{mandante_name}' NON TROVATO")

    if updates:
        if apply:
            try:
                patch("CScontoCliente", s["id"], updates)
                print(f"  OK   {name} → {', '.join(notes)}")
                ok += 1
            except Exception as e:
                print(f"  ERR  {name} — {e}")
                err += 1
        else:
            print(f"  [DRY] {name} → {', '.join(notes)}")
            ok += 1
    else:
        print(f"  ERR  {name} — {', '.join(notes)}")
        err += 1

print(f"\n{'APPLICATO' if apply else 'DRY-RUN'}: {ok} aggiornati, {skip} già ok, {err} errori")
if not apply and ok > 0:
    print("\nRilancia con --apply per applicare le modifiche.")
