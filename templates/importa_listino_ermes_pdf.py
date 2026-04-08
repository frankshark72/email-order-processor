#!/usr/bin/env python3
"""
Importa il listino PDF Ermes in EspoCRM come entità Prodotto.

Prerequisiti:
  pip install requests pdfplumber

Uso su Windows PowerShell:
  & "python.exe" templates\importa_listino_ermes_pdf.py "C:\percorso\listino_ermes.pdf"
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

# Codice articolo Ermes: EASY-S.1P, EASY-S.SP, ecc.
RE_CODICE = re.compile(r'^([A-Z][A-Z0-9\-\.\/]{2,})\s+(.+?)\s+([\d\.]+,\d{2})\s*$')
RE_PREZZO_FINE = re.compile(r'([\d\.]+,\d{2})\s*$')


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
    r = requests.get(f"{API_BASE}/CProdotto", headers=HEADERS, params={
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
        r = requests.patch(f"{API_BASE}/CProdotto/{existing_id}",
                           headers=HEADERS, json=payload, timeout=10)
        return "aggiornato" if r.ok else "errore"
    else:
        r = requests.post(f"{API_BASE}/CProdotto",
                          headers=HEADERS, json=payload, timeout=10)
        return "inserito" if r.ok else "errore"


def parse_pdf_ermes(file_pdf: str) -> list[dict]:
    """
    Estrae prodotti dal PDF Ermes.
    Il formato è: CODICE (una parola) + DESCRIZIONE lunga (multi-riga) + PREZZO finale.
    Le categorie sono righe senza codice/prezzo.
    """
    try:
        import pdfplumber
    except ImportError:
        print("❌ Installa pdfplumber: pip install pdfplumber")
        sys.exit(1)

    prodotti = []
    categoria_corrente = "Sistemi di comunicazione"

    # Ermes ha descrizioni multi-riga — usiamo un approccio a stati
    codice_corrente = None
    desc_corrente = []

    SKIP_PAROLE = ["pagina", "page", "listino", "www.", "rev.", "ermes", "italia",
                   "prezzo", "codice", "descrizione", "iva", "esclusa"]

    with pdfplumber.open(file_pdf) as pdf:
        for page in pdf.pages:
            testo = page.extract_text()
            if not testo:
                continue

            for riga in testo.split('\n'):
                riga = riga.strip()
                if not riga or len(riga) < 3:
                    continue

                # Salta header/footer
                if any(s in riga.lower() for s in SKIP_PAROLE):
                    continue

                # Controlla se la riga finisce con un prezzo
                m_prezzo = RE_PREZZO_FINE.search(riga)

                if m_prezzo:
                    prezzo_str = m_prezzo.group(1)
                    testo_riga = riga[:m_prezzo.start()].strip()

                    # Se abbiamo un codice aperto, questa riga chiude la descrizione
                    if codice_corrente:
                        desc_corrente.append(testo_riga)
                        descrizione_completa = " ".join(desc_corrente).strip()
                        prodotti.append({
                            "codice":    codice_corrente,
                            "name":      descrizione_completa[:255],
                            "descrizioneEstesa": descrizione_completa if len(descrizione_completa) > 255 else "",
                            "prezzo":    pulisci_prezzo(prezzo_str),
                            "categoria": categoria_corrente,
                        })
                        codice_corrente = None
                        desc_corrente = []
                    else:
                        # Prova match diretto codice + desc + prezzo in una riga
                        m = RE_CODICE.match(riga)
                        if m:
                            prodotti.append({
                                "codice":    m.group(1),
                                "name":      m.group(2).strip()[:255],
                                "descrizioneEstesa": "",
                                "prezzo":    pulisci_prezzo(m.group(3)),
                                "categoria": categoria_corrente,
                            })
                else:
                    # Riga senza prezzo
                    parole = riga.split()
                    if not parole:
                        continue

                    primo = parole[0]

                    # Sembra un codice articolo? (es. EASY-S.1P)
                    if (re.match(r'^[A-Z][A-Z0-9\-\.]{2,}$', primo) and
                            len(primo) >= 4 and len(parole) > 1):
                        # Salva prodotto precedente se incompleto (senza prezzo)
                        if codice_corrente and desc_corrente:
                            pass  # scarta prodotti senza prezzo

                        codice_corrente = primo
                        desc_corrente = [" ".join(parole[1:])]
                    elif codice_corrente:
                        # Continuazione della descrizione multi-riga
                        desc_corrente.append(riga)
                    else:
                        # Potrebbe essere una categoria
                        if 5 < len(riga) < 100 and not riga[0].isdigit():
                            categoria_corrente = riga[:80]

    return prodotti


def main():
    if len(sys.argv) < 2:
        print("Uso: python templates\\importa_listino_ermes_pdf.py <listino.pdf>")
        sys.exit(1)

    file_pdf = sys.argv[1]
    print(f"\nFile: {file_pdf}")

    print("\nCerco Ermes in EspoCRM...")
    fornitore_id = trova_fornitore("Ermes")
    if not fornitore_id:
        print("❌ Fornitore Ermes non trovato.")
        sys.exit(1)

    print("\nEstraggo prodotti dal PDF...")
    prodotti = parse_pdf_ermes(file_pdf)
    print(f"Prodotti estratti: {len(prodotti)}")

    if not prodotti:
        print("❌ Nessun prodotto estratto. Controlla il formato del PDF.")
        sys.exit(1)

    print("\nAnteprima (primi 5):")
    for p in prodotti[:5]:
        print(f"  {p['codice']} | {p['name'][:50]} | €{p['prezzo']} | {p['categoria']}")

    contatori = {"inserito": 0, "aggiornato": 0, "errore": 0}

    print(f"\nImport in corso ({len(prodotti)} prodotti)...")
    for i, p in enumerate(prodotti):
        if not p.get("codice") or not p.get("name"):
            continue

        payload = {
            "name":               p["name"],
            "codice":             p["codice"],
            "categoria":          p["categoria"],
            "descrizioneEstesa":  p.get("descrizioneEstesa", ""),
            "unitaMisura":        "pz",
            "attivo":             True,
            "fornitoreId":        fornitore_id,
        }
        if p.get("prezzo") is not None:
            payload["prezzoListino"] = p["prezzo"]

        risultato = salva_prodotto(payload)
        contatori[risultato] += 1

        if (i + 1) % 20 == 0:
            print(f"   ... {i + 1}/{len(prodotti)} processati")
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"TOTALE Ermes:")
    print(f"  ✅ Inseriti:   {contatori['inserito']}")
    print(f"  🔄 Aggiornati: {contatori['aggiornato']}")
    print(f"  ❌ Errori:     {contatori['errore']}")
    print("="*50)


if __name__ == "__main__":
    main()
