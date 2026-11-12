// ════════════════════════════════════════════
// SignBridge — Background Service Worker
// Handles: WebSocket lifecycle, auth token mgmt,
//          tab tracking, and message relay.
// ════════════════════════════════════════════

const WS_URL = 'ws://localhost:8000/ws/sign-recognition';
const MAX_RETRIES = 5;

let ws = null;
let wsRetryCount = 0;
let wsRetryTimer = null;
let authToken = 'default_sign_token';
let activeTabId = null;

// ── Startup ──────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
    console.log('[SignBridge] Extension installed / updated.');
    chrome.storage.local.set({ 
        sb_settings: { signVoice: true, voiceSign: true, record: false },
        prefs: { signEnabled: true, voiceEnabled: true, recordingEnabled: false }
    });
});

chrome.runtime.onStartup.addListener(() => {
    console.log('[SignBridge] Browser started — service worker waking up.');
    loadTokenAndConnect();
});

// Load token on any wake-up
loadTokenAndConnect();

// ── Auth Token Load ───────────────────────────
function loadTokenAndConnect() {
    chrome.storage.local.get(['sb_token', 'currentUser'], (data) => {
        if (data.sb_token) {
            authToken = data.sb_token;
        } else if (data.currentUser && data.currentUser.token) {
            authToken = data.currentUser.token;
        }
        console.log('[SignBridge] Token loaded:', authToken, 'initiating WebSocket.');
        connectWebSocket();
    });
}

// ── WebSocket Manager ─────────────────────────
function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    const url = `${WS_URL}?token=${encodeURIComponent(authToken || 'guest_token')}`;
    console.log('[SignBridge] Connecting WebSocket to', url);

    try {
        ws = new WebSocket(url);
    } catch (err) {
        console.warn('[SignBridge] WebSocket construction failed:', err);
        scheduleReconnect();
        return;
    }

    ws.onopen = () => {
        console.log('[SignBridge] WebSocket connected to backend server.');
        wsRetryCount = 0;
        clearTimeout(wsRetryTimer);
        broadcastToContent({ type: 'WS_STATUS', status: 'connected' });
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        } catch (err) {
            console.error('[SignBridge] WS parse error:', err);
        }
    };

    ws.onerror = (err) => {
        console.warn('[SignBridge] WebSocket error (server might be offline, using client fallback):', err);
    };

    ws.onclose = (ev) => {
        console.log(`[SignBridge] WebSocket closed (code=${ev.code}).`);
        broadcastToContent({ type: 'WS_STATUS', status: 'disconnected' });
        ws = null;
        scheduleReconnect();
    };
}

function scheduleReconnect() {
    if (wsRetryCount >= MAX_RETRIES) {
        console.log('[SignBridge] Max WS retries reached. Backend offline — relying on on-device fallback.');
        broadcastToContent({ type: 'WS_STATUS', status: 'failed' });
        return;
    }
    const delay = Math.min(1000 * Math.pow(2, wsRetryCount), 15000);
    wsRetryCount++;
    wsRetryTimer = setTimeout(connectWebSocket, delay);
}

function disconnectWebSocket() {
    clearTimeout(wsRetryTimer);
    if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
    }
}

// ── Server Message Router ─────────────────────
function handleServerMessage(msg) {
    switch (msg.type) {
        case 'landmarks':
            broadcastToContent({ 
                type: 'LANDMARKS_DATA', 
                pose: msg.pose,
                left_hand: msg.left_hand,
                right_hand: msg.right_hand,
                face: msg.face,
                has_hands: msg.has_hands,
                has_left: msg.has_left,
                has_right: msg.has_right,
                timestamp: msg.timestamp
            });
            break;
        case 'recognition':
            broadcastToContent({ 
                type: 'SIGN_RECOGNITION', 
                text: msg.text,
                rawSign: msg.raw_sign,
                confidence: msg.confidence 
            });
            break;
        case 'avatar_sign':
            broadcastToContent({ type: 'AVATAR_SIGN', ...msg });
            break;
        case 'phrase_ready':
            broadcastToContent({ type: 'PHRASE_READY', text: msg.text });
            break;
        case 'error':
            console.error('[SignBridge] Server error:', msg.message);
            break;
        default:
            console.log('[SignBridge] Server msg:', msg);
    }
}

