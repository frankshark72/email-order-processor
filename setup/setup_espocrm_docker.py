#!/usr/bin/env python3
"""
Crea campi custom e nuove entità in EspoCRM scrivendo direttamente
nei file di metadata del container Docker.

Esegui sulla VM:
  python3 setup/setup_espocrm_docker.py
"""

import json
import subprocess
import sys
import os

CONTAINER = "espocrm-espocrm-1"
CUSTOM_PATH = "/var/www/html/custom/Espo/Custom/Resources/metadata"


def docker_exec(cmd: str) -> tuple[int, str]:
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c", cmd],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


def read_json(path: str) -> dict:
    code, out = docker_exec(f"cat {path} 2>/dev/null || echo '{{}}'")
    try:
        return json.loads(out.strip() or "{}")
    except Exception:
        return {}


def write_json(path: str, data: dict) -> bool:
    content = json.dumps(data, indent=2, ensure_ascii=False)
    # Escape single quotes for shell
    content_escaped = content.replace("'", "'\\''")
    code, out = docker_exec(f"mkdir -p $(dirname {path}) && printf '%s' '{content_escaped}' > {path}")
    return code == 0


def merge_fields(path: str, new_fields: dict) -> bool:
    """Legge file esistente, aggiunge campi, riscrive."""
    existing = read_json(path)
    if "fields" not in existing:
        existing["fields"] = {}
    existing["fields"].update(new_fields)
    return write_json(path, existing)


def merge_links(path: str, new_links: dict) -> bool:
    existing = read_json(path)
    if "links" not in existing:
        existing["links"] = {}
    existing["links"].update(new_links)
    return write_json(path, existing)


ok = 0
err = 0


def step(desc: str, success: bool):
    global ok, err
    if success:
        print(f"   ✅ {desc}")
        ok += 1
    else:
        print(f"   ❌ {desc}")
        err += 1


# ─────────────────────────────────────────────────────────────────────────────
# 1. Campi custom su Account
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("1. CAMPI CUSTOM SU ACCOUNT")
print("="*60)

account_fields = {
    "zona":                 {"type": "varchar", "maxLength": 100},
    "tipoAccount":          {"type": "enum", "options": ["Cliente", "Fornitore", "Prospect", "Installatore", "Rivenditore"], "default": "Cliente"},
    "frequenzaVisitaGiorni":{"type": "int", "default": 30},
    "ultimaVisita":         {"type": "date"},
    "ultimaChiamata":       {"type": "date"},
    "referente":            {"type": "varchar", "maxLength": 150},
    "priorita":             {"type": "enum", "options": ["alta", "media", "bassa"], "default": "media"},
    "latitudine":           {"type": "float"},
    "longitudine":          {"type": "float"},
    "condizioniPagamento":  {"type": "varchar", "maxLength": 100},
    "codiceFiscale":        {"type": "varchar", "maxLength": 20},
}
step("campi Account", merge_fields(f"{CUSTOM_PATH}/entityDefs/Account.json", account_fields))

# ─────────────────────────────────────────────────────────────────────────────
# 2. Campi custom su Prodotto
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("2. CAMPI CUSTOM SU PRODOTTO")
print("="*60)

prodotto_fields = {
    "categoria":   {"type": "varchar", "maxLength": 100},
    "codice":      {"type": "varchar", "maxLength": 50},
    "unitaMisura": {"type": "enum", "options": ["pz", "kg", "lt", "cassa", "collo", "conf"], "default": "pz"},
    "fornitoreId": {"type": "foreignId"},
    "fornitoreName":{"type": "foreignName"},
    "fornitore":   {"type": "link"},
}
prodotto_links = {
    "fornitore": {"type": "belongsTo", "entity": "Account", "foreign": "prodotti", "foreignName": "name"}
}
step("campi Prodotto", merge_fields(f"{CUSTOM_PATH}/entityDefs/Prodotto.json", prodotto_fields))
step("link Prodotto→Account", merge_links(f"{CUSTOM_PATH}/entityDefs/Prodotto.json", prodotto_links))

# ─────────────────────────────────────────────────────────────────────────────
# 3. Campi custom su Listino
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("3. CAMPI CUSTOM SU LISTINO")
print("="*60)

listino_fields = {
    "validoDal":    {"type": "date"},
    "validoAl":     {"type": "date"},
    "fornitoreId":  {"type": "foreignId"},
    "fornitoreName":{"type": "foreignName"},
    "fornitore":    {"type": "link"},
}
listino_links = {
    "fornitore": {"type": "belongsTo", "entity": "Account", "foreign": "listini", "foreignName": "name"}
}
step("campi Listino", merge_fields(f"{CUSTOM_PATH}/entityDefs/Listino.json", listino_fields))
step("link Listino→Account", merge_links(f"{CUSTOM_PATH}/entityDefs/Listino.json", listino_links))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Nuova entità: ScontoCliente
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("4. NUOVA ENTITÀ: ScontoCliente")
print("="*60)

