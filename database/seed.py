"""
Seed the database with example data.
Run: python -m database.seed
"""

from .models import init_db
from .manager import upsert_cliente, upsert_articolo, upsert_listino, upsert_azienda


def seed():
    init_db()

    # --- Aziende destinatarie ---
    az1 = upsert_azienda("Fornitore Alfa Srl", "ordini@fornitore-alfa.it", "Fornitore principale")
    az2 = upsert_azienda("Beta Distribuzione", "acquisti@beta-dist.it")

    # --- Articoli ---
    art1 = upsert_articolo("ART001", "Maglietta tecnica running", "pz")
    art2 = upsert_articolo("ART002", "Pantaloncino ciclismo", "pz")
    art3 = upsert_articolo("ART003", "Scarpe trail taglia 42", "paia")
    art4 = upsert_articolo("ART004", "Borraccia 750ml", "pz")
    art5 = upsert_articolo("ART005", "Casco ciclismo S/M", "pz")

    # --- Clienti ---
    c1 = upsert_cliente("CLI001", "Mario Rossi", "mario.rossi@email.it",
                         "Rossi Sport", "Cliente gold")
    c2 = upsert_cliente("CLI002", "Anna Bianchi", "anna.bianchi@gmail.com",
                         "Bianchi Atletica", "Cliente silver")
    c3 = upsert_cliente("CLI003", "Luigi Verdi", "luigi.verdi@negozio.it",
                         "Verdi Outdoor")

    # --- Listini (prezzi personalizzati per cliente) ---
    # Mario Rossi - prezzi gold (scontati)
    upsert_listino(c1, art1, 18.00, sconto_pct=10)   # 16.20 netto
    upsert_listino(c1, art2, 35.00, sconto_pct=15)   # 29.75 netto
    upsert_listino(c1, art3, 95.00, sconto_pct=10)
    upsert_listino(c1, art4, 8.50)
    upsert_listino(c1, art5, 60.00, sconto_pct=5)

    # Anna Bianchi - prezzi silver
    upsert_listino(c2, art1, 20.00)
    upsert_listino(c2, art2, 38.00)
    upsert_listino(c2, art4, 9.00)

    # Luigi Verdi - prezzi standard
    upsert_listino(c3, art1, 22.00)
    upsert_listino(c3, art3, 105.00)
    upsert_listino(c3, art5, 68.00)

    print("[SEED] Dati di esempio inseriti nel database.")
    print(f"       Clienti: 3, Articoli: 5, Listini: {5+3+3} righe")
    print(f"       Aziende destinatarie: 2")


if __name__ == "__main__":
    seed()
