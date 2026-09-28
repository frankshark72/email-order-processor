#!/usr/bin/env python3
"""
Setup entità COrdine e CRigaOrdine in EspoCRM.
Esegui UNA VOLTA SOLA:

  export ESPOCRM_URL=http://100.79.250.23:8080
  export ESPOCRM_USER=admin
  export ESPOCRM_PASS=<password-admin>
  python3 setup/setup_ordini_entities.py

Nota: EntityManager richiede credenziali admin (non solo API key).
"""

import os
import sys
import base64
import requests

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://localhost:8080").rstrip("/")
ESPOCRM_USER = os.environ.get("ESPOCRM_USER", "admin")
ESPOCRM_PASS = os.environ.get("ESPOCRM_PASS", "")
API_BASE = f"{ESPOCRM_URL}/api/v1"

if not ESPOCRM_PASS:
    sys.exit("Errore: imposta ESPOCRM_PASS con la password dell'utente admin.")

_creds = base64.b64encode(f"{ESPOCRM_USER}:{ESPOCRM_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {_creds}",
    "Content-Type": "application/json",
}

ok = 0
skip = 0
err = 0


def _post(endpoint: str, payload: dict) -> dict | None:
    r = requests.post(f"{API_BASE}/{endpoint}", headers=HEADERS, json=payload, timeout=30)
    if not r.ok:
        return {"_error": r.status_code, "_body": r.text[:300]}
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text[:300]}


def create_entity(name: str, label: str, label_plural: str, entity_type: str = "Base") -> bool:
    global ok, skip, err
    print(f"\n--- Entita: {name}")
    result = _post("EntityManager/createEntity", {
        "name": name,
        "type": entity_type,
        "labelSingular": label,
        "labelPlural": label_plural,
        "addCreatedAt": True,
        "addModifiedAt": True,
        "addCreatedBy": True,
        "addModifiedBy": True,
    })
    if result and result.get("success"):
        print(f"   OK creata")
        ok += 1
        return True
    elif result and ("already exists" in str(result).lower() or "exists" in str(result).lower()):
        print(f"   SKIP gia esistente")
        skip += 1
        return True
    else:
        print(f"   ERRORE: {result}")
        err += 1
        return False


def add_field(entity_type: str, field_type: str, name: str, label: str, **kwargs) -> bool:
    global ok, skip, err
    payload = {
        "entityType": entity_type,
        "type": field_type,
        "name": name,
        "label": label,
        **kwargs
    }
    result = _post("EntityManager/createField", payload)
    if result and result.get("success"):
        print(f"   OK {name} ({field_type})")
        ok += 1
        return True
    elif result and ("already exists" in str(result).lower() or "exists" in str(result).lower()):
        print(f"   SKIP {name} (gia esistente)")
        skip += 1
        return True
    else:
        print(f"   ERRORE {name}: {result}")
        err += 1
        return False


def add_link(entity_from: str, entity_to: str, link_name: str, link_foreign: str,
             label: str, label_foreign: str, rel_type: str = "hasMany") -> bool:
    global ok, skip, err
    payload = {
        "entity": entity_from,
        "entityForeign": entity_to,
        "link": link_name,
        "linkForeign": link_foreign,
        "label": label,
        "labelForeign": label_foreign,
        "linkType": rel_type,
    }
    result = _post("EntityManager/createLink", payload)
    if result and result.get("success"):
        print(f"   OK link {entity_from}.{link_name} -> {entity_to}")
        ok += 1
        return True
    elif result and ("already exists" in str(result).lower() or "exists" in str(result).lower()):
        print(f"   SKIP link {link_name} (gia esistente)")
        skip += 1
        return True
    else:
        print(f"   ERRORE link {link_name}: {result}")
        err += 1
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 1. Nuova entita: COrdine (testata ordine)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("1. NUOVA ENTITA: COrdine")
print("="*60)

create_entity("COrdine", "Ordine", "Ordini", entity_type="BasePlus")

