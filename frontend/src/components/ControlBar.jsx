import { 
  Mic, 
  MicOff, 
  Video, 
  VideoOff, 
  PhoneOff, 
  Volume2, 
  VolumeX, 
  MessageSquare,
  Sparkles
} from 'lucide-react';

export default function ControlBar({
  micOn,
  cameraOn,
  signModeOn,
  ttsVoiceOn,
  onToggleMic,
  onToggleCamera,
  onToggleSignMode,
  onToggleTtsVoice,
  onLeave,
}) {
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
      <div className="glass-pill px-5 py-3 rounded-full flex items-center gap-3 border border-white/10 shadow-2xl backdrop-blur-xl">
        
        {/* Microphone Button */}
        <button
          onClick={onToggleMic}
          className={`w-11 h-11 flex items-center justify-center rounded-full transition-all duration-200 ${
            micOn 
              ? 'bg-gray-700/80 hover:bg-gray-600 text-white' 
              : 'bg-red-500/90 hover:bg-red-600 text-white shadow-lg shadow-red-500/25'
          }`}
          title={micOn ? "Mute Microphone" : "Unmute Microphone"}
        >
          {micOn ? <Mic size={19} /> : <MicOff size={19} />}
        </button>

        {/* Camera Button */}
        <button
          onClick={onToggleCamera}
          className={`w-11 h-11 flex items-center justify-center rounded-full transition-all duration-200 ${
            cameraOn 
              ? 'bg-gray-700/80 hover:bg-gray-600 text-white' 
              : 'bg-red-500/90 hover:bg-red-600 text-white shadow-lg shadow-red-500/25'
          }`}
          title={cameraOn ? "Turn Off Camera" : "Turn On Camera"}
        >
          {cameraOn ? <Video size={19} /> : <VideoOff size={19} />}
        </button>

        <div className="h-6 w-px bg-white/15 mx-1"></div>

        {/* Dedicated Sign Language Translation Toggle Button */}
        <button
          onClick={onToggleSignMode}
          className={`h-11 px-4 flex items-center gap-2 rounded-full font-medium text-xs transition-all duration-200 ${
            signModeOn
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/30 ring-2 ring-blue-400/50 animate-pulse-slow'
              : 'bg-gray-800/80 hover:bg-gray-700/90 text-gray-300 hover:text-white border border-white/10'
          }`}
          title="Toggle Real-Time Sign Language Translation"
        >
          <span className="text-base">🤟</span>
          <span className="hidden sm:inline font-semibold">
            {signModeOn ? 'Sign Translation: ON' : 'Sign Translation: OFF'}
          </span>
          {signModeOn && (
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          )}
        </button>

        {/* Spoken Voice (TTS) Toggle Button */}
        <button
          onClick={onToggleTtsVoice}
          className={`w-11 h-11 flex items-center justify-center rounded-full transition-all duration-200 ${
            ttsVoiceOn
              ? 'bg-emerald-600/90 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
              : 'bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white border border-white/10'
          }`}
          title={ttsVoiceOn ? "Opposite Person Voice Output (TTS): Enabled" : "Voice Output: Muted"}
        >
          {ttsVoiceOn ? <Volume2 size={19} /> : <VolumeX size={19} />}
        </button>

        <div className="h-6 w-px bg-white/15 mx-1"></div>

        {/* Leave Meeting Button (Google Meet style) */}
        <button
          onClick={onLeave}
          className="h-11 px-5 flex items-center justify-center rounded-full bg-red-600 hover:bg-red-700 text-white font-medium text-xs transition-all duration-200 shadow-lg shadow-red-600/30 gap-1.5"
          title="Leave Call"
        >
          <PhoneOff size={18} />
          <span className="hidden md:inline font-semibold">Leave</span>
        </button>

      </div>
    </div>
  );
}
