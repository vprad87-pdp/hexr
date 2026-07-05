// ── PWA: register service worker (enables Android "Add to Home Screen") ───────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// ── Tab switching ────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab, .panel').forEach(el => el.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// ── Helpers ──────────────────────────────────────────────────────────────────
function show(el)  { el.classList.remove('hidden'); }
function hide(el)  { el.classList.add('hidden'); }
function setText(el, msg) { el.textContent = msg; }

// ── Encoder ──────────────────────────────────────────────────────────────────
const encInput    = document.getElementById('enc-input');
const charCount   = document.getElementById('char-count');
const encBtn      = document.getElementById('enc-btn');
const encResult   = document.getElementById('enc-result');
const encImg      = document.getElementById('enc-img');
const encShare    = document.getElementById('enc-share');
const encCopy     = document.getElementById('enc-copy');
const encDownload = document.getElementById('enc-download');
const encError    = document.getElementById('enc-error');
const encSpinner  = document.getElementById('enc-spinner');

let encBlob = null;   // the current HexR PNG, kept for copy-to-clipboard

encInput.addEventListener('input', () => {
  charCount.textContent = encInput.value.length;
});

encBtn.addEventListener('click', async () => {
  const text = encInput.value.trim();
  if (!text) { showError(encError, 'Please enter some text.'); return; }

  hide(encResult); hide(encError);
  show(encSpinner); encBtn.disabled = true;

  try {
    const form = new FormData();
    form.append('text', text);
    const res = await fetch('/encode', { method: 'POST', body: form });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || 'Encoding failed');
    }
    const blob = await res.blob();
    encBlob = blob;
    const url  = URL.createObjectURL(blob);
    encImg.src = url;
    encDownload.href = url;
    encCopy.textContent = 'Copy image';
    // Show Share only if the browser can share the PNG file (mostly mobile).
    const shareFile = new File([blob], 'hexr.png', { type: 'image/png' });
    if (navigator.canShare && navigator.canShare({ files: [shareFile] })) {
      show(encShare);
    } else {
      hide(encShare);
    }
    show(encResult);
  } catch (err) {
    showError(encError, err.message);
  } finally {
    hide(encSpinner); encBtn.disabled = false;
  }
});

encShare.addEventListener('click', async () => {
  if (!encBlob) return;
  const file = new File([encBlob], 'hexr.png', { type: 'image/png' });
  try {
    await navigator.share({
      files: [file],
      title: 'HexR code',
      text: 'Here’s a HexR code — scan it at https://hexr.onrender.com',
    });
  } catch (err) {
    // Ignore the user cancelling the share sheet (AbortError).
    if (err && err.name !== 'AbortError') {
      showError(encError, 'Sharing failed — try Copy image or Download.');
    }
  }
});

encCopy.addEventListener('click', async () => {
  if (!encBlob) return;
  // Clipboard image support (ClipboardItem) is missing on some browsers,
  // notably Firefox — fall back to guiding the user to Download.
  if (!(navigator.clipboard && window.ClipboardItem)) {
    showError(encError, 'Copying images isn’t supported here — use Download PNG instead.');
    return;
  }
  try {
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': encBlob })]);
    const orig = encCopy.textContent;
    encCopy.textContent = 'Copied!';
    setTimeout(() => { encCopy.textContent = orig; }, 1500);
  } catch (err) {
    showError(encError, 'Copy failed — use Download PNG instead.');
  }
});

// ── Scanner ───────────────────────────────────────────────────────────────────
const scanCamera      = document.getElementById('scan-camera');
const scanGallery     = document.getElementById('scan-gallery');
const scanPreviewWrap = document.getElementById('scan-preview-wrap');
const scanPreview     = document.getElementById('scan-preview');
const scanResult      = document.getElementById('scan-result');
const scanText        = document.getElementById('scan-text');
const scanCopy        = document.getElementById('scan-copy');
const scanError       = document.getElementById('scan-error');
const scanSpinner     = document.getElementById('scan-spinner');

async function onFileSelected(file) {
  if (!file) return;
  hide(scanResult); hide(scanError);
  scanPreview.src = URL.createObjectURL(file);
  show(scanPreviewWrap);
  show(scanSpinner);

  try {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch('/decode', { method: 'POST', body: form });
    const j   = await res.json();
    if (!res.ok || j.error) throw new Error(j.error || 'Decoding failed');
    scanText.textContent = j.text;
    show(scanResult);
  } catch (err) {
    showError(scanError, err.message);
  } finally {
    hide(scanSpinner);
  }
}

scanCamera.addEventListener('change',  () => onFileSelected(scanCamera.files[0]));
scanGallery.addEventListener('change', () => onFileSelected(scanGallery.files[0]));

scanCopy.addEventListener('click', async () => {
  await navigator.clipboard.writeText(scanText.textContent).catch(() => {});
  const orig = scanCopy.textContent;
  scanCopy.textContent = 'Copied!';
  setTimeout(() => { scanCopy.textContent = orig; }, 1500);
});

function showError(el, msg) {
  setText(el, msg);
  show(el);
}