# Campi testata
add_field("COrdine", "varchar", "name",              "Numero Ordine")
add_field("COrdine", "link",    "cliente",            "Cliente",               entity="Account")
add_field("COrdine", "enum",    "brand",              "Brand / Mandante",
          options=["ELMO", "4Power", "Ermes", "Altro"])
add_field("COrdine", "date",    "dataOrdine",         "Data Ordine")
add_field("COrdine", "date",    "dataConferma",       "Data Conferma")
add_field("COrdine", "enum",    "stato",              "Stato",
          options=["da_elaborare", "da_confermare", "confermato",
                   "in_evasione", "parziale", "evaso"],
          default="da_elaborare")
add_field("COrdine", "enum",    "flusso",             "Tipo Flusso",
          options=["diretto", "tramite_agente"],
          default="diretto")
add_field("COrdine", "varchar", "riferimentoCliente", "Rif. Cliente")
add_field("COrdine", "varchar", "riferimentoMandante","Rif. Mandante")
add_field("COrdine", "varchar", "emailOrigine",       "Email Origine")
add_field("COrdine", "varchar", "oggettoEmail",       "Oggetto Email")
add_field("COrdine", "text",    "note",               "Note")
add_field("COrdine", "currency","totaleOrdine",       "Totale Ordine")
add_field("COrdine", "bool",    "controlloPrezziOk",  "Controllo Prezzi OK")
add_field("COrdine", "text",    "alertPrezzi",        "Alert Prezzi")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Nuova entita: CRigaOrdine (riga ordine)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("2. NUOVA ENTITA: CRigaOrdine")
print("="*60)

create_entity("CRigaOrdine", "Riga Ordine", "Righe Ordine")

add_field("CRigaOrdine", "link",     "ordine",           "Ordine",              entity="COrdine")
add_field("CRigaOrdine", "link",     "prodotto",         "Prodotto",            entity="CProdotto")
add_field("CRigaOrdine", "varchar",  "codiceProdotto",   "Codice Prodotto")
add_field("CRigaOrdine", "varchar",  "name",             "Descrizione")
add_field("CRigaOrdine", "float",    "quantita",         "Quantita")
add_field("CRigaOrdine", "varchar",  "unitaMisura",      "U.M.")
add_field("CRigaOrdine", "currency", "prezzoUnitario",   "Prezzo Unitario")
add_field("CRigaOrdine", "currency", "prezzoListino",    "Prezzo Listino")
add_field("CRigaOrdine", "currency", "prezzoNetto",      "Prezzo Netto Min")
add_field("CRigaOrdine", "float",    "scontoCliente",    "Sconto Cliente %")
add_field("CRigaOrdine", "currency", "prezzoScontato",   "Prezzo Scontato")
add_field("CRigaOrdine", "currency", "totaleRiga",       "Totale Riga")
add_field("CRigaOrdine", "date",     "dataEvasione",     "Data Evasione Prevista")
add_field("CRigaOrdine", "enum",     "statoRiga",        "Stato Riga",
          options=["da_confermare", "confermato", "in_spedizione", "spedito"],
          default="da_confermare")
add_field("CRigaOrdine", "varchar",  "alertPrezzo",      "Alert Prezzo")
add_field("CRigaOrdine", "text",     "note",             "Note")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Relazioni
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("3. RELAZIONI")
print("="*60)

add_link("COrdine", "CRigaOrdine",
         link_name="righeOrdine", link_foreign="ordine",
         label="Righe Ordine", label_foreign="Ordine",
         rel_type="hasMany")

add_link("COrdine", "Account",
         link_name="cliente", link_foreign="ordini",
         label="Cliente", label_foreign="Ordini",
         rel_type="belongsTo")

# ─────────────────────────────────────────────────────────────────────────────
# Riepilogo
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"COMPLETATO: OK {ok} creati  SKIP {skip} gia esistenti  ERRORE {err} errori")
print("="*60)

if err == 0:
    print("\nSetup completato! Ricarica EspoCRM (Admin > Rebuild) per vedere le modifiche.")
else:
    print(f"\n{err} errori - controlla i messaggi sopra.")
