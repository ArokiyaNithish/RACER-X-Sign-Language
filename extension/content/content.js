// ════════════════════════════════════════════
// SignBridge — content.js
// Main orchestrator for Google Meet integration
// Initializes all modules and manages state
// ════════════════════════════════════════════

(function () {
    'use strict';
    if (window.__sbContentLoaded) return;
    window.__sbContentLoaded = true;

    const PREFIX = '[SignBridge]';

    // ── Extension State ──────────────────────────
    const state = {
        inMeeting: false,
        signVoice: true,   // TTS enabled by default
        voiceSign: false,
        record: false,
        detecting: false,
        avatarOn: false,
        ttsOn: true,
        mode: 'sign',      // 'sign' or 'listen'
    };

    let meetingObserver = null;
    let transcriptBuffer = [];
    let phraseBuffer = [];
    let phraseTimer = null;
    const PHRASE_TIMEOUT = 1800;

    // ── Init ────────────────────────────────────
    async function init() {
        console.log(PREFIX, 'Content script initializing on', window.location.href);

        // Load auth & settings
        await loadSettings();

        // Create UI overlay
        if (window.__sbOverlay) window.__sbOverlay.create();
        if (window.__sbAvatar) window.__sbAvatar.create();

        // Detect meeting join/leave
        observeMeeting();

        // Override quick-toggle callbacks from uiOverlay
        window.__sbToggleDetect = () => toggleFeature('detect');
        window.__sbToggleAvatar = () => toggleFeature('avatar');
        window.__sbToggleRecord = () => toggleFeature('record');
        window.__sbToggleTTS = () => toggleFeature('tts');

        // Listen for sign detection events
        document.addEventListener('sb:signDetected', onSignDetected);

        // Listen for bidirectional mode changes (Sign vs Listen)
        document.addEventListener('sb:modeChanged', (e) => setCommunicationMode(e.detail?.mode));

        // Listen for toggle events from overlay buttons
        document.addEventListener('sb:toggle', (e) => toggleFeature(e.detail));

        // Listen for meeting ended
        document.addEventListener('sb:meetingEnded', () => {
            if (window.__sbAvatar) window.__sbAvatar.hide();
        });

        // Listen for messages from background/popup
        chrome.runtime.onMessage.addListener(handleMessage);

        console.log(PREFIX, 'Content script ready and integrated with sign language engine.');
    }

    // ── Load Settings ────────────────────────────
    async function loadSettings() {
        return new Promise(resolve => {
            chrome.storage.local.get(['sb_settings', 'sb_token', 'sb_user', 'prefs', 'sb_mode'], (data) => {
                const s = data.sb_settings || {};
                const p = data.prefs || {};
                state.signVoice = s.signVoice ?? p.voiceEnabled ?? true;
                state.voiceSign = s.voiceSign ?? false;
                state.record = s.record ?? p.recordingEnabled ?? false;
                state.mode = data.sb_mode || 'sign';
                applySettings();
                resolve();
            });
        });
    }

    function applySettings() {
        if (window.__sbSpeech) {
            window.__sbSpeech.setTTS(state.signVoice);
        }
    }

    // ── Meeting Detection ─────────────────────────
    function observeMeeting() {
        const target = document.body;
        meetingObserver = new MutationObserver(() => {
            checkMeetingStatus();
        });
        meetingObserver.observe(target, { childList: true, subtree: true });

        // Initial check
        checkMeetingStatus();
    }

    function checkMeetingStatus() {
        const inMeetingNow = !!(
            document.querySelector('[data-meeting-title]') ||
            document.querySelector('[data-call-ended]') ||
            document.querySelector('[data-self-name]') ||
            document.querySelector('.NzPR9b') ||
            document.querySelector('[jsname="EieBtf"]') ||
            document.querySelector('[aria-label*="Leave call"]') ||
            document.querySelector('video') ||
            document.querySelector('[aria-label*="You left"]')
        );

        const leaving = !!(
            document.querySelector('[data-call-ended="true"]') ||
            (document.title && document.title.toLowerCase().includes('left the call'))
        );

        if (inMeetingNow && !state.inMeeting) {
            onMeetingJoined();
        } else if (!inMeetingNow && state.inMeeting && leaving) {
            onMeetingLeft();
        }
    }

    function onMeetingJoined() {
        if (state.inMeeting) return;
        state.inMeeting = true;
        console.log(PREFIX, 'Google Meet call active!');

        if (window.__sbOverlay) window.__sbOverlay.show();

        // Check if sign detection is preferred on join
        chrome.storage.local.get(['prefs'], (data) => {
            if (data.prefs?.signEnabled && !state.detecting) {
                startDetection();
            }
        });

        chrome.runtime.sendMessage({ type: 'MEETING_STARTED' }).catch(() => {});
    }

    function onMeetingLeft() {
        if (!state.inMeeting) return;
        state.inMeeting = false;
        console.log(PREFIX, 'Meeting left.');

        stopDetection();
        disableAvatar();
        window.__sbRecorder?.stop();

        if (window.__sbOverlay) window.__sbOverlay.hide();
    }

    // ── Feature Toggles ───────────────────────────
    function toggleFeature(feature) {
        switch (feature) {
            case 'detect':
                state.detecting ? stopDetection() : startDetection();
                break;
            case 'avatar':
                state.avatarOn ? disableAvatar() : enableAvatar();
                break;
            case 'record':
                if (window.__sbRecorder) {
                    window.__sbRecorder.isRecording()
                        ? window.__sbRecorder.stop()
                        : window.__sbRecorder.start();
                }
                break;
            case 'tts':
                state.ttsOn = !state.ttsOn;
                state.signVoice = state.ttsOn;
                if (window.__sbSpeech) window.__sbSpeech.setTTS(state.ttsOn);
                updateOverlayButton('sb-toggle-tts', state.ttsOn, '🔊 Voice ON', '🔇 Voice OFF');
                break;
        }
    }

    function startDetection() {
        if (state.detecting) return;
        state.detecting = true;
        window.__sbSignDetector?.start();
        if (window.__sbOverlay) window.__sbOverlay.setStatus(true, '🟢 Sign Translation Active');
        updateOverlayButton('sb-toggle-detect', true, '🤟 Sign ON', '🤟 Sign OFF');
        console.log(PREFIX, 'Sign detection started.');
    }

    function stopDetection() {
        if (!state.detecting) return;
        state.detecting = false;
        window.__sbSignDetector?.stop();
        if (window.__sbOverlay) window.__sbOverlay.setStatus(false, '🔴 Sign Translation Off');
        updateOverlayButton('sb-toggle-detect', false, '🤟 Sign ON', '🤟 Sign OFF');
        console.log(PREFIX, 'Sign detection stopped.');
    }

    function enableAvatar() {
        if (state.avatarOn) return;
        state.avatarOn = true;
        window.__sbAvatar?.show();
        updateOverlayButton('sb-toggle-avatar', true, '👁️ Avatar ON', '👁️ Avatar OFF');
    }

    function disableAvatar() {
        if (!state.avatarOn) return;
        state.avatarOn = false;
        window.__sbAvatar?.hide();
        updateOverlayButton('sb-toggle-avatar', false, '👁️ Avatar ON', '👁️ Avatar OFF');
    }

    function updateOverlayButton(id, active, onLabel, offLabel) {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.innerHTML = `<span>${active ? '🤟' : '⚪'}</span> ${active ? onLabel : offLabel}`;
        btn.classList.toggle('active', active);
    }

    // ── Sign Event Handler ────────────────────────
    function onSignDetected(e) {
        const { text, confidence, rawSign } = e.detail;
        if (!text) return;

        console.log(PREFIX, `Sign: "${text}" (${((confidence || 0.9) * 100).toFixed(0)}%)`);

        // 1. Update UI overlay & Google Meet live caption banner
        if (window.__sbOverlay) {
            window.__sbOverlay.updateDetection(text, confidence);
            window.__sbOverlay.showSubtitle(text);
        }

        // 2. Accumulate and deliver spoken voice (TTS) + Meet Chat
        deliverPhrase(text);

        // 3. Record entry
        if (window.__sbRecorder?.isRecording()) {
            window.__sbRecorder.addEntry('sign_user', text);
        }
    }

    function deliverPhrase(phrase) {
        if (!phrase) return;
        console.log(PREFIX, 'Delivering speech & captions:', phrase);
        
        // Speak voice out loud so opposite call participant hears it
        if (state.signVoice && window.__sbSpeech) {
            window.__sbSpeech.handle(phrase);
        }
        
        document.dispatchEvent(new CustomEvent('sb:phraseReady', { detail: phrase }));
    }

    // ── Bidirectional Mode Handler (Sign vs Listen) ──
    function setCommunicationMode(mode) {
        if (!mode) return;
        state.mode = mode;
        console.log(PREFIX, 'Setting communication mode to:', mode);

        if (mode === 'sign') {
            // Sign Mode: deaf user signs -> camera detection on, TTS on, speech listener off
            window.__sbSpeechListener?.stop();
            startDetection();
            if (window.__sbOverlay) window.__sbOverlay.setMode('sign');
        } else if (mode === 'listen') {
            // Listen Mode: hearing participant speaks -> speech listener on, avatar on, camera idle
            stopDetection();
            enableAvatar();
            window.__sbSpeechListener?.start();
            if (window.__sbOverlay) window.__sbOverlay.setMode('listen');
        }

        // Save mode to chrome storage
        try {
            chrome.storage.local.set({ sb_mode: mode });
        } catch (e) {}
    }

    // ── Message Handler (from background / popup) ─
    function handleMessage(msg) {
        switch (msg.type) {
            case 'SET_COMMUNICATION_MODE':
            case 'SET_MODE':
                setCommunicationMode(msg.mode);
                break;

            case 'START_SIGN_DETECTION':
                startDetection();
                break;

            case 'STOP_SIGN_DETECTION':
                stopDetection();
                break;

            case 'SET_VOICE_TTS':
                state.signVoice = msg.enabled ?? true;
                state.ttsOn = msg.enabled ?? true;
                if (window.__sbSpeech) window.__sbSpeech.setTTS(state.signVoice);
                break;

            case 'SETTINGS_UPDATE':
                if (msg.settings) {
                    state.signVoice = msg.settings.signVoice ?? state.signVoice;
                    if (state.signVoice) startDetection();
                    else stopDetection();
                    applySettings();
                }
                break;

            case 'LOGOUT':
                stopDetection();
                disableAvatar();
                if (window.__sbOverlay) window.__sbOverlay.hide();
                break;

            case 'WS_STATUS':
                if (window.__sbOverlay && state.detecting) {
                    window.__sbOverlay.setStatus(true, msg.status === 'connected' ? '🟢 RACER-X AI Online' : '🟢 Sign Translation Active');
                }
                break;

            case 'LANDMARKS_DATA':
                if (window.__sbOverlay && window.__sbOverlay.updateLandmarks) {
                    window.__sbOverlay.updateLandmarks(msg);
                }
                break;

            case 'SIGN_RECOGNITION':
                if (window.__sbOverlay) {
                    window.__sbOverlay.updateDetection(msg.text, msg.confidence);
                    window.__sbOverlay.showSubtitle(msg.text);
                }
                deliverPhrase(msg.text);
                break;

            default:
                break;
        }
    }

    // ── Run Init ─────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
