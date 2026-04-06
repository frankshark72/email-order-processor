#!/usr/bin/env python3
"""
Importa il listino Excel Elmo in EspoCRM come entità Prodotto.
Legge i 4 fogli: Intrusione, Antincendio, TVCC, Controllo Accessi.

Prerequisiti:
  pip install requests openpyxl

Uso su Windows CMD:
  set ESPOCRM_URL=http://100.79.250.23:8080
  set ESPOCRM_API_KEY=42f83e62ee977187aa76d2e701bb6fcc
  python templates\importa_listino_elmo.py "C:\percorso\listino_elmo.xlsx"
"""

import sys
import os
import time
import requests
import openpyxl

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "42f83e62ee977187aa76d2e701bb6fcc")
API_BASE = f"{ESPOCRM_URL}/api/v1"
HEADERS = {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}

# Mappa nome foglio → valore categoria
FOGLI = {
    "Intrusione":        "Intrusione",
    "Antincendio":       "Antincendio",
    "TVCC":              "TVCC",
    "Controllo Accessi": "Controllo Accessi",
}


def trova_fornitore_elmo() -> str | None:
    """Cerca l'account Elmo in EspoCRM."""
    r = requests.get(f"{API_BASE}/Account",
                     headers=HEADERS,
                     params={
                         "maxSize": 5,
                         "select": "id,name",
                         "where[0][type]": "contains",
                         "where[0][attribute]": "name",
                         "where[0][value]": "Elmo",
                     }, timeout=10)
    if not r.ok:
        return None
    lst = r.json().get("list", [])
    if lst:
        print(f"   Fornitore trovato: {lst[0]['name']} (id: {lst[0]['id']})")
        return lst[0]["id"]
    return None


def cerca_prodotto(codice: str) -> str | None:
    """Cerca prodotto per codice, ritorna ID se esiste."""
    r = requests.get(f"{API_BASE}/Prodotto",
                     headers=HEADERS,
                     params={
                         "maxSize": 1,
                         "select": "id,name",
                         "where[0][type]": "equals",
                         "where[0][attribute]": "codice",
                         "where[0][value]": codice,
                     }, timeout=10)
    if not r.ok or r.status_code == 404:
        return None
    lst = r.json().get("list", [])
    return lst[0]["id"] if lst else None


