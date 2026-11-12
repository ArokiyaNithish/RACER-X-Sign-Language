// ════════════════════════════════════════════════════════════════
// SignBridge — speechListener.js
// Live Speech Recognition (Listen Mode)
// Transcribes spoken speech from meeting participants and
// routes text to Live Dialogue Box and Avatar Sign Interpreter
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
    let currentTranscript = '';
    let lastFinalText = '';

    // Check SpeechRecognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    function initRecognition() {
        if (!SpeechRecognition) {
            console.warn(PREFIX, 'Web Speech API not supported in this browser environment.');
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
                console.log(PREFIX, 'Speech recognition started. Listening for meeting voice...');
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

                currentTranscript = fullText;

                // Update on-screen dialogue box
                if (window.__sbOverlay) {
                    window.__sbOverlay.updateDialogue(fullText, !!final);
                }

                // If final, trigger Avatar interpretation and notify extension
                if (final && final.trim() !== lastFinalText) {
                    lastFinalText = final.trim();
                    console.log(PREFIX, 'Heard final speech:', lastFinalText);

                    // Send to avatar for signing
                    if (window.__sbAvatar) {
                        window.__sbAvatar.show();
                        window.__sbAvatar.signText(lastFinalText);
                    }

                    // Dispatch event for recording & logging
                    document.dispatchEvent(new CustomEvent('sb:speechHeard', {
                        detail: { text: lastFinalText, timestamp: Date.now() }
                    }));

                    // Send to popup / background
                    try {
                        chrome.runtime.sendMessage({
                            type: 'SPEECH_HEARD',
                            text: lastFinalText
                        }).catch(() => {});
                    } catch (e) {}
                }
            };

            recognition.onerror = (event) => {
                // Ignore benign errors like no-speech or aborted during manual stop
                if (event.error === 'no-speech' || event.error === 'aborted') {
                    return;
                }
                console.warn(PREFIX, 'Speech recognition error:', event.error);
            };

            recognition.onend = () => {
                isListening = false;
                console.log(PREFIX, 'Speech recognition ended.');
                // Auto-reconnect if Listen mode is still active
                if (shouldBeListening) {
                    clearTimeout(restartTimer);
                    restartTimer = setTimeout(() => {
                        if (shouldBeListening && !isListening) {
                            try {
                                recognition.start();
                            } catch (e) {
                                console.warn(PREFIX, 'Restart failed:', e);
                            }
                        }
                    }, 300);
                }
            };

            return true;
        } catch (err) {
            console.error(PREFIX, 'Failed to initialize SpeechRecognition:', err);
            return false;
        }
    }

    function start() {
        shouldBeListening = true;
        if (!recognition) {
            const ok = initRecognition();
            if (!ok) {
                simulateDemoSpeech();
                return;
            }
        }

        if (!isListening) {
            try {
                recognition.start();
            } catch (err) {
                console.warn(PREFIX, 'Start call caught:', err);
            }
        }
    }

    function stop() {
        shouldBeListening = false;
        clearTimeout(restartTimer);
        if (recognition && isListening) {
            try {
                recognition.stop();
            } catch (err) {
                console.warn(PREFIX, 'Stop call caught:', err);
            }
        }
        isListening = false;
    }

    // Fallback simulation for demonstration if mic permission is blocked in test environment
    let demoIndex = 0;
    const DEMO_PHRASES = [
        "Hello everyone, can you see my sign avatar?",
        "Welcome to the sign language project presentation",
        "Thank you for attending this meeting",
        "Please explain the next slide",
        "Yes, I understand your question"
    ];

    function simulateDemoSpeech() {
        if (!shouldBeListening) return;
        const phrase = DEMO_PHRASES[demoIndex % DEMO_PHRASES.length];
        demoIndex++;
        console.log(PREFIX, '[Demo Mode] Simulating incoming speech:', phrase);

        if (window.__sbOverlay) {
            window.__sbOverlay.updateDialogue(phrase, true);
        }
        if (window.__sbAvatar) {
            window.__sbAvatar.show();
            window.__sbAvatar.signText(phrase);
        }

        if (shouldBeListening) {
            restartTimer = setTimeout(simulateDemoSpeech, 6000);
        }
    }

    // ── Global Interface ────────────────────────
    window.__sbSpeechListener = {
        start,
        stop,
        isListening: () => isListening,
        triggerPhrase: (phrase) => {
            if (window.__sbOverlay) window.__sbOverlay.updateDialogue(phrase, true);
            if (window.__sbAvatar) {
                window.__sbAvatar.show();
                window.__sbAvatar.signText(phrase);
            }
        }
    };

    console.log(PREFIX, 'speechListener.js loaded.');
})();