sconto_scope = {
    "entity": True, "object": True, "tab": True,
    "type": "Base", "module": "Custom", "stream": False,
    "disabled": False, "importable": True
}
sconto_defs = {
    "fields": {
        "name":         {"type": "varchar", "required": True},
        "categoria":    {"type": "varchar", "maxLength": 100},
        "tipoPrezzo":   {"type": "enum",
                         "options": ["sconto_percentuale", "netto_rivenditore", "netto_installatore"],
                         "default": "sconto_percentuale"},
        "sconto":       {"type": "float"},
        "validoDal":    {"type": "date"},
        "validoAl":     {"type": "date"},
        "note":         {"type": "text"},
        "clienteId":    {"type": "foreignId"},
        "clienteName":  {"type": "foreignName"},
        "cliente":      {"type": "link"},
        "fornitoreId":  {"type": "foreignId"},
        "fornitoreName":{"type": "foreignName"},
        "fornitore":    {"type": "link"},
    },
    "links": {
        "cliente":   {"type": "belongsTo", "entity": "Account", "foreign": "scontiClienteCliente",   "foreignName": "name"},
        "fornitore": {"type": "belongsTo", "entity": "Account", "foreign": "scontiClienteFornitore", "foreignName": "name"},
        "createdBy": {"type": "belongsTo", "entity": "User"},
        "modifiedBy":{"type": "belongsTo", "entity": "User"},
    },
    "collection": {"orderBy": "createdAt", "order": "desc"}
}
step("scope ScontoCliente",    write_json(f"{CUSTOM_PATH}/scopes/ScontoCliente.json", sconto_scope))
step("entityDefs ScontoCliente", write_json(f"{CUSTOM_PATH}/entityDefs/ScontoCliente.json", sconto_defs))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Nuova entità: RigaListino
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("5. NUOVA ENTITÀ: RigaListino")
print("="*60)

riga_scope = {
    "entity": True, "object": True, "tab": True,
    "type": "Base", "module": "Custom", "stream": False,
    "disabled": False, "importable": True
}
riga_defs = {
    "fields": {
        "name":           {"type": "varchar", "required": True},
        "tipoCliente":    {"type": "enum",
                           "options": ["rivenditore", "installatore"],
                           "default": "rivenditore"},
        "quantitaMinima": {"type": "int", "default": 1},
        "prezzoNetto":    {"type": "currency"},
        "note":           {"type": "text"},
        "prodottoId":     {"type": "foreignId"},
        "prodottoName":   {"type": "foreignName"},
        "prodotto":       {"type": "link"},
        "listinoId":      {"type": "foreignId"},
        "listinoName":    {"type": "foreignName"},
        "listino":        {"type": "link"},
    },
    "links": {
        "prodotto":  {"type": "belongsTo", "entity": "Prodotto",  "foreign": "righeListino", "foreignName": "name"},
        "listino":   {"type": "belongsTo", "entity": "Listino",   "foreign": "righe",        "foreignName": "name"},
        "createdBy": {"type": "belongsTo", "entity": "User"},
        "modifiedBy":{"type": "belongsTo", "entity": "User"},
    },
    "collection": {"orderBy": "quantitaMinima", "order": "asc"}
}
step("scope RigaListino",     write_json(f"{CUSTOM_PATH}/scopes/RigaListino.json", riga_scope))
step("entityDefs RigaListino", write_json(f"{CUSTOM_PATH}/entityDefs/RigaListino.json", riga_defs))

# ─────────────────────────────────────────────────────────────────────────────
# 6. Rebuild cache EspoCRM
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("6. REBUILD CACHE ESPOCRM")
print("="*60)

code, out = docker_exec("php /var/www/html/command.php rebuild 2>&1")
if code == 0:
    print("   ✅ cache rebuilt")
    ok += 1
else:
    print(f"   ⚠️  rebuild output: {out[:200]}")
    # Non è un errore bloccante
    err += 1

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"COMPLETATO: ✅ {ok} operazioni  ❌ {err} errori")
print("="*60)
if err == 0:
    print("\n🎉 Ricarica EspoCRM nel browser per vedere le modifiche.")
else:
    print("\n⚠️  Alcuni passi hanno avuto errori. Verifica sopra.")
