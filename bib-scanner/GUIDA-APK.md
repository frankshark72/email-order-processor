# 📱 Come trasformare l'app in un APK Android

L'app è una **PWA**: il modo più semplice e affidabile per ottenere un APK è
**PWABuilder**, il servizio gratuito di Microsoft. Non serve installare niente
sul computer.

> Perché non un APK già pronto qui? Compilare un APK richiede l'Android SDK e i
> server di build di Google, che l'ambiente di sviluppo usato per creare l'app
> ha bloccato. PWABuilder fa quel lavoro online al posto tuo.

## Cosa ti serve
- L'app pubblicata online con indirizzo `https://`
- Un browser sul computer
- ~10 minuti

---

## Passo 1 — Pubblica l'app online (GitHub Pages)

PWABuilder ha bisogno di un URL pubblico `https://`. Soluzione gratuita: GitHub Pages.

GitHub Pages può pubblicare solo la **radice** del repository, quindi i file
dell'app (`index.html`, `app.js`, ecc.) devono stare alla radice — non in una
sottocartella. Crea un repository nuovo con il contenuto di `bib-scanner/` alla
radice (vedi la sezione *"Spostare in un repository nuovo"* del `README.md`).

Poi:
1. Apri il repository su GitHub → **Settings → Pages**.
2. **Source**: *Deploy from a branch* → branch `main` → cartella **`/ (root)`** → **Save**.
3. Dopo 1-2 minuti l'app sarà online su
   `https://<tuo-utente>.github.io/<nome-repo>/`.
4. Apri quell'URL e verifica che l'app si carichi correttamente.

---

## Passo 2 — Genera l'APK con PWABuilder

1. Vai su **https://www.pwabuilder.com**
2. Incolla l'URL della tua app e premi **Start**.
3. PWABuilder analizza la PWA e mostra un punteggio: l'app è già conforme
   (manifest, service worker e icone sono inclusi).
4. Premi **Package For Stores** → riquadro **Android** → **Generate Package**.

---

## Passo 3 — Opzioni del pacchetto Android

Nella finestra Android:

- **Package ID**: identificativo univoco, es. `com.tuonome.scannerpettorali`
  (minuscolo, senza spazi). Una volta scelto **non cambiarlo più**.
- **App name**: `Scanner Pettorali`
- **Signing key**: la prima volta scegli **"Create new"**.

> ⚠️ **IMPORTANTE — chiave di firma.** PWABuilder ti darà un file `.keystore`
> con una password. **Conserva entrambi** in un posto sicuro: servono per ogni
> aggiornamento futuro dell'app. Se li perdi, non potrai più aggiornare l'APK
> già installato.

Premi **Generate** / **Download**.

---

## Passo 4 — Cosa scarichi

Ottieni uno ZIP che contiene:

| File | A cosa serve |
|------|--------------|
| `.apk` | Installazione diretta sul telefono (sideload) |
| `.aab` | Solo se vuoi pubblicare sul Google Play Store |
| chiave di firma + `assetlinks.json` | Firma e verifica del dominio |

---

## Passo 5 — Installare l'APK sul telefono

1. Trasferisci il file `.apk` sul telefono (cavo USB, email, Google Drive…).
2. Aprilo dal telefono.
3. Android chiederà di abilitare **"Installa app sconosciute"** per il browser o
   l'app file manager che stai usando: confermalo.
4. Installa, apri l'app e al primo avvio concedi il permesso **fotocamera**.

---

## Nota — togliere la barra del browser (opzionale)

L'APK generato è una *Trusted Web Activity*: di default può mostrare una piccola
barra in alto. Per eliminarla, prendi il file **`assetlinks.json`** fornito da
PWABuilder e pubblicalo nel repository in:

```
.well-known/assetlinks.json
```

così da renderlo raggiungibile a
`https://<tuo-utente>.github.io/<nome-repo>/.well-known/assetlinks.json`.
Senza questo passaggio l'app funziona comunque, mostra solo la barra.

---

## Alternativa — app nativa con Capacitor

Se preferisci un **progetto Android nativo** da compilare con **Android Studio**
(più controllo sul codice nativo, ma richiede l'installazione di Android Studio
sul tuo PC), posso configurarlo nel repository. Chiedimelo e lo preparo.
