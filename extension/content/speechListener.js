// ════════════════════════════════════════════════════════════════
// SignBridge — speechListener.js
// Dual-Source Live Speech Listener (Listen Mode)
// 1. Google Meet Native Live Captions Observer (captures remote call audio)
// 2. Web Speech Recognition API (captures direct microphone voice)
// 3. Interactive Quick Test Trigger (for instant offline verification)
// ════════════════════════════════════════════════════════════════

(function () {
    'use strict';
    if (window.__sbSpeechListenerLoaded) return;
    window.__sbSpeechListenerLoaded = true;

    const PREFIX = '[SignBridge SpeechListener]';

    let recognition = null;
    let isListening = false;
    let shouldBeListening = false;
    let restartTimer = null;
    let captionObserver = null;
    let lastProcessedText = '';
    let speechBlocked = false;

    // Check SpeechRecognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    // ── 1. Speech Recognition (Web Speech API) ──────────────────
    function initRecognition() {
        if (!SpeechRecognition) {
            console.log(PREFIX, 'Web Speech API not available; relying on Meet caption observer and test chips.');
            return false;
        }

        try {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            recognition.maxAlternatives = 1;

            recognition.onstart = () => {
                isListening = true;
                speechBlocked = false;
                console.log(PREFIX, 'Speech listener active. Listening for voice in meeting...');
                if (window.__sbOverlay) {
                    window.__sbOverlay.updateDialogue('Listening to call participants...', false);
                }
            };

            recognition.onresult = (event) => {
                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    const res = event.results[i];
                    const text = res[0].transcript;
                    if (res.isFinal) {
                        final += text;
                    } else {
                        interim += text;
                    }
                }

                const fullText = (final || interim).trim();
                if (!fullText) return;

                if (window.__sbOverlay) {
                    window.__sbOverlay.updateDialogue(fullText, !!final);
                }

                if (final && final.trim() !== lastProcessedText) {
                    processSpeechText(final.trim());
                }
            };

            recognition.onerror = (event) => {
                if (event.error === 'no-speech' || event.error === 'aborted') {
                    return;
                }
                if (event.error === 'not-allowed' || event.error === 'audio-capture') {
                    speechBlocked = true;
                    console.log(PREFIX, 'Mic in use by Google Meet. Captions and quick test chips remain active.');
                    return;
                }
                console.log(PREFIX, 'Speech listener status:', event.error);
            };

            recognition.onend = () => {
                isListening = false;
                if (shouldBeListening && !speechBlocked) {
                    clearTimeout(restartTimer);
                    restartTimer = setTimeout(() => {
                        if (shouldBeListening && !isListening && !speechBlocked) {
                            try { recognition.start(); } catch (e) {}
                        }
                    }, 500);
                }
            };

            return true;
        } catch (err) {
            console.log(PREFIX, 'SpeechRecognition init failed:', err);
            return false;
        }
    }

    // ── 2. Google Meet Live Caption Observer ────────────────────
    // Google Meet renders live subtitles into specific DOM containers when enabled
    function startCaptionObserver() {
        if (captionObserver) return;

        const captionSelectors = [
            'div[jscontroller] .iTTPOb',
            'div[aria-live="polite"]',
            '.bh44bd',
            '.VbkSUe',
            '[data-sender-name]'
        ];

        captionObserver = new MutationObserver(() => {
            if (!shouldBeListening) return;

            for (const sel of captionSelectors) {
                const nodes = document.querySelectorAll(sel);
                if (nodes.length > 0) {
                    const latestNode = nodes[nodes.length - 1];
                    const text = latestNode.textContent?.trim();
                    if (text && text.length > 2 && text !== lastProcessedText) {
                        console.log(PREFIX, 'Captured Meet live caption:', text);
                        processSpeechText(text);
                        break;
                    }
                }
            }
        });

        try {
            captionObserver.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
            console.log(PREFIX, 'Google Meet caption observer active.');
        } catch (e) {}
    }

    function stopCaptionObserver() {
        if (captionObserver) {
            captionObserver.disconnect();
            captionObserver = null;
        }
    }

    // ── 3. Central Speech Processor ─────────────────────────────
    function processSpeechText(text) {
        if (!text) return;
        lastProcessedText = text;
        console.log(PREFIX, 'Processing speech text:', text);

        // Update Dialogue Box in overlay
        if (window.__sbOverlay) {
            window.__sbOverlay.updateDialogue(text, true);
        }

        // Trigger Sign Avatar
        if (window.__sbAvatar) {
            window.__sbAvatar.show();
            window.__sbAvatar.signText(text);
        }

        // Notify recording & popup
        document.dispatchEvent(new CustomEvent('sb:speechHeard', {
            detail: { text, timestamp: Date.now() }
        }));

        try {
            chrome.runtime.sendMessage({
                type: 'SPEECH_HEARD',
                text
            }).catch(() => {});
        } catch (e) {}
    }

    // ── 4. Public API ───────────────────────────────────────────
    function start() {
        shouldBeListening = true;
        speechBlocked = false;

        // 1. Start Meet caption observer
        startCaptionObserver();

        // 2. Start Web Speech recognition
        if (!recognition) {
            initRecognition();
        }

        if (recognition && !isListening) {
            try {
                recognition.start();
            } catch (err) {
                // If already active or mic locked
            }
        }

        if (window.__sbOverlay) {
            window.__sbOverlay.updateDialogue('Listening for voice from call...', false);
        }
        if (window.__sbAvatar) {
            window.__sbAvatar.show();
        }
    }

    function stop() {
        shouldBeListening = false;
        clearTimeout(restartTimer);
        stopCaptionObserver();

        if (recognition && isListening) {
            try { recognition.stop(); } catch (err) {}
        }
        isListening = false;
    }

    // ── Global Hook ─────────────────────────────────────────────
    window.__sbSpeechListener = {
        start,
        stop,
        isListening: () => isListening || shouldBeListening,
        triggerPhrase: (phrase) => {
            console.log(PREFIX, 'Manual test phrase triggered:', phrase);
            processSpeechText(phrase);
        }
    };

    console.log(PREFIX, 'Dual-Source speechListener.js loaded.');
})();
