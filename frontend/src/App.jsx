import { useState, useEffect, useRef } from 'react';
import ParticipantTile from './components/ParticipantTile';
import ControlBar from './components/ControlBar';
import TextInputBox from './components/TextInputBox';
import AuthModal from './components/AuthModal';
import { signDetector } from './utils/SignDetector';
import { LogOut, Users, Shield, Sparkles } from 'lucide-react';

const INITIAL_REMOTE_USERS = [
  { 
    id: 1, 
    name: "Dr. Santhi (Remote)", 
    role: "normal", 
    isLocal: false, 
    subtitle: "", 
    isCameraOn: true 
  },
  { 
    id: 2, 
    name: "Ishwarya (Signer)", 
    role: "sign", 
    isLocal: false, 
    subtitle: "", 
    isCameraOn: false 
  },
];

export default function App() {
  // Authentication State
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('sb_currentUser');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Meeting State
  const [role, setRole] = useState(null); // 'sign' or 'normal'
  const [localStream, setLocalStream] = useState(null);
  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(true);
  const [signModeOn, setSignModeOn] = useState(true);
  const [ttsVoiceOn, setTtsVoiceOn] = useState(true);

  // Subtitles & Participants
  const [localSubtitle, setLocalSubtitle] = useState("");
  const [remoteUsers, setRemoteUsers] = useState(INITIAL_REMOTE_USERS);

  const subtitleTimeoutRef = useRef(null);

  // Sync TTS engine with toggle
  useEffect(() => {
    signDetector.setTTS(ttsVoiceOn);
  }, [ttsVoiceOn]);

  // Camera Management
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
      setLocalStream(stream);
      setCameraOn(true);
    } catch (err) {
      console.warn("Camera access denied or unavailable:", err);
      setCameraOn(false);
    }
  };

  const stopCamera = () => {
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
      setCameraOn(false);
    }
  };

  const toggleCamera = async () => {
    if (cameraOn) {
      stopCamera();
    } else {
      await startCamera();
    }
  };

  const toggleMic = () => {
    setMicOn(!micOn);
  };

  const toggleSignMode = () => {
    setSignModeOn(prev => !prev);
  };

  const toggleTtsVoice = () => {
    setTtsVoiceOn(prev => !prev);
  };

  // Subtitle Auto-Clear Timer
  useEffect(() => {
    if (localSubtitle) {
      if (subtitleTimeoutRef.current) clearTimeout(subtitleTimeoutRef.current);
      subtitleTimeoutRef.current = setTimeout(() => {
        setLocalSubtitle("");
      }, 5000);
    }
    return () => clearTimeout(subtitleTimeoutRef.current);
  }, [localSubtitle]);

  // Hook up Sign Language Recognition Engine
  useEffect(() => {
    if (role && signModeOn && (cameraOn || role === 'sign')) {
      signDetector.startDetection(true, (translatedPhrase) => {
        setLocalSubtitle(translatedPhrase);
        
        // Also replicate on the opposite person's view so they see the live translation
        setRemoteUsers(prev => prev.map(u => ({
          ...u,
          subtitle: u.role === 'normal' ? translatedPhrase : u.subtitle
        })));
        
        // Clear remote subtitle after 5s
        setTimeout(() => {
          setRemoteUsers(prev => prev.map(u => ({ ...u, subtitle: "" })));
        }, 5000);
      });
    } else {
      signDetector.stopDetection();
    }

    return () => signDetector.stopDetection();
  }, [role, signModeOn, cameraOn]);

  // Join and Leave Meeting Handlers
  const joinMeeting = async (selectedRole) => {
    setRole(selectedRole);
    if (selectedRole === 'sign') {
      setSignModeOn(true);
    }
    await startCamera();
  };

  const leaveMeeting = () => {
    stopCamera();
    signDetector.stopDetection();
    setRole(null);
    setLocalSubtitle("");
  };

  const handleSignOut = () => {
    leaveMeeting();
    localStorage.removeItem('sb_currentUser');
    setCurrentUser(null);
  };

  // ── SCREEN 1: LOGIN / SIGN UP MODAL ─────────────────────────
  if (!currentUser) {
    return <AuthModal onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  // ── SCREEN 2: PRE-MEETING ROLE LOBBY ────────────────────────
  if (!role) {
    return (
      <div className="w-full min-h-screen flex flex-col items-center justify-center p-6 relative">
        {/* Glow orbs */}
        <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Top User Bar */}
        <div className="absolute top-6 right-6 flex items-center gap-3 glass-pill px-4 py-2 rounded-full border border-white/10 z-20">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-xs font-bold text-white">
            {currentUser.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-xs font-medium text-gray-200">{currentUser.name}</span>
          <button
            onClick={handleSignOut}
            className="text-gray-400 hover:text-red-400 transition-colors ml-2"
            title="Sign Out"
          >
            <LogOut size={14} />
          </button>
        </div>

        <div className="glass-panel w-full max-w-2xl rounded-3xl p-8 md:p-10 text-center shadow-2xl border border-white/10 z-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-xl shadow-blue-500/25 mb-4">
            <span className="text-3xl">🤟</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
            Ready to join the meeting?
          </h1>
          <p className="text-sm text-gray-400 max-w-md mx-auto mb-8">
            Choose your communication mode to activate real-time sign language or speech captioning.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
            {/* Sign Language User Card */}
            <button
              onClick={() => joinMeeting('sign')}
              className="p-6 rounded-2xl bg-white/5 hover:bg-white/10 border border-blue-500/30 hover:border-blue-400 transition-all duration-200 group text-left relative overflow-hidden shadow-lg"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-3xl group-hover:scale-110 transition-transform">🤟</span>
                <span className="text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-400/30 rounded-md px-2 py-0.5">
                  AI Translation
                </span>
              </div>
              <h3 className="text-base font-bold text-white group-hover:text-blue-300 transition-colors">
                Sign Language Signer
              </h3>
              <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
                Uses camera to translate continuous gestures into live captions and vocal speech for other participants.
              </p>
            </button>

            {/* Hearing / Normal Participant Card */}
            <button
              onClick={() => joinMeeting('normal')}
              className="p-6 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-emerald-400 transition-all duration-200 group text-left relative overflow-hidden shadow-lg"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-3xl group-hover:scale-110 transition-transform">💬</span>
                <span className="text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 rounded-md px-2 py-0.5">
                  Spoken / Captions
                </span>
              </div>
              <h3 className="text-base font-bold text-white group-hover:text-emerald-300 transition-colors">
                Hearing Participant
              </h3>
              <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
                Hear translated sign language spoken aloud and view live text subtitles generated by signers.
              </p>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── SCREEN 3: ACTIVE GOOGLE MEET ROOM ───────────────────────
  return (
    <div className="w-full min-h-screen flex flex-col pb-24 relative overflow-hidden">
      
      {/* Google Flow Glass Header */}
      <header className="h-16 px-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 glass-pill px-3.5 py-1.5 rounded-full border border-white/10">
            <span className="text-base">🤟</span>
            <span className="font-bold text-sm bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent">
              SignBridge Room
            </span>
          </div>
          <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${
            role === 'sign' 
              ? 'bg-blue-500/15 border-blue-400/30 text-blue-300' 
              : 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300'
          }`}>
            {role === 'sign' ? '🤟 Signer Active' : '💬 Participant Mode'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="glass-pill px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-1.5 text-xs text-gray-300">
            <Users size={13} className="text-blue-400" />
            <span>{remoteUsers.length + 1} online</span>
          </div>

          <div className="glass-pill px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-xs font-bold text-white">
              {currentUser.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-xs font-medium text-gray-200 hidden sm:inline">
              {currentUser.name}
            </span>
          </div>
        </div>
      </header>

      {/* Video Grid Layout */}
      <main className="flex-1 p-4 md:p-6 flex items-center justify-center w-full max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 w-full auto-rows-fr max-h-[calc(100vh-140px)]">
          {/* Local Participant Tile */}
          <ParticipantTile
            name={currentUser.name}
            role={role}
            isLocal={true}
            subtitle={localSubtitle}
            videoStream={localStream}
            isCameraOn={cameraOn}
          />

          {/* Remote Participant Tiles */}
          {remoteUsers.map(user => (
            <ParticipantTile
              key={user.id}
              name={user.name}
              role={user.role}
              isLocal={false}
              subtitle={user.subtitle}
              videoStream={null}
              isCameraOn={user.isCameraOn}
            />
          ))}
        </div>
      </main>

      {/* Normal Participant Text Input (for typing live broadcast captions) */}
      {role === 'normal' && (
        <TextInputBox onSend={(text) => {
          setLocalSubtitle(text);
          signDetector.speak(text);
        }} />
      )}

      {/* Floating Google Flow Control Bar */}
      <ControlBar
        micOn={micOn}
        cameraOn={cameraOn}
        signModeOn={signModeOn}
        ttsVoiceOn={ttsVoiceOn}
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onToggleSignMode={toggleSignMode}
        onToggleTtsVoice={toggleTtsVoice}
        onLeave={leaveMeeting}
      />

    </div>
  );
}
