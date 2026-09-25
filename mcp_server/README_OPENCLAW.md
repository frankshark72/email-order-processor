# MCP Server EspoCRM — Setup su VPS OpenClaw

## 1. Installa dipendenze

```bash
pip install mcp requests
# oppure con requirements.txt:
pip install -r mcp_server/requirements.txt
```

## 2. Testa il server manualmente

```bash
export ESPOCRM_URL=http://100.79.250.23:8080
export ESPOCRM_API_KEY=42f83e62ee977187aa76d2e701bb6fcc
python mcp_server/espocrm_mcp.py
# Deve stampare: "Running server 'espocrm' with transport 'stdio'"
# Premi Ctrl+C per uscire
```

## 3. Registra in OpenClaw

Edita `~/.openclaw/openclaw.json` e aggiungi la sezione `mcpServers`:

```json
{
  "mcpServers": {
    "espocrm": {
      "command": "python",
      "args": ["/root/email-order-processor/mcp_server/espocrm_mcp.py"],
      "env": {
        "ESPOCRM_URL": "http://100.79.250.23:8080",
        "ESPOCRM_API_KEY": "42f83e62ee977187aa76d2e701bb6fcc"
      }
    }
  }
}
```

> Adatta il path `/root/email-order-processor/mcp_server/espocrm_mcp.py`
> a dove hai clonato il repo sulla VPS.

## 4. Riavvia OpenClaw

```bash
openclaw daemon restart
```

## 5. Verifica da Telegram

Scrivi al bot:
- `briefing` → deve rispondere con task + ordini + clienti urgenti
- `clienti zona Barese` → lista clienti zona Barese
- `zone` → tutte le zone con conteggio clienti
- `registra visita Mario Rossi note: discusso nuovo catalogo`

## Tool disponibili

| Tool | Descrizione |
|---|---|
| `cerca_cliente` | Cerca cliente per nome (ricerca parziale) |
| `lista_clienti` | Elenca clienti, filtrabili per zona/tipo |
| `lista_zone` | Tutte le zone con numero clienti |
| `clienti_zona` | Clienti di una zona + link Google Maps |
| `ultima_visita` | Data e note dell'ultima visita |
| `registra_visita` | Crea Meeting in EspoCRM |
| `registra_chiamata` | Crea Call in EspoCRM |
| `aggiungi_nota` | Aggiunge Note a un account |
| `crea_task` | Crea Task/reminder |
| `task_oggi` | Task in scadenza oggi |
| `ordini_in_attesa` | Ordini email non ancora confermati |
| `briefing` | Briefing mattutino completo |
