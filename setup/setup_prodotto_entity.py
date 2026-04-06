#!/usr/bin/env python3
"""
Crea/completa l'entità Prodotto in EspoCRM con tutti i campi
necessari per il listino Elmo (e altri fornitori).

Esegui sulla VM:
  python3 setup/setup_prodotto_entity.py
"""

import json
import subprocess

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
    content_escaped = content.replace("'", "'\\''")
    code, out = docker_exec(
        f"mkdir -p $(dirname {path}) && printf '%s' '{content_escaped}' > {path}"
    )
    return code == 0


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
# 1. Scope Prodotto
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("1. SCOPE PRODOTTO")
print("="*60)

prodotto_scope = {
    "entity": True,
    "object": True,
    "tab": True,
    "type": "Base",
    "module": "Custom",
    "stream": False,
    "disabled": False,
    "importable": True
}
step("scope Prodotto", write_json(f"{CUSTOM_PATH}/scopes/Prodotto.json", prodotto_scope))

# ─────────────────────────────────────────────────────────────────────────────
# 2. EntityDefs Prodotto
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("2. ENTITYDEFS PRODOTTO")
print("="*60)

prodotto_defs = {
    "fields": {
        "name": {
            "type": "varchar",
            "maxLength": 255,
            "required": True
        },
        "codice": {
            "type": "varchar",
            "maxLength": 50
        },
        "codiceAlfanumerico": {
            "type": "varchar",
            "maxLength": 50
        },
        "categoria": {
            "type": "enum",
            "options": ["Intrusione", "Antincendio", "TVCC", "Controllo Accessi", "Altro"],
            "default": "Altro"
        },
        "disponibilita": {
            "type": "varchar",
            "maxLength": 200
        },
        "prezzoListino": {
            "type": "currency"
        },
        "prezzoSuRichiesta": {
            "type": "bool",
            "default": False
        },
        "codiceRiparazione": {
            "type": "varchar",
            "maxLength": 10
        },
        "garanzia": {
            "type": "varchar",
            "maxLength": 20
        },
        "attivo": {
            "type": "bool",
            "default": True
        },
        "note": {
            "type": "text"
        },
        "fornitoreId": {
            "type": "foreignId"
        },
        "fornitoreName": {
            "type": "foreignName"
        },
        "fornitore": {
            "type": "link"
        }
    },
    "links": {
        "fornitore": {
            "type": "belongsTo",
            "entity": "Account",
            "foreign": "prodotti",
            "foreignName": "name"
        },
        "createdBy": {"type": "belongsTo", "entity": "User"},
        "modifiedBy": {"type": "belongsTo", "entity": "User"}
    },
    "collection": {
        "orderBy": "codice",
        "order": "asc"
    }
}
step("entityDefs Prodotto", write_json(f"{CUSTOM_PATH}/entityDefs/Prodotto.json", prodotto_defs))

# ─────────────────────────────────────────────────────────────────────────────
# 3. Aggiungi link prodotti su Account
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("3. LINK PRODOTTI SU ACCOUNT")
print("="*60)

account_path = f"{CUSTOM_PATH}/entityDefs/Account.json"
account_defs = read_json(account_path)
if "links" not in account_defs:
    account_defs["links"] = {}
account_defs["links"]["prodotti"] = {
    "type": "hasMany",
    "entity": "Prodotto",
    "foreign": "fornitore",
    "foreignName": "name"
}
step("link Account→Prodotti", write_json(account_path, account_defs))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Rebuild cache
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("4. REBUILD CACHE")
print("="*60)

code, out = docker_exec("php /var/www/html/command.php rebuild 2>&1")
if code == 0:
    print("   ✅ cache rebuilt")
    ok += 1
else:
    print(f"   ⚠️  {out[:200]}")
    err += 1

print("\n" + "="*60)
print(f"COMPLETATO: ✅ {ok}  ❌ {err}")
print("="*60)
if err == 0:
    print("\n🎉 Ricarica EspoCRM — trovi 'Prodotto' nel menu.")
