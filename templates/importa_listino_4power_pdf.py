#!/usr/bin/env python3
"""
Importa il listino PDF 4Power in EspoCRM come entità Prodotto.

Prerequisiti:
  pip install requests pdfplumber

Uso su Windows PowerShell:
  & "python.exe" templates\importa_listino_4power_pdf.py "C:\percorso\listino_4power.pdf"
"""

import sys
import os
import re
import time
import requests

ESPOCRM_URL = os.environ.get("ESPOCRM_URL", "http://100.79.250.23:8080").rstrip("/")
ESPOCRM_API_KEY = os.environ.get("ESPOCRM_API_KEY", "42f83e62ee977187aa76d2e701bb6fcc")
API_BASE = f"{ESPOCRM_URL}/api/v1"
HEADERS = {"X-Api-Key": ESPOCRM_API_KEY, "Content-Type": "application/json"}

# Regex per riconoscere un codice articolo (tutto maiuscolo, alfanumerico)
RE_CODICE = re.compile(r'^([A-Z0-9][A-Z0-9/\-\.]{3,})\s+(.+?)\s+([\d\.]+,\d{2})\s*$')
# Regex per il prezzo finale (es. 89,00 o 1.234,00)
RE_PREZZO = re.compile(r'([\d\.]+,\d{2})\s*$')


def trova_fornitore(nome: str) -> str | None:
    r = requests.get(f"{API_BASE}/Account", headers=HEADERS, params={
        "maxSize": 5, "select": "id,name",
        "where[0][type]": "contains",
        "where[0][attribute]": "name",
        "where[0][value]": nome,
    }, timeout=10)
    if not r.ok:
        return None
    lst = r.json().get("list", [])
    if lst:
        print(f"   Fornitore: {lst[0]['name']} (id: {lst[0]['id']})")
        return lst[0]["id"]
    return None


def cerca_prodotto(codice: str) -> str | None:
    r = requests.get(f"{API_BASE}/Prodotto", headers=HEADERS, params={
        "maxSize": 1, "select": "id",
        "where[0][type]": "equals",
        "where[0][attribute]": "codice",
        "where[0][value]": codice,
    }, timeout=10)
    if not r.ok or r.status_code == 404:
        return None
    lst = r.json().get("list", [])
    return lst[0]["id"] if lst else None


def pulisci_prezzo(val: str) -> float | None:
    s = val.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def salva_prodotto(payload: dict) -> str:
    codice = payload.get("codice", "")
    existing_id = cerca_prodotto(codice) if codice else None
    if existing_id:
        r = requests.patch(f"{API_BASE}/Prodotto/{existing_id}",
                           headers=HEADERS, json=payload, timeout=10)
        return "aggiornato" if r.ok else "errore"
    else:
        r = requests.post(f"{API_BASE}/Prodotto",
                          headers=HEADERS, json=payload, timeout=10)
        return "inserito" if r.ok else "errore"


def parse_pdf(file_pdf: str) -> list[dict]:
    """Estrae prodotti dal PDF 4Power."""
    try:
        import pdfplumber
    except ImportError:
        print("❌ Installa pdfplumber: pip install pdfplumber")
        sys.exit(1)

    prodotti = []
    categoria_corrente = "UPS"

    with pdfplumber.open(file_pdf) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            testo = page.extract_text()
            if not testo:
                continue

            for riga in testo.split('\n'):
                riga = riga.strip()
                if not riga:
                    continue

                # Prova a fare match con pattern codice + descrizione + prezzo
                m = RE_CODICE.match(riga)
                if m:
                    codice = m.group(1).strip()
                    descrizione = m.group(2).strip()
                    prezzo_raw = m.group(3).strip()
                    prezzo = pulisci_prezzo(prezzo_raw)

                    prodotti.append({
                        "codice": codice,
                        "name": descrizione[:255],
                        "prezzo": prezzo,
                        "categoria": categoria_corrente,
                    })
                    continue

                # Riga senza prezzo = possibile categoria
                if not RE_PREZZO.search(riga) and len(riga) > 5 and len(riga) < 80:
                    # Esclude righe che sembrano header/piè di pagina
                    if not any(skip in riga.lower() for skip in ["pagina", "page", "listino", "www.", "rev."]):
                        # Se non inizia con codice, potrebbe essere categoria
                        primo = riga.split()[0] if riga.split() else ""
                        if not RE_CODICE.match(riga) and primo.isupper() and len(primo) < 4:
                            pass  # ignora numeri pagina etc
                        elif len(riga) > 10 and not primo[0].isdigit():
                            categoria_corrente = riga[:80]

    return prodotti


def main():
    if len(sys.argv) < 2:
        print("Uso: python templates\\importa_listino_4power_pdf.py <listino.pdf>")
        sys.exit(1)

    file_pdf = sys.argv[1]
    print(f"\nFile: {file_pdf}")

    print("\nCerco 4Power in EspoCRM...")
    fornitore_id = trova_fornitore("4Power")
    if not fornitore_id:
        fornitore_id = trova_fornitore("4power")
    if not fornitore_id:
        print("❌ Fornitore 4Power non trovato.")
        sys.exit(1)

    print("\nEstraggo prodotti dal PDF...")
    prodotti = parse_pdf(file_pdf)
    print(f"Prodotti trovati: {len(prodotti)}")

    if not prodotti:
        print("❌ Nessun prodotto estratto. Controlla il formato del PDF.")
        sys.exit(1)

    # Mostra anteprima
    print("\nAnteprima (primi 5):")
    for p in prodotti[:5]:
        print(f"  {p['codice']} | {p['name'][:50]} | €{p['prezzo']} | {p['categoria']}")

    contatori = {"inserito": 0, "aggiornato": 0, "errore": 0}

    print(f"\nImport in corso...")
    for i, p in enumerate(prodotti):
        if not p.get("codice") or not p.get("name"):
            continue

        payload = {
            "name":        p["name"],
            "codice":      p["codice"],
            "categoria":   p["categoria"],
            "unitaMisura": "pz",
            "attivo":      True,
            "fornitoreId": fornitore_id,
        }
        if p.get("prezzo") is not None:
            payload["prezzoListino"] = p["prezzo"]

        risultato = salva_prodotto(payload)
        contatori[risultato] += 1

        if (i + 1) % 20 == 0:
            print(f"   ... {i + 1}/{len(prodotti)} processati")
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"TOTALE 4Power:")
    print(f"  ✅ Inseriti:   {contatori['inserito']}")
    print(f"  🔄 Aggiornati: {contatori['aggiornato']}")
    print(f"  ❌ Errori:     {contatori['errore']}")
    print("="*50)


if __name__ == "__main__":
    main()
