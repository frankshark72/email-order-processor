#!/usr/bin/env python3
"""
Setup entità e campi custom in EspoCRM.
Esegui UNA VOLTA SOLA dalla VPS:

  export ESPOCRM_URL=http://100.79.250.23:8080
  export ESPOCRM_API_KEY=42f83e62ee977187aa76d2e701bb6fcc
  python setup/setup_espocrm_entities.py
"""

import os
import sys
import json
import requests

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "")
API_BASE = f"{ESPOCRM_URL}/api/v1"

if not ESPOCRM_API_KEY:
    sys.exit("Errore: ESPOCRM_API_KEY non impostata.")

HEADERS = {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}

ok = 0
skip = 0
err = 0


def _post(endpoint: str, payload: dict) -> dict | None:
    r = requests.post(f"{API_BASE}/{endpoint}", headers=HEADERS, json=payload, timeout=30)
    return r.json() if r.ok else None


def create_entity(name: str, label: str, label_plural: str) -> bool:
    global ok, skip, err
    print(f"\n📦 Entità: {name}")
    result = _post("EntityManager/createEntity", {
        "name": name,
        "type": "Base",
        "labelSingular": label,
        "labelPlural": label_plural,
        "addCreatedAt": True,
        "addModifiedAt": True,
        "addCreatedBy": True,
        "addModifiedBy": True,
    })
    if result and result.get("success"):
        print(f"   ✅ creata")
        ok += 1
        return True
    elif result and "already exists" in str(result).lower():
        print(f"   ⏭  già esistente")
        skip += 1
        return True
    else:
        print(f"   ❌ errore: {result}")
        err += 1
        return False


def add_field(entity: str, field_type: str, name: str, label: str, **kwargs) -> bool:
    global ok, skip, err
    payload = {"entityType": entity, "type": field_type, "name": name, "label": label, **kwargs}
    result = _post("EntityManager/createField", payload)
    if result and result.get("success"):
        print(f"   ✅ {name} ({field_type})")
        ok += 1
        return True
    elif result and ("already exists" in str(result).lower() or "exists" in str(result).lower()):
        print(f"   ⏭  {name} (già esistente)")
        skip += 1
        return True
    else:
        print(f"   ❌ {name}: {result}")
        err += 1
        return False


def add_relationship(entity_a: str, entity_b: str, rel_type: str = "manyToOne",
                     name_a: str = "", name_b: str = "") -> bool:
    global ok, skip, err
    result = _post("EntityManager/createRelationship", {
        "entityA": entity_a,
        "entityB": entity_b,
        "relationshipType": rel_type,
        "labelA": name_a or entity_a,
        "labelB": name_b or entity_b,
    })
    if result and result.get("success"):
        print(f"   ✅ relazione {entity_a} ↔ {entity_b}")
        ok += 1
        return True
    else:
        print(f"   ⏭  relazione {entity_a} ↔ {entity_b}: {result}")
        skip += 1
        return True  # spesso già esiste, non è un errore bloccante


# ─────────────────────────────────────────────────────────────────────────────
# 1. Campi custom su Account (clienti + fornitori)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("1. CAMPI CUSTOM SU ACCOUNT")
print("="*60)

add_field("Account", "varchar", "zona", "Zona")
add_field("Account", "enum", "tipoAccount", "Tipo Account",
          options=["cliente", "fornitore", "prospect"],
          default="cliente")
add_field("Account", "int", "frequenzaVisitaGiorni", "Frequenza Visita (giorni)",
          default=30)
add_field("Account", "date", "ultimaVisita", "Ultima Visita")
add_field("Account", "varchar", "referente", "Referente")
add_field("Account", "enum", "priorita", "Priorità",
          options=["alta", "media", "bassa"],
          default="media")
add_field("Account", "float", "latitudine", "Latitudine")
add_field("Account", "float", "longitudine", "Longitudine")
add_field("Account", "varchar", "condizioniPagamento", "Condizioni di Pagamento")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Campi custom su Prodotto
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("2. CAMPI CUSTOM SU PRODOTTO")
print("="*60)

add_field("Prodotto", "link", "fornitore", "Fornitore",
          entity="Account")
add_field("Prodotto", "varchar", "categoria", "Categoria")
add_field("Prodotto", "varchar", "codice", "Codice Prodotto")
add_field("Prodotto", "enum", "unitaMisura", "Unità di Misura",
          options=["pz", "kg", "lt", "cassa", "collo", "conf"],
          default="pz")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Campi custom su Listino
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("3. CAMPI CUSTOM SU LISTINO")
print("="*60)

add_field("Listino", "link", "fornitore", "Fornitore",
          entity="Account")
add_field("Listino", "date", "validoDal", "Valido Dal")
add_field("Listino", "date", "validoAl", "Valido Al")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Nuova entità: ScontoCliente
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("4. NUOVA ENTITÀ: ScontoCliente")
print("="*60)

create_entity("ScontoCliente", "Sconto Cliente", "Sconti Clienti")

add_field("ScontoCliente", "link", "cliente", "Cliente", entity="Account")
add_field("ScontoCliente", "link", "fornitore", "Fornitore", entity="Account")
add_field("ScontoCliente", "varchar", "categoria", "Categoria Prodotto")
add_field("ScontoCliente", "float", "sconto", "Sconto %")
add_field("ScontoCliente", "date", "validoDal", "Valido Dal")
add_field("ScontoCliente", "date", "validoAl", "Valido Al")
add_field("ScontoCliente", "text", "note", "Note")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Nuova entità: RigaListino
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("5. NUOVA ENTITÀ: RigaListino")
print("="*60)

create_entity("RigaListino", "Riga Listino", "Righe Listino")

add_field("RigaListino", "link", "prodotto", "Prodotto", entity="Prodotto")
add_field("RigaListino", "link", "listino", "Listino", entity="Listino")
add_field("RigaListino", "int", "quantitaMinima", "Quantità Minima", default=1)
add_field("RigaListino", "currency", "prezzoNetto", "Prezzo Netto")
add_field("RigaListino", "text", "note", "Note")

# ─────────────────────────────────────────────────────────────────────────────
# Riepilogo
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"COMPLETATO: ✅ {ok} creati  ⏭  {skip} già esistenti  ❌ {err} errori")
print("="*60)

if err == 0:
    print("\n🎉 Setup completato! Ricarica EspoCRM per vedere le modifiche.")
    print("   Admin → Entity Manager → per verificare campi e entità.")
else:
    print(f"\n⚠️  {err} errori — verifica i messaggi sopra.")
    print("   Probabilmente alcuni campi vanno creati manualmente in Admin → Entity Manager.")
