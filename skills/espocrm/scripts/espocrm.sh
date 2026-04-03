#!/usr/bin/env bash
# EspoCRM REST API helper script for OpenClaw skill.
# Usage: espocrm.sh <command> [args...]
#
# Requires: ESPOCRM_URL, ESPOCRM_API_KEY

set -euo pipefail

BASE="${ESPOCRM_URL%/}/api/v1"
AUTH_HEADER="X-Api-Key: ${ESPOCRM_API_KEY}"

_curl() {
  curl -sS -H "$AUTH_HEADER" -H "Content-Type: application/json" "$@"
}

cmd="${1:-help}"
shift || true

case "$cmd" in

  # ── Query ──────────────────────────────────────────────────────
  search)
    # search <Entity> <field> <value>
    entity="$1"; field="$2"; value="$3"
    _curl "${BASE}/${entity}?where%5B0%5D%5Btype%5D=contains&where%5B0%5D%5Bfield%5D=${field}&where%5B0%5D%5Bvalue%5D=${value}&maxSize=20"
    ;;

  search-exact)
    # search-exact <Entity> <field> <value>
    entity="$1"; field="$2"; value="$3"
    _curl "${BASE}/${entity}?where%5B0%5D%5Btype%5D=equals&where%5B0%5D%5Bfield%5D=${field}&where%5B0%5D%5Bvalue%5D=${value}&maxSize=10"
    ;;

  get)
    # get <Entity> <id>
    entity="$1"; id="$2"
    _curl "${BASE}/${entity}/${id}"
    ;;

  list)
    # list <Entity> [maxSize] [orderBy]
    entity="$1"; max="${2:-20}"; order="${3:-name}"
    _curl "${BASE}/${entity}?maxSize=${max}&orderBy=${order}"
    ;;

  # ── Create / Update ────────────────────────────────────────────
  create)
    # create <Entity> <json_data>
    entity="$1"; data="$2"
    _curl -X POST "${BASE}/${entity}" -d "$data"
    ;;

  update)
    # update <Entity> <id> <json_data>
    entity="$1"; id="$2"; data="$3"
    _curl -X PUT "${BASE}/${entity}/${id}" -d "$data"
    ;;

  # ── Clienti (Account) ─────────────────────────────────────────
  find-cliente)
    # find-cliente <nome_o_email>
    query="$1"
    # Try by name first, then by email
    result=$(_curl "${BASE}/Account?where%5B0%5D%5Btype%5D=contains&where%5B0%5D%5Bfield%5D=name&where%5B0%5D%5Bvalue%5D=${query}&maxSize=5")
    total=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo 0)
    if [ "$total" = "0" ]; then
      _curl "${BASE}/Account?where%5B0%5D%5Btype%5D=contains&where%5B0%5D%5Bfield%5D=emailAddress&where%5B0%5D%5Bvalue%5D=${query}&maxSize=5"
    else
      echo "$result"
    fi
    ;;

  clienti-zona)
    # clienti-zona <zona>
    zona="$1"
    _curl "${BASE}/Account?where%5B0%5D%5Btype%5D=equals&where%5B0%5D%5Bfield%5D=zona&where%5B0%5D%5Bvalue%5D=${zona}&where%5B1%5D%5Btype%5D=equals&where%5B1%5D%5Bfield%5D=tipoAccount&where%5B1%5D%5Bvalue%5D=cliente&maxSize=50&orderBy=name"
    ;;

  zone)
    # zone — list all unique zones
    _curl "${BASE}/Account?where%5B0%5D%5Btype%5D=equals&where%5B0%5D%5Bfield%5D=tipoAccount&where%5B0%5D%5Bvalue%5D=cliente&select=zona,name&maxSize=200&orderBy=zona" \
      | python3 -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
zones = Counter(r.get('zona','Senza zona') or 'Senza zona' for r in data.get('list',[]))
for z, count in sorted(zones.items()):
    print(f'{z}: {count} clienti')
