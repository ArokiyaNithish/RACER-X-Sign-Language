/* ══════════════════════════════════════════════
   SignBridge Extension Popup — JS
   Handles Sign Up, Sign In, and Dashboard toggles:
   (Sign Language Detection, Voice TTS, and Meeting Report).
   ══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
    // Screens
    const scrSignUp = document.getElementById('screen-signup');
    const scrSignIn = document.getElementById('screen-signin');
    const scrDash = document.getElementById('screen-dashboard');

    // Input Fields
    const suName = document.getElementById('su-name');
    const suUid = document.getElementById('su-uid');
    const suPw = document.getElementById('su-pw');
    const suErr = document.getElementById('su-error');

    const siUid = document.getElementById('si-uid');
    const siPw = document.getElementById('si-pw');
    const siErr = document.getElementById('si-error');

    // Dashboard elements
    const avatarChar = document.getElementById('user-avatar');
    const dashName = document.getElementById('user-fullname');
    const dashLabel = document.getElementById('user-id-label');

    const togSign = document.getElementById('toggle-sign');
    const signText = document.getElementById('sign-status-text');
    const cardSign = document.getElementById('card-sign');

    const togVoice = document.getElementById('toggle-voice');
    const voiceText = document.getElementById('voice-status-text');
    const cardVoice = document.getElementById('card-voice');

    const togReport = document.getElementById('toggle-report');
    const reportText = document.getElementById('report-status-text');
    const cardReport = document.getElementById('card-report');
    const btnDown = document.getElementById('btn-download');

    const detBox = document.getElementById('detected-box');
    const detText = document.getElementById('detected-text');
    const detPhrase = document.getElementById('detected-phrase');

    // Dual Mode Elements
    const btnModeSign = document.getElementById('btn-mode-sign');
    const btnModeListen = document.getElementById('btn-mode-listen');
    const modeIndicator = document.getElementById('mode-active-indicator');
    const speechBox = document.getElementById('speech-box');
    const speechText = document.getElementById('speech-text');
    const avatarSignStatus = document.getElementById('avatar-sign-status');

    // ── 1. Initialization ──────────────────────────────────────────
    try {
        const data = await chrome.storage.local.get(['currentUser', 'prefs', 'sb_token', 'sb_mode']);
        if (data.currentUser && (data.currentUser.uid || data.currentUser.userId)) {
            showScreen(scrDash);
            populateDashboard(data.currentUser);
            initToggles(data.prefs || {});
            setPopupMode(data.sb_mode || 'sign', false);
        } else {
            showScreen(scrSignIn);
        }
    } catch (e) {
        showScreen(scrSignIn);
    }

    // ── 2. Navigation Handlers ─────────────────────────────────────
    document.getElementById('go-signin').addEventListener('click', (e) => {
        e.preventDefault();
        suErr.classList.add('hidden');
        showScreen(scrSignIn);
    });

    document.getElementById('go-signup').addEventListener('click', (e) => {
        e.preventDefault();
        siErr.classList.add('hidden');
        showScreen(scrSignUp);
    });

    document.getElementById('btn-signout').addEventListener('click', async () => {
        try {
            await chrome.storage.local.remove(['currentUser', 'sb_token', 'sb_user']);
            chrome.runtime.sendMessage({ type: "STOP_SIGN_DETECTION" });
            chrome.runtime.sendMessage({ type: "STOP_RECORDING" });
        } catch (e) { }

        siUid.value = ''; siPw.value = '';
        siErr.classList.add('hidden');
        showScreen(scrSignIn);
    });

    // ── 3. Sign Up Logic ───────────────────────────────────────────
    document.getElementById('btn-signup').addEventListener('click', async () => {
        const name = suName.value.trim();
        const uid = suUid.value.trim();
        const pw = suPw.value.trim();

        if (!name || !uid || !pw) {
            suErr.textContent = "All fields are required.";
            suErr.classList.remove('hidden');
            return;
        }

        if (pw.length < 4) {
            suErr.textContent = "Password must be at least 4 characters.";
            suErr.classList.remove('hidden');
            return;
        }

        suErr.classList.add('hidden');

        // Store user and token
        const token = `jwt_${Date.now()}`;
        const user = { name, uid, token };
        try {
            await chrome.storage.local.set({ 
                currentUser: user,
                sb_token: token,
                sb_user: { id: uid, name, email: uid }
            });
            chrome.runtime.sendMessage({ type: 'AUTH_UPDATE', token, user });
        } catch (e) { }

        showScreen(scrDash);
        populateDashboard(user);
        initToggles({});
    });

    // ── 4. Sign In Logic ───────────────────────────────────────────
    document.getElementById('btn-signin').addEventListener('click', async () => {
        const uid = siUid.value.trim();
        const pw = siPw.value.trim();

        if (!uid || !pw) {
            siErr.textContent = "Please enter User ID and Password.";
            siErr.classList.remove('hidden');
            return;
        }

        // Accepts user/user or any valid password >= 4 chars for demo convenience
        if (pw.length >= 4) {
            siErr.classList.add('hidden');
            const token = `jwt_${Date.now()}`;
            const user = { 
                name: uid === "user" ? "Alex (Signer)" : uid.split('@')[0], 
                uid: uid, 
                token: token 
            };

            try {
                await chrome.storage.local.set({ 
                    currentUser: user,
                    sb_token: token,
                    sb_user: { id: uid, name: user.name, email: uid }
                });
                chrome.runtime.sendMessage({ type: 'AUTH_UPDATE', token, user });
            } catch (e) { }

            showScreen(scrDash);
            populateDashboard(user);
            initToggles({});
        } else {
            siErr.textContent = "Password must be at least 4 characters.";
            siErr.classList.remove('hidden');
        }
    });

    // ── 5. Dashboard Logic ─────────────────────────────────────────
    function showScreen(screenEl) {
        scrSignUp.classList.remove('active');
        scrSignIn.classList.remove('active');
        scrDash.classList.remove('active');
        screenEl.classList.add('active');
    }

    function populateDashboard(user) {
        dashName.textContent = user.name || "User";
        dashLabel.textContent = `@${user.uid}`;
        avatarChar.textContent = (user.name || "U")[0].toUpperCase();
    }

    function initToggles(prefs) {
        const signEnabled = prefs.signEnabled ?? true;
        const voiceEnabled = prefs.voiceEnabled ?? true;
        const reportEnabled = prefs.recordingEnabled ?? false;

        togSign.checked = signEnabled;
        if (togVoice) togVoice.checked = voiceEnabled;
        togReport.checked = reportEnabled;

        updateSignUI(signEnabled);
        updateVoiceUI(voiceEnabled);
        updateReportUI(reportEnabled);

        detBox.style.opacity = signEnabled ? "1" : "0.4";
        if (!signEnabled) {
            detText.textContent = "—";
            detPhrase.textContent = "";
        }
    }

    // Toggle handlers
    togSign.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        updateSignUI(enabled);
        try {
            const data = await chrome.storage.local.get('prefs');
            const prefs = data.prefs || {};
            prefs.signEnabled = enabled;
            await chrome.storage.local.set({ prefs });

            chrome.runtime.sendMessage({ 
                type: enabled ? "START_SIGN_DETECTION" : "STOP_SIGN_DETECTION" 
            });
        } catch (err) { }
    });

    if (togVoice) {
        togVoice.addEventListener('change', async (e) => {
            const enabled = e.target.checked;
            updateVoiceUI(enabled);
            try {
                const data = await chrome.storage.local.get('prefs');
                const prefs = data.prefs || {};
                prefs.voiceEnabled = enabled;
                await chrome.storage.local.set({ prefs });

                chrome.runtime.sendMessage({ 
                    type: "SET_VOICE_TTS", 
                    enabled: enabled 
                });
            } catch (err) { }
        });
    }

    togReport.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        updateReportUI(enabled);
        try {
            const data = await chrome.storage.local.get('prefs');
            const prefs = data.prefs || {};
            prefs.recordingEnabled = enabled;
            await chrome.storage.local.set({ prefs });

            if (enabled) {
                chrome.runtime.sendMessage({ type: "START_RECORDING" });
                btnDown.classList.add('hidden');
            } else {
                chrome.runtime.sendMessage({ type: "STOP_RECORDING" });
                btnDown.classList.remove('hidden');
            }
        } catch (err) { }
    });

    function updateSignUI(enabled) {
        if (enabled) {
            cardSign.style.borderColor = "rgba(138, 180, 248, 0.4)";
            signText.textContent = "Active — translating camera gestures";
            signText.style.color = "#8ab4f8";
            detBox.style.opacity = "1";
        } else {
            cardSign.style.borderColor = "var(--border)";
            signText.textContent = "Off — click toggle to enable";
            signText.style.color = "var(--text-sub)";
            detBox.style.opacity = "0.4";
            detText.textContent = "—";
            detPhrase.textContent = "";
        }
    }

    function updateVoiceUI(enabled) {
        if (!cardVoice) return;
        if (enabled) {
            cardVoice.style.borderColor = "rgba(52, 168, 83, 0.4)";
            voiceText.textContent = "Active — speaking to opposite participants";
            voiceText.style.color = "#81c995";
        } else {
            cardVoice.style.borderColor = "var(--border)";
            voiceText.textContent = "Muted — visual captions only";
            voiceText.style.color = "var(--text-sub)";
        }
    }

    function updateReportUI(enabled) {
        if (enabled) {
            cardReport.style.borderColor = "rgba(197, 138, 249, 0.4)";
            reportText.textContent = "Recording transcript & minutes";
            reportText.style.color = "#c58af9";
        } else {
            cardReport.style.borderColor = "var(--border)";
            reportText.textContent = "Off — transcription idle";
            reportText.style.color = "var(--text-sub)";
        }
    }

    // ── Mode Switcher Logic (Sign vs Listen) ────────
    async function setPopupMode(mode, broadcast = true) {
        if (mode === 'sign') {
            btnModeSign?.classList.add('active-sign');
            btnModeListen?.classList.remove('active-listen');
            if (modeIndicator) {
                modeIndicator.textContent = "🤟 Sign Active";
                modeIndicator.style.color = "#00D4FF";
                modeIndicator.style.borderColor = "rgba(0, 212, 255, 0.4)";
                modeIndicator.style.background = "rgba(0, 212, 255, 0.15)";
            }
            detBox?.classList.remove('hidden');
            speechBox?.classList.add('hidden');
        } else {
            btnModeSign?.classList.remove('active-sign');
            btnModeListen?.classList.add('active-listen');
            if (modeIndicator) {
                modeIndicator.textContent = "👂 Listen Active";
                modeIndicator.style.color = "#c084fc";
                modeIndicator.style.borderColor = "rgba(168, 85, 247, 0.4)";
                modeIndicator.style.background = "rgba(168, 85, 247, 0.18)";
            }
            detBox?.classList.add('hidden');
            speechBox?.classList.remove('hidden');
        }

        if (broadcast) {
            try {
                await chrome.storage.local.set({ sb_mode: mode });
                chrome.runtime.sendMessage({ type: "SET_COMMUNICATION_MODE", mode });
                const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
                if (tabs && tabs[0]) {
                    chrome.tabs.sendMessage(tabs[0].id, { type: "SET_COMMUNICATION_MODE", mode }).catch(() => {});
                }
            } catch (err) {}
        }
    }

    btnModeSign?.addEventListener('click', () => setPopupMode('sign', true));
    btnModeListen?.addEventListener('click', () => setPopupMode('listen', true));

    // Listen for incoming detection & speech data
    try {
        chrome.runtime.onMessage.addListener((request) => {
            if (request.type === "SIGN_RECOGNITION") {
                detText.textContent = request.text || "—";
                if (speechText) {
                    speechText.textContent = `Opposite Signer: "${request.text}"`;
                    if (avatarSignStatus) avatarSignStatus.textContent = `🔊 Voice: "${request.text}"`;
                }
            }
            if (request.type === "PHRASE_READY") {
                detPhrase.textContent = request.text;
            }
            if (request.type === "SPEECH_HEARD") {
                if (speechText) speechText.textContent = `"${request.text}"`;
            }
        });
    } catch (e) { }

    // Download PDF
    btnDown.addEventListener('click', () => {
        try {
            chrome.runtime.sendMessage({ type: "DOWNLOAD_REPORT" });
        } catch (e) { }
        const orig = btnDown.textContent;
        btnDown.textContent = "Generating PDF...";
        setTimeout(() => { btnDown.textContent = orig; }, 2000);
    });
});
