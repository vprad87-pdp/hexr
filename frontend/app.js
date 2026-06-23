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
const encDownload = document.getElementById('enc-download');
const encError    = document.getElementById('enc-error');
const encSpinner  = document.getElementById('enc-spinner');

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
    const url  = URL.createObjectURL(blob);
    encImg.src = url;
    encDownload.href = url;
    show(encResult);
  } catch (err) {
    showError(encError, err.message);
  } finally {
    hide(encSpinner); encBtn.disabled = false;
  }
});

// ── Scanner ───────────────────────────────────────────────────────────────────
const scanCamera      = document.getElementById('scan-camera');
const scanGallery     = document.getElementById('scan-gallery');
const scanPreviewWrap = document.getElementById('scan-preview-wrap');
const scanPreview     = document.getElementById('scan-preview');
const scanBtn         = document.getElementById('scan-btn');
const scanResult      = document.getElementById('scan-result');
const scanText        = document.getElementById('scan-text');
const scanCopy        = document.getElementById('scan-copy');
const scanError       = document.getElementById('scan-error');
const scanSpinner     = document.getElementById('scan-spinner');

let selectedFile = null;

function onFileSelected(file) {
  if (!file) return;
  selectedFile = file;
  hide(scanResult); hide(scanError);
  scanPreview.src = URL.createObjectURL(file);
  show(scanPreviewWrap);
}

scanCamera.addEventListener('change',  () => onFileSelected(scanCamera.files[0]));
scanGallery.addEventListener('change', () => onFileSelected(scanGallery.files[0]));

scanBtn.addEventListener('click', async () => {
  const file = selectedFile;
  if (!file) return;

  hide(scanResult); hide(scanError);
  show(scanSpinner); scanBtn.disabled = true;

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
    hide(scanSpinner); scanBtn.disabled = false;
  }
});

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
