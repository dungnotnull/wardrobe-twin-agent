/**
 * Background service worker for the Wardrobe Twin Agent extension.
 * Manages WebSocket connection to the local desktop app and handles
 * messages between content scripts and the popup.
 */

const WS_URL = 'ws://127.0.0.1:7331/ws';
let ws = null;
let reconnectTimer = null;

function connectWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('[WardrobeTwin] WebSocket connected');
      if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
      }
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      // Forward to popup if open
      chrome.runtime.sendMessage(msg).catch(() => {});
    };

    ws.onclose = () => {
      console.log('[WardrobeTwin] WebSocket disconnected');
      ws = null;
      // Reconnect after 5 seconds
      if (!reconnectTimer) {
        reconnectTimer = setInterval(connectWS, 5000);
      }
    };

    ws.onerror = (err) => {
      console.error('[WardrobeTwin] WebSocket error:', err);
      ws?.close();
    };
  } catch (e) {
    console.error('[WardrobeTwin] WS connect failed:', e);
  }
}

// Connect on startup
connectWS();

// Listen for messages from popup / content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'ping_backend') {
    // Check if WS is connected
    sendResponse({ connected: ws && ws.readyState === WebSocket.OPEN });
    return true;
  }

  if (msg.type === 'tryon_request' || msg.type === 'mix_match_request' || msg.type === 'size_chart_extract') {
    // Forward to backend via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      sendResponse({ sent: true });
    } else {
      sendResponse({ error: 'Backend not connected. Start the Wardrobe Twin app first.' });
    }
    return true;
  }

  if (msg.type === 'get_product_data') {
    // Ask content script for product data
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'extract_product' }, (response) => {
          sendResponse(response);
        });
      } else {
        sendResponse({ error: 'No active tab' });
      }
    });
    return true;  // async response
  }
});
