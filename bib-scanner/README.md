# 🏃 Scanner Pettorali Gara

Web app per smartphone che scansiona i **QR code dei pettorali gara**, costruisce
la lista di quelli registrati e **avvisa subito se un pettorale è già presente**.

Funziona interamente nel browser: nessun account, nessun server, nessuna
connessione necessaria dopo il primo caricamento.

## Funzionalità

- 📷 **Scansione QR** con la fotocamera del telefono (in tempo reale)
- 📋 **Lista** dei pettorali registrati, salvata sul dispositivo
- ⚠️ **Avviso duplicati**: banner rosso + suono + vibrazione se un pettorale
  è già stato scansionato (con conteggio di quante volte)
- ✏️ **Inserimento manuale** per i pettorali con QR rovinato
- ⬇️ **Esporta CSV** (pettorale, n° scansioni, prima e ultima scansione)
- 🔦 Torcia e cambio fotocamera (dove supportati)
- 📴 **Funziona offline** e installabile come app (PWA "Aggiungi a Home")

## Come si usa

1. Apri l'app sul telefono e premi **▶ Avvia scanner**.
2. Concedi il permesso per la fotocamera.
3. Inquadra il QR code del pettorale:
   - ✅ verde + bip acuto → pettorale **aggiunto**
   - ⚠️ rosso + bip grave + vibrazione → pettorale **già presente**
4. La lista resta salvata anche chiudendo l'app. Usa **⬇ CSV** per esportarla.

> L'identificativo del pettorale è il **contenuto esatto del QR code** (un numero,
> un testo o un URL). Il rilevamento dei duplicati confronta questo valore: due
> QR identici = duplicato.

## Eseguire in locale (per sviluppo/test)

La fotocamera richiede un contesto sicuro: `https://` **oppure** `localhost`.
Aprire `index.html` con doppio clic (`file://`) **non** abilita la fotocamera.

```bash
cd bib-scanner
python3 -m http.server 8000
```

Poi apri `http://localhost:8000` nel browser del computer.

## Usarla sul telefono (pubblicazione su GitHub Pages)

Per usarla sul telefono serve un indirizzo `https://`. Il modo più semplice è
GitHub Pages:

1. Carica questa cartella in un repository GitHub.
2. Repository → **Settings → Pages**.
3. **Source**: branch `main`, cartella `/root` (o la cartella che contiene questi file).
4. Dopo qualche minuto l'app sarà online su
   `https://<tuo-utente>.github.io/<nome-repo>/`.
5. Aprila sul telefono e, dal menu del browser, scegli
   **"Aggiungi a schermata Home"** per installarla come app.

## Spostare in un repository nuovo

Questi file sono autonomi: per avere un repo dedicato basta copiare la cartella.

```bash
cp -r bib-scanner ~/scanner-pettorali
cd ~/scanner-pettorali
git init
git add .
git commit -m "Scanner pettorali gara"
# poi collega il repo creato su GitHub:
git remote add origin https://github.com/<tuo-utente>/<nome-repo>.git
git push -u origin main
```

## Note tecniche

- **Decodifica QR**: [jsQR](https://github.com/cozmo/jsQR) (incluso in `lib/`,
  nessuna dipendenza esterna a runtime).
- **Dati**: salvati in `localStorage` del browser. Sono legati a quel browser
  su quel dispositivo; svuotare i dati del sito o cambiare dispositivo li perde.
  Esporta il CSV per conservare i risultati.
- **Compatibilità**: Chrome/Safari/Firefox aggiornati su Android e iOS.
  Vibrazione e torcia non sono disponibili su tutti i dispositivi (iOS le ignora).

## Struttura

```
bib-scanner/
├── index.html      interfaccia
├── styles.css      stile (mobile-first)
├── app.js          logica: fotocamera, scansione, duplicati, salvataggio
├── manifest.json   metadati PWA
├── sw.js           service worker (uso offline)
├── lib/jsqr.js     libreria di decodifica QR
└── icons/          icone dell'app
```
