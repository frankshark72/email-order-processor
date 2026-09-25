---
name: briefing
description: Riassunto mattutino giornaliero e risposta a "cosa devo fare oggi?". Usa questa skill quando l'utente chiede il briefing, il riassunto della giornata, cosa deve fare, o quando è il cron mattutino delle 8:00.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - ESPOCRM_URL
        - ESPOCRM_API_KEY
      bins:
        - curl
        - python3
    primaryEnv: ESPOCRM_API_KEY
    emoji: "☀️"
---

# Briefing — Riassunto Giornaliero

Genera un briefing mattutino completo per un commerciale B2B in Puglia.
Combina dati da EspoCRM (task, clienti, visite, ordini) in un unico messaggio.

## Setup

Usa lo script EspoCRM: `{baseDir}/../espocrm/scripts/espocrm.sh`

## Workflow: Briefing mattutino

Quando l'utente chiede "cosa devo fare oggi?", "briefing", "buongiorno",
o quando viene attivato dal cron mattutino:

### Step 1 — Task in scadenza oggi
```bash
{baseDir}/../espocrm/scripts/espocrm.sh task-oggi
```

### Step 2 — Ordini in attesa di conferma
```bash
{baseDir}/../espocrm/scripts/espocrm.sh search-exact OrdineEmail stato in_attesa
```

### Step 3 — Clienti più urgenti da ricontattare
Per le principali zone, recupera i clienti più in ritardo:
```bash
{baseDir}/../espocrm/scripts/espocrm.sh zone
```
Poi per le zone con più urgenze, recupera i clienti:
```bash
{baseDir}/../espocrm/scripts/espocrm.sh clienti-zona "<zona_piu_urgente>"
```

### Step 4 — Componi il briefing

Formato del messaggio:
```
☀️ Buongiorno! Ecco il tuo briefing per oggi, [data in italiano]:

📋 TASK IN SCADENZA OGGI:
  • [Nome task] — [cliente collegato se presente]
  • [Nome task]
  (oppure: ✅ Nessuna task in scadenza oggi)

💰 ORDINI IN ATTESA:
  • Ordine da [email mittente] — [oggetto] — in attesa da [N] giorni
  (oppure: ✅ Nessun ordine in attesa)

📞 CLIENTI DA RICONTATTARE (top 5 più urgenti):
  1. [Nome] ([Zona]) — [N] giorni fa ⚠️
  2. [Nome] ([Zona]) — [N] giorni fa ⚠️
  3. [Nome] ([Zona]) — mai visitato 🆕

📍 SUGGERIMENTO VISITA:
  Se esci oggi, zona [X] ha [N] clienti da visitare.
  Scrivi "/giro [zona]" per il percorso ottimizzato.
```

## Workflow: "Riassumi la mia settimana"

1. Recupera Meeting (visite) degli ultimi 7 giorni
2. Recupera Call (chiamate) degli ultimi 7 giorni
3. Recupera Task completati degli ultimi 7 giorni
4. Recupera OrdineEmail creati negli ultimi 7 giorni

Formato:
```
📊 Riepilogo settimana [da] — [a]:
  📍 [N] visite effettuate
  📞 [N] chiamate registrate
  ✅ [N] task completati
  📧 [N] ordini processati
  
  Clienti visitati: [lista nomi]
  Zona più attiva: [zona]
```

## Regole

- Il briefing deve essere conciso ma completo
- Massimo 5 clienti nella sezione "da ricontattare"
- Ordina sempre per urgenza
- Se non ci sono dati (nessun task, nessun ordine), dillo esplicitamente con ✅
- Date in italiano (es. "venerdì 3 aprile 2026")
- Rispondi sempre in italiano
- Suggerisci sempre un'azione concreta ("Chiama Mario", "Vai nel Barese")
