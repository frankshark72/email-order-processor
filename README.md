# Email Order Processor 📦

Agente Python che monitora la tua casella email, estrae automaticamente gli ordini con Claude AI, verifica i prezzi e ti invia una notifica su Telegram per la conferma.

## Funzionamento

```
Email in arrivo
      │
      ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ IMAP Reader │───▶│  Claude AI        │───▶│  Price Checker  │
│             │    │  (Estrazione      │    │  (Verifica vs   │
│ Gmail/IMAP  │    │   ordine da       │    │   DB listini)   │
│ Outlook/... │    │   testo+PDF+xlsx) │    │                 │
└─────────────┘    └──────────────────┘    └────────┬────────┘
                                                    │
                                                    ▼
                                          ┌─────────────────┐
                                          │  Telegram Bot   │
                                          │                 │
                                          │ ✅ Conferma     │
                                          │ ✏️ Modifica     │
                                          │ ❌ Rifiuta      │
                                          └────────┬────────┘
                                                   │ conferma
                                                   ▼
                                          ┌─────────────────┐
                                          │  Email Sender   │
                                          │  (Inoltro       │
                                          │   all'azienda)  │
                                          └─────────────────┘
```

## Installazione

### 1. Requisiti

- Python 3.10+
- Account Claude AI (Anthropic): https://console.anthropic.com
- Bot Telegram (creato con @BotFather)

### 2. Installa le dipendenze

```bash
cd email-order-processor
pip install -r requirements.txt
```

### 3. Configurazione guidata

```bash
python main.py setup
```

Il wizard ti chiederà:
- Provider email (Gmail, Outlook, Aruba, ecc.)
- Token del bot Telegram
- Chiave API Anthropic

### 4. Gmail: App Password

Se usi Gmail devi usare una **App Password** (non la tua password normale):

1. Vai su https://myaccount.google.com/apppasswords
2. Crea una password per "Posta"
3. Abilita IMAP in Gmail: Impostazioni → Tutti gli indirizzi → Inoltro e POP/IMAP → Abilita IMAP

### 5. Crea il bot Telegram

1. Apri Telegram e cerca **@BotFather**
2. Invia `/newbot` e segui le istruzioni
3. Copia il **token** che ti viene dato
4. Invia un messaggio al tuo bot
5. Apri: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Trova il numero **`id`** dentro **`chat`** → è il tuo `chat_id`

## Utilizzo

### Avvia l'agente (modalità continua)

```bash
python main.py avvia
```

Il bot Telegram si avvia e controlla le email ogni 2 minuti.

### Elabora email una sola volta

```bash
python main.py processa
```

### Test connessioni

```bash
python main.py test-telegram   # test bot Telegram
python main.py test-email      # test connessione IMAP
```

### Gestione database

```bash
python main.py seed            # inserisce dati di esempio
python main.py lista-clienti   # mostra i clienti
python main.py lista-articoli  # mostra articoli e listini
python main.py lista-ordini    # mostra ordini ricevuti
```

## Struttura del database

Il database SQLite si trova in `data/orders.db`.

| Tabella | Contenuto |
|---------|-----------|
| `clienti` | Anagrafica clienti con email |
| `articoli` | Catalogo articoli con codice |
| `listini` | Prezzi personalizzati per cliente |
| `aziende` | Aziende a cui inviare gli ordini |
| `ordini` | Ordini estratti dalle email |
| `righe_ordine` | Righe di ogni ordine con verifica prezzi |

### Aggiungere un cliente manualmente

```python
from database.manager import upsert_cliente, upsert_listino, upsert_articolo

# Aggiungi cliente
cid = upsert_cliente(
    codice="CLI010",
    nome="Marco Bianchi",
    email="marco@negozio.it",
    azienda="Negozio Bianchi"
)

# Aggiungi articolo
aid = upsert_articolo("ART010", "Scarpe running taglia 43", "paia")

# Imposta prezzo per questo cliente
upsert_listino(cid, aid, prezzo=89.00, sconto_pct=5)
```

## Formato email supportato

L'agente capisce:

- **Email in testo libero**: "Vorrei ordinare 3 magliette taglia M a 15€..."
- **Email strutturate**: tabelle con codice, descrizione, quantità, prezzo
- **Allegati PDF**: ordini in formato PDF
- **Allegati Excel** (.xlsx/.xls): fogli ordine
- **Allegati CSV**: liste prodotti

## Notifica Telegram

Quando arriva un ordine ricevi un messaggio come questo:

```
⚠️ NUOVO ORDINE DA VERIFICARE

📧 Da: mario.rossi@email.it
📋 Oggetto: Ordine Aprile 2026
📅 Data ordine: 2026-04-01

👤 Cliente: Mario Rossi (Rossi Sport)

📦 RIGHE ORDINE:
✅ ART001 Maglietta tecnica running
    Qty: 10 pz | Prezzo: 16.20 €
❌ ART002 Pantaloncino ciclismo
    Qty: 5 pz | Prezzo: 30.00 € | Listino: 29.75 €

💰 Totale ricevuto: 312.00 €
💰 Totale listino: 310.75 €
⚡ Differenza: +1.25 €

━━━━━━━━━━━━━━━━━━━━━━
Vuoi inviare questo ordine all'azienda?

[✅ Conferma & Invia]  [✏️ Modifica prezzi]  [❌ Rifiuta]
```

## Configurazione avanzata

Vedi `config.yaml` per tutte le opzioni disponibili.

### Filtro mittenti

Per analizzare solo email da certi indirizzi:

```yaml
agent:
  filtro_mittenti:
    - cliente@azienda.it
    - "@altro-cliente.it"
```

### Intervallo di controllo

```yaml
agent:
  poll_interval_seconds: 60   # ogni minuto
```