// ── Message Hub (from content / popup) ────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    switch (msg.type) {
        // ── Auth events ──
        case 'AUTH_UPDATE':
            authToken = msg.token || authToken;
            disconnectWebSocket();
            connectWebSocket();
            sendResponse({ ok: true });
            break;

        case 'LOGOUT':
            authToken = 'guest_token';
            disconnectWebSocket();
            sendResponse({ ok: true });
            break;

        // ── Detection Controls (from popup) ──
        case 'START_SIGN_DETECTION':
            console.log('[SignBridge BG] START_SIGN_DETECTION requested');
            connectWebSocket();
            broadcastToContent({ type: 'START_SIGN_DETECTION' });
            sendResponse({ ok: true });
            break;

        case 'STOP_SIGN_DETECTION':
            console.log('[SignBridge BG] STOP_SIGN_DETECTION requested');
            broadcastToContent({ type: 'STOP_SIGN_DETECTION' });
            sendResponse({ ok: true });
            break;

        case 'SET_VOICE_TTS':
            broadcastToContent({ type: 'SET_VOICE_TTS', enabled: msg.enabled });
            sendResponse({ ok: true });
            break;

        // ── Frame relay (content → backend via WS) ──
        case 'SEND_FRAME':
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'frame',
                    data: msg.data,
                    userId: msg.userId || 'signer',
                    timestamp: msg.timestamp || Date.now()
                }));
                sendResponse({ ok: true, forwarded: true });
            } else {
                sendResponse({ ok: false, reason: 'ws_not_connected' });
                connectWebSocket();
            }
            break;

        // ── Communication Mode Relay (Sign vs Listen) ──
        case 'SET_COMMUNICATION_MODE':
            broadcastToContent({ type: 'SET_COMMUNICATION_MODE', mode: msg.mode });
            sendResponse({ ok: true });
            break;

        case 'SPEECH_HEARD':
            broadcastToContent({ type: 'SPEECH_HEARD', text: msg.text });
            sendResponse({ ok: true });
            break;

        // ── Settings update ──
        case 'SETTINGS_UPDATE':
            broadcastToContent({ type: 'SETTINGS_UPDATE', settings: msg.settings });
            sendResponse({ ok: true });
            break;

        // ── WS status query ──
        case 'GET_WS_STATUS':
            sendResponse({
                status: ws
                    ? (ws.readyState === WebSocket.OPEN ? 'connected' : 'connecting')
                    : 'disconnected'
            });
            break;

        // ── Recording ──
        case 'START_RECORDING':
            broadcastToContent({ type: 'START_RECORDING' });
            sendResponse({ ok: true });
            break;

        case 'STOP_RECORDING':
            broadcastToContent({ type: 'STOP_RECORDING' });
            sendResponse({ ok: true });
            break;

        case 'DOWNLOAD_REPORT':
            broadcastToContent({ type: 'DOWNLOAD_REPORT' });
            sendResponse({ ok: true });
            break;

        default:
            sendResponse({ ok: true });
    }

    return true;
});

// ── Tab Tracking ──────────────────────────────
chrome.tabs.onActivated.addListener((info) => {
    chrome.tabs.get(info.tabId, (tab) => {
        if (tab && tab.url && tab.url.includes('meet.google.com')) {
            activeTabId = info.tabId;
        }
    });
});

chrome.tabs.onRemoved.addListener((tabId) => {
    if (tabId === activeTabId) activeTabId = null;
});

// ── Storage Change Listener ───────────────────
chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local') return;
    if (changes.sb_token) {
        const newToken = changes.sb_token.newValue;
        if (newToken && newToken !== authToken) {
            authToken = newToken;
            disconnectWebSocket();
            connectWebSocket();
        }
    }
});

// ── Utilities: Broadcast to Meet Tabs ─────────
function broadcastToContent(msg) {
    chrome.tabs.query({ url: 'https://meet.google.com/*' }, (tabs) => {
        tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, msg).catch(() => {});
        });
    });
}

// ── Alarms (keep service worker alive for WS) ─
chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'keepAlive') {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            connectWebSocket();
        }
    }
});
