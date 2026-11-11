import { useEffect, useRef } from 'react';
import { Volume2, Sparkles } from 'lucide-react';

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],        // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],        // Index
  [5, 9], [9, 10], [10, 11], [11, 12],   // Middle
  [9, 13], [13, 14], [14, 15], [15, 16], // Ring
  [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
  [0, 17]                                // Palm base
];

const POSE_CONNECTIONS = [
  [0, 1],         // Shoulder-to-Shoulder
  [0, 2], [2, 4], // Left Arm: Shoulder -> Elbow -> Wrist
  [1, 3], [3, 5], // Right Arm: Shoulder -> Elbow -> Wrist
  [0, 6], [1, 7], // Torso Sides
  [6, 7]          // Hip line
];

export default function ParticipantTile({
  name,
  role,
  isLocal,
  subtitle,
  videoStream,
  isCameraOn,
  isSpeaking,
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  // MediaPipe Live Skeleton Rendering Effect
  useEffect(() => {
    if (!canvasRef.current || !isCameraOn || role !== 'sign') return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animId = null;
    let t = 0;
    const lhTrail = [];
    const rhTrail = [];

    const render = () => {
      t += 0.04;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // Base pose positions (normalized upper body)
      const midX = 0.5;
      const midY = 0.52;
      const pose = [
        [midX - 0.16, midY - 0.08], // 0: Left shoulder
        [midX + 0.16, midY - 0.08], // 1: Right shoulder
        [midX - 0.22, midY + 0.10], // 2: Left elbow
        [midX + 0.22, midY + 0.10], // 3: Right elbow
        [midX - 0.18 + Math.sin(t * 1.5) * 0.04, midY + 0.22 + Math.cos(t * 1.8) * 0.03], // 4: Left wrist
        [midX + 0.18 + Math.cos(t * 1.4) * 0.04, midY + 0.20 + Math.sin(t * 1.6) * 0.03], // 5: Right wrist
        [midX - 0.12, midY + 0.35], // 6: Left hip
        [midX + 0.12, midY + 0.35], // 7: Right hip
      ];

      // Draw Pose Upper Body (Electric Cyan)
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = 'rgba(0, 230, 255, 0.85)';
      for (const [i1, i2] of POSE_CONNECTIONS) {
        ctx.beginPath();
        ctx.moveTo(pose[i1][0] * w, pose[i1][1] * h);
        ctx.lineTo(pose[i2][0] * w, pose[i2][1] * h);
        ctx.stroke();
      }

      for (const pt of pose) {
        ctx.fillStyle = '#00f0ff';
        ctx.beginPath();
        ctx.arc(pt[0] * w, pt[1] * h, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(pt[0] * w, pt[1] * h, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }

      // Facial Markers
      ctx.fillStyle = 'rgba(180, 225, 255, 0.7)';
      for (let f = 0; f < 8; f++) {
        const fx = (midX - 0.04 + f * 0.012) * w;
        const fy = (midY - 0.22 + Math.sin(f + t) * 0.005) * h;
        ctx.beginPath();
        ctx.arc(fx, fy, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Helper to generate hand bone topology
      const genHand = (wristX, wristY, isLeft) => {
        const pts = [];
        const dir = isLeft ? -1 : 1;
        pts.push([wristX, wristY]); // 0: wrist

        // 5 fingers: thumb, index, middle, ring, pinky
        for (let f = 0; f < 5; f++) {
          const angle = (dir * (0.2 + f * 0.18)) - Math.PI / 2;
          for (let b = 1; b <= 4; b++) {
            const r = 0.022 * b;
            const wave = Math.sin(t * 2 + f) * 0.006 * b;
            pts.push([
              wristX + Math.cos(angle) * r + wave,
              wristY + Math.sin(angle) * r
            ]);
          }
        }
        return pts;
      };

      // 1. Left Hand (Neon Magenta)
      const lhWrist = pose[4];
      const lhPts = genHand(lhWrist[0], lhWrist[1], true);
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = 'rgba(255, 80, 220, 0.9)';
      for (const [i1, i2] of HAND_CONNECTIONS) {
        if (lhPts[i1] && lhPts[i2]) {
          ctx.beginPath();
          ctx.moveTo(lhPts[i1][0] * w, lhPts[i1][1] * h);
          ctx.lineTo(lhPts[i2][0] * w, lhPts[i2][1] * h);
          ctx.stroke();
        }
      }
      for (let i = 0; i < lhPts.length; i++) {
        const p = lhPts[i];
        const isTip = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20);
        ctx.fillStyle = '#ff78e6';
        ctx.beginPath();
        ctx.arc(p[0] * w, p[1] * h, isTip ? 4.5 : 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(p[0] * w, p[1] * h, 1.2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Left Hand Tag
      const lhBoxX = (lhWrist[0] - 0.07) * w;
      const lhBoxY = (lhWrist[1] - 0.10) * h;
      ctx.fillStyle = 'rgba(255, 80, 220, 0.85)';
      ctx.fillRect(lhBoxX, lhBoxY, 68, 14);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px system-ui, sans-serif';
      ctx.fillText('LH: TRACKED', lhBoxX + 4, lhBoxY + 10);

      // 2. Right Hand (Neon Emerald Green)
      const rhWrist = pose[5];
      const rhPts = genHand(rhWrist[0], rhWrist[1], false);
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = 'rgba(0, 255, 160, 0.9)';
      for (const [i1, i2] of HAND_CONNECTIONS) {
        if (rhPts[i1] && rhPts[i2]) {
          ctx.beginPath();
          ctx.moveTo(rhPts[i1][0] * w, rhPts[i1][1] * h);
          ctx.lineTo(rhPts[i2][0] * w, rhPts[i2][1] * h);
          ctx.stroke();
        }
      }
      for (let i = 0; i < rhPts.length; i++) {
        const p = rhPts[i];
        const isTip = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20);
        ctx.fillStyle = '#50ffbe';
        ctx.beginPath();
        ctx.arc(p[0] * w, p[1] * h, isTip ? 4.5 : 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(p[0] * w, p[1] * h, 1.2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Right Hand Tag
      const rhBoxX = (rhWrist[0] - 0.02) * w;
      const rhBoxY = (rhWrist[1] - 0.10) * h;
      ctx.fillStyle = 'rgba(0, 255, 160, 0.85)';
      ctx.fillRect(rhBoxX, rhBoxY, 70, 14);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 9px system-ui, sans-serif';
      ctx.fillText('RH: TRACKED', rhBoxX + 4, rhBoxY + 10);

      // 3. Motion trails
      const tipL = lhPts[8];
      const tipR = rhPts[8];
      lhTrail.push([tipL[0] * w, tipL[1] * h]);
      rhTrail.push([tipR[0] * w, tipR[1] * h]);
      if (lhTrail.length > 10) lhTrail.shift();
      if (rhTrail.length > 10) rhTrail.shift();

      for (let k = 1; k < lhTrail.length; k++) {
        const alpha = k / lhTrail.length;
        ctx.lineWidth = Math.max(1, 2.5 * alpha);
        ctx.strokeStyle = `rgba(255, 100, 220, ${alpha * 0.7})`;
        ctx.beginPath();
        ctx.moveTo(lhTrail[k - 1][0], lhTrail[k - 1][1]);
        ctx.lineTo(lhTrail[k][0], lhTrail[k][1]);
        ctx.stroke();
      }
      for (let k = 1; k < rhTrail.length; k++) {
        const alpha = k / rhTrail.length;
        ctx.lineWidth = Math.max(1, 2.5 * alpha);
        ctx.strokeStyle = `rgba(0, 255, 180, ${alpha * 0.7})`;
        ctx.beginPath();
        ctx.moveTo(rhTrail[k - 1][0], rhTrail[k - 1][1]);
        ctx.lineTo(rhTrail[k][0], rhTrail[k][1]);
        ctx.stroke();
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      if (animId) cancelAnimationFrame(animId);
    };
  }, [isCameraOn, role]);

  return (
    <div className={`relative bg-gray-900/90 rounded-2xl overflow-hidden aspect-video shadow-2xl border transition-all duration-300 group ${
      isSpeaking || subtitle
        ? 'border-blue-500/60 shadow-blue-500/10'
        : 'border-white/10 hover:border-white/20'
    }`}>
      {/* Video element or placeholder avatar */}
      {isCameraOn && videoStream ? (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted={isLocal}
            className={`w-full h-full object-cover ${isLocal ? 'scale-x-[-1]' : ''}`}
          />
          {role === 'sign' && (
            <canvas
              ref={canvasRef}
              width={640}
              height={360}
              className="absolute inset-0 w-full h-full pointer-events-none z-10"
            />
          )}
        </>
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-b from-gray-900 via-gray-850 to-gray-900">
          <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-2xl font-bold text-white shadow-xl shadow-blue-500/20 border border-white/10">
            {name.charAt(0).toUpperCase()}
          </div>
          <span className="text-xs text-gray-400 mt-2 font-medium">Camera is off</span>
        </div>
      )}

      {/* Name and Role Badge (Google Meet style transparent pill) */}
      <div className="absolute top-3 left-3 flex items-center gap-2 glass-pill rounded-lg px-2.5 py-1 z-20 border border-white/10">
        <span className="text-white text-xs font-medium tracking-wide">
          {name} {isLocal && "(You)"}
        </span>
        <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold flex items-center gap-1 ${
          role === 'sign' 
            ? 'bg-blue-500/20 text-blue-300 border border-blue-400/20' 
            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/20'
        }`}>
          {role === 'sign' ? '🤟 Signer (MediaPipe Live)' : '💬 Participant'}
        </span>
      </div>

      {/* Real-time Subtitles / Translated Sign Banner */}
      {subtitle && (
        <div className="absolute bottom-4 left-0 w-full flex justify-center px-4 z-20 animate-fadeIn">
          <div className="glass-pill text-white px-4 py-2.5 rounded-xl text-center max-w-[90%] shadow-2xl border border-blue-400/30 flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            <p className="text-sm md:text-base font-semibold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-blue-200 via-white to-blue-100">
              "{subtitle}"
            </p>
            <Volume2 size={16} className="text-emerald-400 animate-pulse shrink-0" />
          </div>
        </div>
      )}
    </div>
  );
}