"
    ;;

  # ── Visite (Meeting) ──────────────────────────────────────────
  ultima-visita)
    # ultima-visita <account_id>
    account_id="$1"
    _curl "${BASE}/Meeting?where%5B0%5D%5Btype%5D=equals&where%5B0%5D%5Bfield%5D=parentId&where%5B0%5D%5Bvalue%5D=${account_id}&where%5B1%5D%5Btype%5D=equals&where%5B1%5D%5Bfield%5D=parentType&where%5B1%5D%5Bvalue%5D=Account&where%5B2%5D%5Btype%5D=equals&where%5B2%5D%5Bfield%5D=status&where%5B2%5D%5Bvalue%5D=Held&orderBy=dateStart&order=desc&maxSize=1"
    ;;

  registra-visita)
    # registra-visita <account_id> <note>
    account_id="$1"; note="${2:-Visita}"
    today=$(date +%Y-%m-%d)
    now=$(date +"%Y-%m-%d %H:%M:%S")
    _curl -X POST "${BASE}/Meeting" -d "{
      \"name\": \"Visita ${today}\",
      \"dateStart\": \"${now}\",
      \"dateEnd\": \"${now}\",
      \"status\": \"Held\",
      \"description\": \"${note}\",
      \"parentType\": \"Account\",
      \"parentId\": \"${account_id}\"
    }"
    ;;

  # ── Chiamate (Call) ────────────────────────────────────────────
  registra-chiamata)
    # registra-chiamata <account_id> <direzione:in|out> <durata_minuti> <note>
    account_id="$1"; direction="${2:-out}"; duration="${3:-0}"; note="${4:-}"
    now=$(date +"%Y-%m-%d %H:%M:%S")
    _curl -X POST "${BASE}/Call" -d "{
      \"name\": \"Chiamata\",
      \"dateStart\": \"${now}\",
      \"status\": \"Held\",
      \"direction\": \"${direction}\",
      \"duration\": ${duration},
      \"description\": \"${note}\",
      \"parentType\": \"Account\",
      \"parentId\": \"${account_id}\"
    }"
    ;;

  # ── Task ───────────────────────────────────────────────────────
  crea-task)
    # crea-task <nome> <scadenza_YYYY-MM-DD> [account_id]
    nome="$1"; scadenza="$2"; account_id="${3:-}"
    data="{\"name\": \"${nome}\", \"dateEnd\": \"${scadenza} 09:00:00\", \"status\": \"Not Started\""
    if [ -n "$account_id" ]; then
      data="${data}, \"parentType\": \"Account\", \"parentId\": \"${account_id}\""
    fi
    data="${data}}"
    _curl -X POST "${BASE}/Task" -d "$data"
    ;;

  task-oggi)
    # task-oggi — tasks due today
    today=$(date +%Y-%m-%d)
    _curl "${BASE}/Task?where%5B0%5D%5Btype%5D=on&where%5B0%5D%5Bfield%5D=dateEnd&where%5B0%5D%5Bvalue%5D=${today}&where%5B1%5D%5Btype%5D=notIn&where%5B1%5D%5Bfield%5D=status&where%5B1%5D%5Bvalue%5D%5B%5D=Completed&where%5B1%5D%5Bvalue%5D%5B%5D=Canceled&maxSize=50"
    ;;

  # ── Note ───────────────────────────────────────────────────────
  aggiungi-nota)
    # aggiungi-nota <account_id> <tipo:whatsapp|generico> <testo>
    account_id="$1"; tipo="${2:-generico}"; testo="$3"
    _curl -X POST "${BASE}/Note" -d "{
      \"type\": \"Post\",
      \"post\": \"[${tipo}] ${testo}\",
      \"parentType\": \"Account\",
      \"parentId\": \"${account_id}\"
    }"
    ;;

  # ── Help ───────────────────────────────────────────────────────
  help|*)
    cat <<'HELP'
EspoCRM API helper — Comandi:

  Clienti:
    find-cliente <nome_o_email>
    clienti-zona <zona>
    zone

  Visite:
    ultima-visita <account_id>
    registra-visita <account_id> <note>

  Chiamate:
    registra-chiamata <account_id> <in|out> <durata_min> <note>

  Task:
    crea-task <nome> <scadenza> [account_id]
    task-oggi

  Note:
    aggiungi-nota <account_id> <whatsapp|generico> <testo>

  Generici:
    search <Entity> <field> <value>
    search-exact <Entity> <field> <value>
    get <Entity> <id>
    list <Entity> [maxSize] [orderBy]
    create <Entity> <json>
    update <Entity> <id> <json>
HELP
    ;;

esac
