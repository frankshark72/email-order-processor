---
name: visite
description: Pianificazione visite clienti per zona in Puglia. Usa questa skill quando l'utente chiede di pianificare un giro visite, vuole sapere quali clienti visitare in una zona, chiede di ottimizzare un percorso, o dice "domani vado a..." o "/giro" o "pianifica la settimana".
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
    emoji: "📍"
---

# Visite — Pianificazione Giri Clienti in Puglia

Pianifica le visite ai clienti raggruppandoli per zona geografica,
con calcolo urgenze e link Google Maps per il percorso ottimizzato.

## Setup

Usa lo script EspoCRM: `{baseDir}/../espocrm/scripts/espocrm.sh`

## Zone

L'utente opera in Puglia. Le zone sono personalizzate e salvate nel campo `zona`
degli Account in EspoCRM. Esempi tipici: Barese, Salento, Dauno, Tarantino,
Brindisino, Valle d'Itria, BAT, Murgia.

## Workflow: /giro <zona>

Quando l'utente chiede di pianificare un giro in una zona:

### Step 1 — Recupera clienti della zona
```bash
{baseDir}/../espocrm/scripts/espocrm.sh clienti-zona "<zona>"
```

### Step 2 — Per ogni cliente, recupera ultima visita
```bash
{baseDir}/../espocrm/scripts/espocrm.sh ultima-visita "<account_id>"
```

### Step 3 — Calcola urgenza
Per ogni cliente calcola:
- `giorni_fa` = giorni dall'ultima visita (Meeting con status=Held)
- `frequenza` = campo `frequenzaVisitaGiorni` dell'Account (default 30)
- `in_ritardo` = `giorni_fa > frequenza` oppure mai visitato
- `priorita` = mai visitato > più giorni in ritardo > nei tempi

### Step 4 — Ordina per urgenza
1. Mai visitati (più urgenti)
2. Più giorni in ritardo rispetto alla frequenza
3. Nei tempi (meno urgenti)

### Step 5 — Genera link Google Maps
Costruisci l'URL con le tappe usando gli indirizzi dei clienti
(campi `billingAddressStreet`, `billingAddressCity`):

```
https://www.google.com/maps/dir/?api=1&origin=My+Location&destination=ULTIMO_INDIRIZZO&waypoints=INDIRIZZO1|INDIRIZZO2|INDIRIZZO3&travelmode=driving
```

URL-encode gli indirizzi. Massimo 10 tappe in Google Maps.
Aggiungi ", Puglia, Italia" a ogni indirizzo per precisione.

### Step 6 — Rispondi con formato
```
📍 Zona [NOME ZONA] — [N] clienti

1. **[Nome Azienda]** — [Città]
   🆕 Mai visitato / ⚠️ [N] giorni fa / ✅ [N] giorni fa
   
2. **[Nome Azienda]** — [Città]
   ⚠️ [N] giorni fa (obiettivo: ogni [freq]gg)

🗺 Apri percorso in Google Maps: [URL]
```

## Workflow: /zone

Lista tutte le zone con riepilogo urgenze:

```bash
{baseDir}/../espocrm/scripts/espocrm.sh zone
```

Rispondi con:
```
📊 Riepilogo zone:
  Barese: 12 clienti (3 ⚠️ da ricontattare)
  Salento: 8 clienti (1 ⚠️)
  Dauno: 5 clienti (5 ⚠️ tutti in ritardo!)
```

## Workflow: /settimana o "pianifica la settimana"

1. Recupera tutte le zone con clienti in ritardo
2. Ordina le zone per numero di clienti in ritardo (decrescente)
3. Assegna una zona per giorno lavorativo (lunedì-venerdì)
4. Per ogni giorno mostra i clienti da visitare nella zona assegnata

Formato:
```
📅 Piano visite settimana [data inizio] - [data fine]:

Lunedì    → Zona Dauno (5 clienti ⚠️)
Martedì   → Zona Barese (3 clienti ⚠️)
Mercoledì → Zona Salento (1 cliente ⚠️)
Giovedì   → libero
Venerdì   → Zona BAT (2 clienti ⚠️)
```

## Regole

- Gli indirizzi vanno sempre completati con "Puglia, Italia" nel link Maps
- Se un cliente non ha indirizzo, segnalalo ma non escluderlo dalla lista
- Suggerisci sempre il link Google Maps quando ci sono 2+ clienti
- Mostra le distanze approssimative solo se hai le coordinate (latitudine/longitudine)
- Rispondi sempre in italiano
- Se l'utente dice "domani vado a [zona]", trattalo come /giro <zona>
