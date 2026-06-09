/**
 * Popup script — runs when the user clicks the extension icon.
 * Shows product info, try-on button, and results.
 */

const WS_URL = 'ws://127.0.0.1:7331/ws';
let ws = null;
let currentProduct = null;
let pendingRequestId = null;

// ── WebSocket ──────────────────────────────────────────

function connectWS() {
  try {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => updateStatus(true);
    ws.onclose = () => { updateStatus(false); ws = null; };
    ws.onmessage = handleWSMessage;
    ws.onerror = () => { ws?.close(); };
  } catch (e) {
    updateStatus(false);
  }
}

connectWS();

// ── DOM refs ───────────────────────────────────────────

const statusEl = document.getElementById('status');
const noProductEl = document.getElementById('noProduct');
const productCardEl = document.getElementById('productCard');
const productImageEl = document.getElementById('productImage');
const productTitleEl = document.getElementById('productTitle');
const productBrandEl = document.getElementById('productBrand');
const productPriceEl = document.getElementById('productPrice');
const tryonBtnEl = document.getElementById('tryonBtn');
const mixMatchBtnEl = document.getElementById('mixMatchBtn');
const loadingEl = document.getElementById('loading');
const resultCardEl = document.getElementById('resultCard');
const resultImageEl = document.getElementById('resultImage');
const sizeRecEl = document.getElementById('sizeRecommendation');
const fitNotesEl = document.getElementById('fitNotes');
const mixMatchResultsEl = document.getElementById('mixMatchResults');
const mixMatchListEl = document.getElementById('mixMatchList');
const errorEl = document.getElementById('error');

// ── Status ─────────────────────────────────────────────

function updateStatus(connected) {
  statusEl.textContent = connected ? '● Connected' : '○ Disconnected';
  statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
  tryonBtnEl.disabled = !connected || !currentProduct;
  mixMatchBtnEl.disabled = !connected || !currentProduct;
}

// ── Product detection ───────────────────────────────────

async function detectProduct() {
  try {
    // Try via background script (content script extraction)
    const response = await chrome.runtime.sendMessage({ type: 'get_product_data' });
    if (response && response.detected) {
      currentProduct = response;
      showProduct(response);
    } else {
      showNoProduct();
    }
  } catch (e) {
    showNoProduct();
  }
}

function showProduct(product) {
  noProductEl.style.display = 'none';
  productCardEl.style.display = 'block';

  if (product.images && product.images.length > 0) {
    productImageEl.src = product.images[0];
    productImageEl.style.display = 'block';
  } else {
    productImageEl.style.display = 'none';
  }

  productTitleEl.textContent = product.title || 'Unknown Product';
  productBrandEl.textContent = product.brand || '';
  productPriceEl.textContent = product.price || '';

  updateStatus(ws && ws.readyState === WebSocket.OPEN);
}

function showNoProduct() {
  noProductEl.style.display = 'block';
  productCardEl.style.display = 'none';
  currentProduct = null;
}

detectProduct();

// ── Try-On ──────────────────────────────────────────────

tryonBtnEl.addEventListener('click', async () => {
  if (!currentProduct || !ws || ws.readyState !== WebSocket.OPEN) return;

  showLoading(true);
  hideResults();
  hideError();

  // Fetch product images as base64
  const imagesB64 = [];
  if (currentProduct.images && currentProduct.images.length > 0) {
    for (const url of currentProduct.images.slice(0, 3)) {
      try {
        const resp = await fetch(url);
        const blob = await resp.blob();
        const b64 = await blobToBase64(blob);
        imagesB64.push(b64);
      } catch (e) {
        console.warn('Failed to fetch image:', url, e);
      }
    }
  }

  const requestId = crypto.randomUUID();
  pendingRequestId = requestId;

  const msg = {
    type: 'tryon_request',
    request_id: requestId,
    payload: {
      product_url: currentProduct.url,
      product_images_b64: imagesB64,
      product_title: currentProduct.title,
      brand: currentProduct.brand,
      price: currentProduct.price,
      size_chart_html: currentProduct.size_chart_html,
      source_site: currentProduct.source_site,
    },
  };

  ws.send(JSON.stringify(msg));
});

// ── Mix-Match ──────────────────────────────────────────

mixMatchBtnEl.addEventListener('click', async () => {
  if (!currentProduct || !ws || ws.readyState !== WebSocket.OPEN) return;

  hideError();

  const imagesB64 = [];
  if (currentProduct.images && currentProduct.images.length > 0) {
    try {
      const resp = await fetch(currentProduct.images[0]);
      const blob = await resp.blob();
      const b64 = await blobToBase64(blob);
      imagesB64.push(b64);
    } catch (e) { /* ignore */ }
  }

  const requestId = crypto.randomUUID();
  const msg = {
    type: 'mix_match_request',
    request_id: requestId,
    payload: {
      garment_image_b64: imagesB64[0] || undefined,
      top_k: 5,
    },
  };

  ws.send(JSON.stringify(msg));
});

// ── WebSocket message handler ──────────────────────────

function handleWSMessage(event) {
  let msg;
  try {
    msg = JSON.parse(event.data);
  } catch (e) {
    return;
  }

  if (msg.type === 'tryon_result') {
    showLoading(false);
    const payload = msg.payload;

    if (payload.error) {
      showError(payload.error);
      return;
    }

    if (payload.tryon) {
      const tryon = payload.tryon;
      if (tryon.result_image_b64) {
        resultImageEl.src = 'data:image/png;base64,' + tryon.result_image_b64;
        resultCardEl.style.display = 'block';
      }
      if (tryon.size_recommendation) {
        sizeRecEl.textContent = 'Recommended Size: ' + tryon.size_recommendation;
      }
      if (tryon.fit_notes) {
        fitNotesEl.textContent = tryon.fit_notes;
      }
    }

    if (payload.size_match) {
      const sm = payload.size_match;
      sizeRecEl.textContent = 'Recommended Size: ' + sm.recommended_size + ' (' + Math.round(sm.confidence * 100) + '% confidence)';
      fitNotesEl.textContent = (sm.fit_notes || []).join(' | ');
      resultCardEl.style.display = 'block';
    }

    if (payload.mix_match) {
      showMixMatchResults(payload.mix_match);
    }
  }

  if (msg.type === 'mix_match_result') {
    showMixMatchResults(msg.payload);
  }

  if (msg.type === 'error') {
    showLoading(false);
    showError(msg.payload?.message || 'Unknown error');
  }
}

// ── UI helpers ─────────────────────────────────────────

function showLoading(show) {
  loadingEl.style.display = show ? 'block' : 'none';
  tryonBtnEl.disabled = show;
}

function hideResults() {
  resultCardEl.style.display = 'none';
  mixMatchResultsEl.style.display = 'none';
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.style.display = 'block';
}

function hideError() {
  errorEl.style.display = 'none';
}

function showMixMatchResults(data) {
  if (!data || !data.suggestions || data.suggestions.length === 0) {
    mixMatchResultsEl.style.display = 'none';
    return;
  }

  mixMatchListEl.innerHTML = '';
  data.suggestions.forEach((item) => {
    const div = document.createElement('div');
    div.className = 'mix-match-item';
    div.innerHTML = \
      <span>\</span>
      <span class="score">\%</span>
    \;
    mixMatchListEl.appendChild(div);
  });
  mixMatchResultsEl.style.display = 'block';
}

async function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const b64 = reader.result.split(',')[1];
      resolve(b64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
