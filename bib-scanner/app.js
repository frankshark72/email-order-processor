'use strict';

(function () {
  const STORAGE_KEY = 'bibScanner.v1.scans';
  const SCAN_COOLDOWN_MS = 2500;  // stesso QR ignorato finché resta inquadrato
  const SCAN_INTERVAL_MS = 150;   // throttle della decodifica
  const PROCESS_WIDTH = 640;      // i frame vengono ridotti a questa larghezza

  // ── DOM ───────────────────────────────────────────────
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const statusEl = document.getElementById('status');
  const counterEl = document.getElementById('counter');
  const listCountEl = document.getElementById('listCount');
  const bibListEl = document.getElementById('bibList');
  const emptyHint = document.getElementById('emptyHint');
  const toggleCameraBtn = document.getElementById('toggleCameraBtn');
  const flipBtn = document.getElementById('flipBtn');
  const torchBtn = document.getElementById('torchBtn');
  const cameraPlaceholder = document.getElementById('cameraPlaceholder');
  const manualInput = document.getElementById('manualInput');
  const manualAddBtn = document.getElementById('manualAddBtn');
  const exportBtn = document.getElementById('exportBtn');
  const clearBtn = document.getElementById('clearBtn');

  // ── Stato ─────────────────────────────────────────────
  let scans = loadScans();
  let stream = null;
  let scanning = false;
  let rafId = null;
  let lastDecodeAt = 0;
  let flashTimer = null;
  let audioCtx = null;
  let facingMode = 'environment';
  let torchOn = false;
  const recentCodes = new Map();  // codice -> timestamp ultimo avvistamento

  // ── Persistenza ───────────────────────────────────────
  function loadScans() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.error('Lettura storage fallita', e);
      return [];
    }
  }

  function saveScans() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(scans));
    } catch (e) {
      console.error('Salvataggio storage fallito', e);
      setStatus('⚠ Impossibile salvare la lista', 'duplicate');
    }
  }

  // ── Rendering ─────────────────────────────────────────
  function render() {
    counterEl.textContent = String(scans.length);
    listCountEl.textContent = String(scans.length);
    emptyHint.hidden = scans.length > 0;

    const sorted = scans.slice().sort((a, b) => b.lastTime - a.lastTime);
    bibListEl.innerHTML = '';

    for (const s of sorted) {
      const li = document.createElement('li');
      li.className = 'bib-item';

      const info = document.createElement('div');
      info.className = 'bib-info';

      const code = document.createElement('span');
      code.className = 'bib-code';
      code.textContent = s.code;
      code.title = s.code;
      info.appendChild(code);

      const meta = document.createElement('span');
      meta.className = 'bib-meta';
      meta.textContent = formatTime(s.lastTime);
      info.appendChild(meta);

      li.appendChild(info);

      if (s.count > 1) {
        const badge = document.createElement('span');
        badge.className = 'bib-badge';
        badge.textContent = '×' + s.count;
        badge.title = 'Scansionato ' + s.count + ' volte';
        li.appendChild(badge);
      }

      const del = document.createElement('button');
      del.className = 'del-btn';
      del.type = 'button';
      del.textContent = '✕';
      del.setAttribute('aria-label', 'Rimuovi ' + s.code);
      del.addEventListener('click', () => removeScan(s.code));
      li.appendChild(del);

      bibListEl.appendChild(li);
    }
  }

  function formatTime(ts) {
    return new Date(ts).toLocaleTimeString('it-IT', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  }

  function setStatus(text, state) {
    statusEl.textContent = text;
    statusEl.dataset.state = state || 'idle';
  }

  function flashStatus() {
    clearTimeout(flashTimer);
    statusEl.classList.remove('flash');
    void statusEl.offsetWidth;  // forza il restart dell'animazione
    statusEl.classList.add('flash');
    flashTimer = setTimeout(() => statusEl.classList.remove('flash'), 600);
  }

  // ── Logica principale ─────────────────────────────────
  function handleCode(rawCode, fromCamera) {
    const code = (rawCode || '').trim();
    if (!code) return;

    const now = Date.now();

    if (fromCamera) {
      // Cooldown: finché lo stesso QR resta inquadrato il timestamp
      // viene rinfrescato e la scansione non si ripete.
      const last = recentCodes.get(code);
      recentCodes.set(code, now);
      if (last && now - last < SCAN_COOLDOWN_MS) return;
    }

    const existing = scans.find(s => s.code === code);

    if (existing) {
      existing.count += 1;
      existing.lastTime = now;
      saveScans();
      render();
      setStatus('⚠ GIÀ PRESENTE: ' + code + '  (×' + existing.count + ')', 'duplicate');
      flashStatus();
      beepDuplicate();
      vibrate([130, 70, 130, 70, 130]);
    } else {
      scans.push({ code: code, count: 1, firstTime: now, lastTime: now });
      saveScans();
      render();
      setStatus('✓ Aggiunto: ' + code, 'success');
      flashStatus();
      beepSuccess();
      vibrate(90);
    }
  }

  function removeScan(code) {
    scans = scans.filter(s => s.code !== code);
    recentCodes.delete(code);
    saveScans();
    render();
    setStatus('Rimosso: ' + code, 'idle');
  }

  // ── Feedback: suono + vibrazione ──────────────────────
  function ensureAudio() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) audioCtx = new AC();
    }
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }

  function tone(freq, startOffset, duration, type) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type || 'sine';
    osc.frequency.value = freq;
    const t0 = audioCtx.currentTime + startOffset;
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(0.35, t0 + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.03);
  }

  function beepSuccess() {
    if (!ensureAudio()) return;
    tone(880, 0, 0.12, 'sine');
    tone(1320, 0.1, 0.13, 'sine');
  }

  function beepDuplicate() {
    if (!ensureAudio()) return;
    tone(300, 0, 0.18, 'square');
    tone(300, 0.24, 0.18, 'square');
    tone(300, 0.48, 0.28, 'square');
  }

  function vibrate(pattern) {
    if (navigator.vibrate) {
      try { navigator.vibrate(pattern); } catch (e) { /* ignora */ }
    }
  }

  // ── Fotocamera ────────────────────────────────────────
  async function startCamera() {
    ensureAudio();  // sblocca l'audio sul gesto utente

    if (typeof jsQR !== 'function') {
      setStatus('❌ Libreria QR non caricata', 'duplicate');
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus('❌ Fotocamera non supportata dal browser', 'duplicate');
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode } },
        audio: false
      });
    } catch (e) {
      console.error(e);
      const msg = e && e.name === 'NotAllowedError'
        ? 'Permesso fotocamera negato'
        : (e && e.message) || 'Fotocamera non disponibile';
      setStatus('❌ ' + msg, 'duplicate');
      return;
    }

    video.srcObject = stream;
    try {
      await video.play();
    } catch (e) {
      console.error('video.play()', e);
    }

    scanning = true;
    cameraPlaceholder.hidden = true;
    toggleCameraBtn.textContent = '⏸ Ferma scanner';
    toggleCameraBtn.classList.add('active');
    setStatus('Scanner attivo — inquadra un pettorale', 'idle');
    setupCameraControls();
    rafId = requestAnimationFrame(scanLoop);
  }

  function stopCamera() {
    scanning = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    video.srcObject = null;
    cameraPlaceholder.hidden = false;
    toggleCameraBtn.textContent = '▶ Avvia scanner';
    toggleCameraBtn.classList.remove('active');
    flipBtn.hidden = true;
    torchBtn.hidden = true;
    torchBtn.classList.remove('active');
    torchOn = false;
    setStatus('Scanner fermo', 'idle');
  }

  function setupCameraControls() {
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      navigator.mediaDevices.enumerateDevices()
        .then(devices => {
          const cams = devices.filter(d => d.kind === 'videoinput');
          flipBtn.hidden = cams.length < 2;
        })
        .catch(() => {});
    }
    const track = stream && stream.getVideoTracks()[0];
    const caps = track && track.getCapabilities ? track.getCapabilities() : {};
    torchBtn.hidden = !(caps && caps.torch);
  }

  async function flipCamera() {
    facingMode = facingMode === 'environment' ? 'user' : 'environment';
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    scanning = false;
    await startCamera();
  }

  async function toggleTorch() {
    const track = stream && stream.getVideoTracks()[0];
    if (!track) return;
    torchOn = !torchOn;
    try {
      await track.applyConstraints({ advanced: [{ torch: torchOn }] });
      torchBtn.classList.toggle('active', torchOn);
    } catch (e) {
      console.error('Torcia non disponibile', e);
      torchOn = false;
    }
  }

  // ── Ciclo di scansione ────────────────────────────────
  function scanLoop() {
    if (!scanning) return;
    rafId = requestAnimationFrame(scanLoop);

    const now = performance.now();
    if (now - lastDecodeAt < SCAN_INTERVAL_MS) return;
    lastDecodeAt = now;

    if (video.readyState !== video.HAVE_ENOUGH_DATA) return;
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return;

    const scale = Math.min(1, PROCESS_WIDTH / vw);
    const w = Math.round(vw * scale);
    const h = Math.round(vh * scale);
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;

    ctx.drawImage(video, 0, 0, w, h);

    let imageData;
    try {
      imageData = ctx.getImageData(0, 0, w, h);
    } catch (e) {
      return;
    }

    let result;
    try {
      result = jsQR(imageData.data, w, h, { inversionAttempts: 'dontInvert' });
    } catch (e) {
      return;
    }

    if (result && result.data) {
      handleCode(result.data, true);
    }
  }

  // ── Inserimento manuale ───────────────────────────────
  function manualAdd() {
    const value = manualInput.value;
    if (value && value.trim()) {
      ensureAudio();
      handleCode(value, false);
      manualInput.value = '';
    }
    manualInput.focus();
  }

  // ── Export CSV ────────────────────────────────────────
  function exportCSV() {
    if (scans.length === 0) {
      setStatus('Niente da esportare', 'idle');
      return;
    }
    const rows = [['Pettorale', 'Scansioni', 'Prima scansione', 'Ultima scansione']];
    const sorted = scans.slice().sort((a, b) => a.firstTime - b.firstTime);
    for (const s of sorted) {
      rows.push([
        s.code,
        String(s.count),
        new Date(s.firstTime).toLocaleString('it-IT'),
        new Date(s.lastTime).toLocaleString('it-IT')
      ]);
    }
    const csv = rows.map(r => r.map(csvCell).join(',')).join('\r\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    a.href = url;
    a.download = 'pettorali-' + stamp + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setStatus('CSV esportato (' + scans.length + ' pettorali)', 'success');
  }

  function csvCell(value) {
    const s = String(value);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  // ── Svuota lista ──────────────────────────────────────
  function clearAll() {
    if (scans.length === 0) return;
    if (!confirm('Eliminare tutti i ' + scans.length + ' pettorali scansionati?')) return;
    scans = [];
    recentCodes.clear();
    saveScans();
    render();
    setStatus('Lista svuotata', 'idle');
  }

  // ── Eventi ────────────────────────────────────────────
  toggleCameraBtn.addEventListener('click', () => {
    if (scanning) stopCamera();
    else startCamera();
  });
  flipBtn.addEventListener('click', flipCamera);
  torchBtn.addEventListener('click', toggleTorch);
  manualAddBtn.addEventListener('click', manualAdd);
  manualInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); manualAdd(); }
  });
  exportBtn.addEventListener('click', exportCSV);
  clearBtn.addEventListener('click', clearAll);

  // ── Service worker (uso offline) ──────────────────────
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(e => console.warn('SW', e));
    });
  }

  // ── Avvio ─────────────────────────────────────────────
  render();
  if (!window.isSecureContext) {
    setStatus('⚠ Serve HTTPS (o localhost) per la fotocamera', 'duplicate');
  } else {
    setStatus('Pronto — premi Avvia scanner', 'idle');
  }
})();
