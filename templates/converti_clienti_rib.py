#!/usr/bin/env python3
"""
Converte il CSV clienti della mandante nel formato import EspoCRM.

Uso:
  python3 templates/converti_clienti_rib.py clienti_rib.csv
  → genera templates/import_espocrm_clienti.csv
"""

import sys
import csv
import os

# Mappa province → zona Puglia (personalizzabile)
ZONE = {
    "BA": "Barese",
    "BT": "Barese",
    "BR": "Brindisino",
    "LE": "Leccese",
    "TA": "Tarantino",
    "FG": "Foggiano",
    "KR": "Calabria",
    "CS": "Calabria",
    "CZ": "Calabria",
    "RC": "Calabria",
    "NA": "Campania",
    "SA": "Campania",
    "AV": "Campania",
    "BN": "Campania",
    "CE": "Campania",
    "MI": "Nord",
    "TO": "Nord",
    "RM": "Centro",
}

def zona_da_provincia(prov: str) -> str:
    return ZONE.get((prov or "").strip().upper(), "")

def pulisci_tel(tel: str) -> str:
    """Normalizza numero telefono."""
    t = (tel or "").strip().replace(" ", "").replace("-", "")
    if t and not t.startswith("+") and not t.startswith("0"):
        t = "0" + t
    return t

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 templates/converti_clienti_rib.py <file_input.csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = os.path.join(os.path.dirname(input_file),
                               "import_espocrm_clienti.csv")

    # Prova diversi separatori (tab, punto e virgola, virgola)
    separatori = ["\t", ";", ","]
    righe = []
    separatore_usato = "\t"

    for sep in separatori:
        with open(input_file, encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=sep)
            righe = list(reader)
            if len(righe) > 0 and len(righe[0]) > 3:
                separatore_usato = sep
                break

    if not righe:
        print("❌ File vuoto o formato non riconosciuto.")
        sys.exit(1)

    print(f"✅ Lette {len(righe)} righe (separatore: {repr(separatore_usato)})")
    print(f"   Colonne trovate: {list(righe[0].keys())[:5]}...")

    # Colonne output EspoCRM
    fieldnames = [
        "name", "emailAddress", "phoneNumber",
        "billingAddressStreet", "billingAddressCity",
        "billingAddressState", "billingAddressPostalCode",
        "billingAddressCountry",
        "zona", "tipoAccount", "referente",
        "condizioniPagamento", "priorita",
        "frequenzaVisitaGiorni", "description",
    ]

    scritti = 0
    saltati = 0

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in righe:
            nome = (r.get("RagioneSociale") or "").strip()
            if not nome:
                saltati += 1
                continue

            # Telefono: preferisci cellulare se disponibile
            tel_fisso = pulisci_tel(r.get("Telefono1") or "")
            tel_cell  = pulisci_tel(r.get("Telcellulare") or "")
            telefono  = tel_cell if tel_cell else tel_fisso

            # Note: metti partita IVA e codice conto nelle note
            id_conto = (r.get("IdConto") or "").strip()
            piva = (r.get("PartitaIVA") or "").strip()
            note_parts = []
            if id_conto:
                note_parts.append(f"Codice conto: {id_conto}")
            if piva:
                note_parts.append(f"P.IVA: {piva}")
            if tel_fisso and tel_cell:
                note_parts.append(f"Tel fisso: {tel_fisso}")

            prov = (r.get("idprovincia_1") or "").strip().upper()

            writer.writerow({
                "name":                     nome,
                "emailAddress":             (r.get("email_1") or "").strip(),
                "phoneNumber":              telefono,
                "billingAddressStreet":     (r.get("indirizzo_1") or "").strip().title(),
                "billingAddressCity":       (r.get("localita_1") or "").strip().title(),
                "billingAddressState":      prov,
                "billingAddressPostalCode": (r.get("idcap_1") or "").strip(),
                "billingAddressCountry":    "Italia",
                "zona":                     zona_da_provincia(prov),
                "tipoAccount":              "cliente",
                "referente":                (r.get("Contatto") or "").strip().title(),
                "condizioniPagamento":      (r.get("Dspagamento") or "").strip(),
                "priorita":                 "media",
                "frequenzaVisitaGiorni":    "30",
                "description":             " | ".join(note_parts),
            })
            scritti += 1

    print(f"✅ Convertiti {scritti} clienti → {output_file}")
    if saltati:
        print(f"   ⏭  {saltati} righe saltate (nome vuoto)")
    print(f"\nProssimo passo:")
    print(f"  EspoCRM → Account → Import → carica {os.path.basename(output_file)}")
    print(f"  Spunta 'Header row' → Next → Import")

if __name__ == "__main__":
    main()
