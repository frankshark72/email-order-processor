#!/usr/bin/env python3
"""
Genera il file Excel template per l'import clienti in EspoCRM.

Uso:
  pip install openpyxl
  python3 templates/genera_template_excel.py
  → crea templates/import_clienti.xlsx
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# ── Foglio 1: Template da compilare ──────────────────────────────────────────
ws = wb.active
ws.title = "Clienti"

# Colonne: (nome_api_espocrm, etichetta_italiana, esempio, note)
COLUMNS = [
    ("name",                    "Ragione Sociale *",        "Rossi Srl",            "OBBLIGATORIO"),
    ("emailAddress",            "Email",                    "info@rossi.it",        ""),
    ("phoneNumber",             "Telefono",                 "0832-123456",          ""),
    ("billingAddressStreet",    "Via / Indirizzo",          "Via Roma 1",           ""),
    ("billingAddressCity",      "Città",                    "Lecce",                ""),
    ("billingAddressPostalCode","CAP",                      "73100",                ""),
    ("zona",                    "Zona",                     "Leccese",              "Es: Barese, Leccese, Foggiano, Tarantino, Brindisino"),
    ("tipoAccount",             "Tipo",                     "cliente",              "Valori: cliente / fornitore / prospect"),
    ("frequenzaVisitaGiorni",   "Frequenza Visita (giorni)","30",                   "Ogni quanti giorni visitarlo. 0 = fornitore"),
    ("referente",               "Referente",                "Mario Rossi",          "Nome persona di contatto"),
    ("priorita",                "Priorità",                 "alta",                 "Valori: alta / media / bassa"),
    ("condizioniPagamento",     "Condizioni Pagamento",     "Netto 30",             "Es: Netto 30, Netto 60, Rimessa Diretta"),
    ("latitudine",              "Latitudine",               "40.3516",              "Coordinate GPS (opzionale, per Google Maps)"),
    ("longitudine",             "Longitudine",              "18.1750",              "Coordinate GPS (opzionale, per Google Maps)"),
    ("website",                 "Sito Web",                 "www.rossi.it",         ""),
    ("description",             "Note",                     "Cliente storico",      "Note libere"),
]

# Stili
HEADER_API_FILL   = PatternFill("solid", fgColor="1F4E79")  # blu scuro = nome API
HEADER_IT_FILL    = PatternFill("solid", fgColor="2E75B6")  # blu = etichetta italiana
EXAMPLE_FILL      = PatternFill("solid", fgColor="D6E4F0")  # azzurro chiaro = esempio
NOTE_FILL         = PatternFill("solid", fgColor="FFF2CC")  # giallo = note
WHITE_FONT        = Font(color="FFFFFF", bold=True, size=10)
DARK_FONT         = Font(color="1F4E79", size=10)
NOTE_FONT         = Font(color="7F6000", italic=True, size=9)
BORDER            = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin")
)

# Riga 1: nomi campo API (per import EspoCRM)
for col_idx, (api_name, _, _, _) in enumerate(COLUMNS, 1):
    cell = ws.cell(row=1, column=col_idx, value=api_name)
    cell.fill = HEADER_API_FILL
    cell.font = WHITE_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BORDER

# Riga 2: etichette italiane
for col_idx, (_, label, _, _) in enumerate(COLUMNS, 1):
    cell = ws.cell(row=2, column=col_idx, value=label)
    cell.fill = HEADER_IT_FILL
    cell.font = WHITE_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER

# Riga 3: esempi
for col_idx, (_, _, example, _) in enumerate(COLUMNS, 1):
    cell = ws.cell(row=3, column=col_idx, value=example)
    cell.fill = EXAMPLE_FILL
    cell.font = DARK_FONT
    cell.alignment = Alignment(horizontal="left", vertical="center")
    cell.border = BORDER

# Riga 4: note sui valori
for col_idx, (_, _, _, note) in enumerate(COLUMNS, 1):
    cell = ws.cell(row=4, column=col_idx, value=note)
    cell.fill = NOTE_FILL
    cell.font = NOTE_FONT
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    cell.border = BORDER

# Righe dati (5 in poi) — 20 righe vuote predisposte
DATA_FILL = PatternFill("solid", fgColor="F5F9FF")
for row_idx in range(5, 25):
    for col_idx in range(1, len(COLUMNS) + 1):
        cell = ws.cell(row=row_idx, column=col_idx, value="")
        cell.fill = DATA_FILL
        cell.font = Font(size=10)
        cell.border = BORDER
        cell.alignment = Alignment(horizontal="left", vertical="center")

# Altezze righe
ws.row_dimensions[1].height = 20   # API names
ws.row_dimensions[2].height = 30   # Etichette
ws.row_dimensions[3].height = 20   # Esempi
ws.row_dimensions[4].height = 35   # Note
for r in range(5, 25):
    ws.row_dimensions[r].height = 20

# Larghezze colonne
COL_WIDTHS = [25,22,16,25,16,8,14,12,10,12,10,20,12,12,20,25]
for i, w in enumerate(COL_WIDTHS, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

# Blocca le prime 4 righe durante lo scroll
ws.freeze_panes = "A5"

# ── Foglio 2: Istruzioni import EspoCRM ──────────────────────────────────────
ws2 = wb.create_sheet("Istruzioni Import")
istruzioni = [
    ("COME IMPORTARE IN ESPOCRM", ""),
    ("", ""),
    ("1. COMPILA IL FOGLIO 'Clienti'", ""),
    ("   • Riempi i dati dal rigo 5 in poi", ""),
    ("   • La riga 1 (API names) viene usata per il mapping automatico", ""),
    ("   • Non modificare la riga 1", ""),
    ("", ""),
    ("2. ESPORTA COME CSV", ""),
    ("   • File → Salva con nome → CSV (delimitato da virgole)", ""),
    ("   • Salva SOLO il foglio 'Clienti'", ""),
    ("", ""),
    ("3. IMPORTA IN ESPOCRM", ""),
    ("   • Vai su EspoCRM → Account → menu in alto a destra → Import", ""),
    ("   • Carica il CSV", ""),
    ("   • Metti la spunta su 'Header row' (prima riga = nomi campo)", ""),
    ("   • EspoCRM mapperà automaticamente le colonne se i nomi API coincidono", ""),
    ("   • Clicca Next → Next → Import", ""),
    ("", ""),
    ("4. VALORI ENUM VALIDI", ""),
    ("   tipoAccount:  cliente | fornitore | prospect", ""),
    ("   priorita:     alta | media | bassa", ""),
    ("", ""),
    ("5. COORDINATE GPS (latitudine/longitudine)", ""),
    ("   • Vai su Google Maps → cerca l'indirizzo → tasto destro → 'Che cosa c'è qui?'", ""),
    ("   • Copia le coordinate (es. 40.3516, 18.1750)", ""),
    ("   • latitudine = primo numero, longitudine = secondo", ""),
]
for row_idx, (testo, _) in enumerate(istruzioni, 1):
    cell = ws2.cell(row=row_idx, column=1, value=testo)
    if testo and not testo.startswith(" ") and not testo.startswith("   "):
        cell.font = Font(bold=True, color="1F4E79", size=11)
    else:
        cell.font = Font(size=10)

ws2.column_dimensions["A"].width = 70

# Salva
out = "templates/import_clienti.xlsx"
wb.save(out)
print(f"✅ Template Excel creato: {out}")
print("   Aprilo, compila dal rigo 5, esporta come CSV e importa in EspoCRM.")