def pulisci_prezzo(val) -> float | None:
    """Converte '€ 25,00' o '25.00' in float."""
    if val is None:
        return None
    s = str(val).strip().replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def importa_foglio(ws, categoria: str, fornitore_id: str, aggiorna: bool = True) -> tuple[int, int, int]:
    """Importa tutte le righe di un foglio Excel. Ritorna (inseriti, aggiornati, saltati)."""
    inseriti = 0
    aggiornati = 0
    saltati = 0

    # Trova riga header (contiene "Prodotto" o "Descrizione")
    header_row = None
    col_map = {}
    for row in ws.iter_rows(max_row=10):
        vals = [str(c.value or "").strip() for c in row]
        if "Prodotto" in vals or "Descrizione breve" in vals:
            header_row = row[0].row
            for cell in row:
                v = str(cell.value or "").strip()
                col_map[v] = cell.column - 1  # indice 0
            break

    if header_row is None:
        print(f"   ⚠️  Header non trovato nel foglio {categoria}")
        return 0, 0, 0

    print(f"   Header riga {header_row}, colonne: {list(col_map.keys())}")

    rows = list(ws.iter_rows(min_row=header_row + 1, values_only=True))

    for i, row in enumerate(rows):
        if not any(row):
            continue

        def get(col_name):
            idx = col_map.get(col_name)
            if idx is None:
                return None
            return row[idx] if idx < len(row) else None

        codice = str(get("Prodotto") or "").strip()
        if not codice:
            saltati += 1
            continue

        descrizione = str(get("Descrizione breve") or "").strip()
        if not descrizione:
            saltati += 1
            continue

        codice_alfa = str(get("Alfanumerico") or "").strip()
        disponibilita = str(get("Disponibilità") or "").strip()
        cr = str(get("CR") or "").strip()
        garanzia = str(get("G") or "").strip()

        prezzo_raw = get("Prezzo")
        prezzo_su_richiesta = False
        prezzo = None

        if str(prezzo_raw or "").strip().lower().startswith("prezzo su"):
            prezzo_su_richiesta = True
        else:
            prezzo = pulisci_prezzo(prezzo_raw)

        payload = {
            "name":                descrizione,
            "codice":              codice,
            "codiceAlfanumerico":  codice_alfa,
            "categoria":           categoria,
            "disponibilita":       disponibilita,
            "codiceRiparazione":   cr,
            "garanzia":            garanzia,
            "prezzoSuRichiesta":   prezzo_su_richiesta,
            "attivo":              True,
            "fornitoreId":         fornitore_id,
        }
        if prezzo is not None:
            payload["prezzoListino"] = prezzo

        # Verifica se esiste già
        existing_id = cerca_prodotto(codice)

        if existing_id and not aggiorna:
            saltati += 1
            continue

        if existing_id:
            r = requests.patch(f"{API_BASE}/Prodotto/{existing_id}",
                               headers=HEADERS, json=payload, timeout=10)
            if r.ok:
                aggiornati += 1
            else:
                print(f"   ❌ Aggiornamento {codice}: {r.status_code} {r.text[:100]}")
                saltati += 1
        else:
            r = requests.post(f"{API_BASE}/Prodotto",
                              headers=HEADERS, json=payload, timeout=10)
            if r.ok:
                inseriti += 1
            else:
                print(f"   ❌ Inserimento {codice}: {r.status_code} {r.text[:100]}")
                saltati += 1

        if (inseriti + aggiornati) % 20 == 0 and (inseriti + aggiornati) > 0:
            print(f"      ... {inseriti + aggiornati} prodotti processati")
            time.sleep(0.5)

    return inseriti, aggiornati, saltati


def main():
    if len(sys.argv) < 2:
        print("Uso: python templates\\importa_listino_elmo.py <listino_elmo.xlsx>")
        sys.exit(1)

    file_xlsx = sys.argv[1]

    print(f"\nApertura file: {file_xlsx}")
    try:
        wb = openpyxl.load_workbook(file_xlsx, data_only=True)
    except Exception as e:
        print(f"❌ Errore apertura file: {e}")
        sys.exit(1)

    print(f"Fogli trovati: {wb.sheetnames}")

    # Trova Elmo in EspoCRM
    print("\nCerco fornitore Elmo in EspoCRM...")
    fornitore_id = trova_fornitore_elmo()
    if not fornitore_id:
        print("❌ Fornitore Elmo non trovato in EspoCRM. Verificare che esista come Account.")
        sys.exit(1)

    totale_inseriti = 0
    totale_aggiornati = 0
    totale_saltati = 0

    for nome_foglio, categoria in FOGLI.items():
        # Cerca foglio con nome simile (case insensitive)
        ws = None
        for sheet_name in wb.sheetnames:
            if nome_foglio.lower() in sheet_name.lower():
                ws = wb[sheet_name]
                break

        if ws is None:
            print(f"\n⚠️  Foglio '{nome_foglio}' non trovato, salto.")
            continue

        print(f"\n{'='*50}")
        print(f"Foglio: {sheet_name} → categoria: {categoria}")
        print("="*50)

        ins, agg, sal = importa_foglio(ws, categoria, fornitore_id)
        totale_inseriti += ins
        totale_aggiornati += agg
        totale_saltati += sal
        print(f"   ✅ Inseriti: {ins}  🔄 Aggiornati: {agg}  ⏭  Saltati: {sal}")

    print(f"\n{'='*50}")
    print(f"TOTALE:")
    print(f"  ✅ Inseriti:   {totale_inseriti}")
    print(f"  🔄 Aggiornati: {totale_aggiornati}")
    print(f"  ⏭  Saltati:    {totale_saltati}")
    print("="*50)


if __name__ == "__main__":
    main()
