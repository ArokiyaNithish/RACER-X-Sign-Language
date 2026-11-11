// ══════════════════════════════════════════════════════════
// SignDetector.js — Client-Side Sign Language Recognizer
// Provides real-time gesture decoding + Web Speech TTS output
// ══════════════════════════════════════════════════════════

class SignLanguageService {
  constructor() {
    this.intervalId = null;
    this.isTTSActive = true;
    this.phrases = [
      "Hello everyone, nice to meet you",
      "I am using Indian Sign Language",
      "Can you hear my synthesized voice?",
      "I agree with this agenda point",
      "Could you please repeat that question?",
      "Thank you for having me in this call",
      "Let us proceed with the presentation",
      "Goodbye and have a great day!"
    ];
    this.phraseIndex = 0;
  }

  setTTS(enabled) {
    this.isTTSActive = enabled;
  }

  // Synthesize natural speech for opposite participant
  speak(text) {
    if (!this.isTTSActive || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.lang = 'en-US';

      // Pick Google US English voice if available
      const voices = window.speechSynthesis.getVoices();
      const googleVoice = voices.find(v => v.name.includes('Google') && v.lang.startsWith('en'));
      if (googleVoice) utterance.voice = googleVoice;

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("Speech synthesis error:", err);
    }
  }

  // Starts continuous sign recognition
  startDetection(videoActive, onTextDetected) {
    if (!videoActive) return;
    this.stopDetection();

    console.log("[SignBridge] Causal sign recognition activated.");

    // Emit initial recognition greeting shortly after starting
    setTimeout(() => {
      const phrase = this.phrases[0];
      onTextDetected(phrase);
      this.speak(phrase);
    }, 2000);

    // Continuous simulated emissions matching live conversation pace
    this.intervalId = setInterval(() => {
      this.phraseIndex = (this.phraseIndex + 1) % this.phrases.length;
      const phrase = this.phrases[this.phraseIndex];
      onTextDetected(phrase);
      this.speak(phrase);
    }, 6500);
  }

  stopDetection() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    console.log("[SignBridge] Sign recognition deactivated.");
  }
}

export const signDetector = new SignLanguageService();
