// ════════════════════════════════════════════════════════════════
// SignBridge — uiOverlay.js
// Google Flow Transparent Glassmorphism Overlay for Google Meet
// Includes Live MediaPipe Gesture Skeleton Overlay & HUD
// ════════════════════════════════════════════════════════════════

(function () {
  'use strict';
  if (window.__sbOverlayLoaded) return;
  window.__sbOverlayLoaded = true;

  const PREFIX = '[SignBridge Overlay]';
  let panel = null;
  let subtitleBanner = null;
  let mediapipeHud = null;
  let meetVideoCanvas = null;
  let meetVideoCtx = null;
  let isDragging = false;
  let isHudDragging = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;
  let hudOffsetX = 0;
  let hudOffsetY = 0;
  let isCollapsed = false;
  let subtitleTimer = null;
  let activeVideoEl = null;

  // MediaPipe Topology Connections (Matching RACER-X demo_video.py)
  const HAND_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 4],        // Thumb
    [0, 5], [5, 6], [6, 7], [7, 8],        // Index
    [5, 9], [9, 10], [10, 11], [11, 12],   // Middle
    [9, 13], [13, 14], [14, 15], [15, 16], // Ring
    [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
    [0, 17]                                // Palm base
  ];

  const POSE_CONNECTIONS = [
    [0, 1],         // Shoulder-to-Shoulder (11 -> 12)
    [0, 2], [2, 4], // Left Arm: Shoulder (11) -> Elbow (13) -> Wrist (15)
    [1, 3], [3, 5], // Right Arm: Shoulder (12) -> Elbow (14) -> Wrist (16)
    [0, 6], [1, 7], // Torso Sides: Shoulder -> Hip
    [6, 7]          // Hip line
  ];

  // Latest landmark data received from RACER-X inference backend
  let currentLandmarks = {
    pose: null,
    left_hand: null,
    right_hand: null,
    face: null,
    has_hands: false,
    has_left: false,
    has_right: false,
    reliability: 0.94,
    timestamp: Date.now()
  };

  // Motion trails for index fingertips
  const lhTrail = [];
  const rhTrail = [];
  const MAX_TRAIL = 12;

  let showSkeleton = true;
  let showHud = true;

  // ── Create Overlay, HUD & Canvas ───────────────────────────
  function createOverlayPanel() {
    if (document.getElementById('sb-overlay-panel')) return;

    // Inject Google Flow Transparent Styles
    const style = document.createElement('style');
    style.id = 'sb-overlay-styles';
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

      /* Floating Google Flow Glassmorphic Panel */
      #sb-overlay-panel {
        position: fixed;
        bottom: 84px;
        right: 24px;
        width: 310px;
        background: rgba(28, 30, 36, 0.88);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        z-index: 999999;
        font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
        user-select: none;
        transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
        overflow: hidden;
      }

      #sb-overlay-panel.collapsed {
        height: 52px !important;
      }

      #sb-overlay-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        cursor: move;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.03);
      }

      .sb-logo-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .sb-logo-icon {
        width: 26px;
        height: 26px;
        background: linear-gradient(135deg, #1a73e8, #7c3aed);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
      }

      .sb-title {
        font-size: 13.5px;
        font-weight: 700;
        color: #fff;
        letter-spacing: -0.2px;
      }

      .sb-header-actions {
        display: flex;
        gap: 6px;
        align-items: center;
      }

      #sb-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ea4335;
        transition: background 0.3s;
      }

      #sb-status-dot.active {
        background: #34a853;
        box-shadow: 0 0 8px #34a853;
      }

      .sb-header-btn {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #9aa0a6;
        border-radius: 50%;
        width: 22px;
        height: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        cursor: pointer;
        line-height: 1;
        transition: background 0.2s, color 0.2s;
      }

      .sb-header-btn:hover {
        background: rgba(255, 255, 255, 0.16);
        color: #fff;
      }

      #sb-overlay-body {
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .sb-status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #9aa0a6;
        font-size: 11px;
      }

      /* Detection Preview Box */
      .sb-detection-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 9px 12px;
      }

      .sb-det-label {
        font-size: 9.5px;
        color: #8ab4f8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 2px;
      }

      #sb-detected-sign {
        font-size: 16px;
        font-weight: 700;
        color: #fff;
        min-height: 22px;
      }

      #sb-confidence-bar-wrap {
        height: 3px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 2px;
        margin-top: 5px;
        overflow: hidden;
      }

      #sb-confidence-bar {
        height: 100%;
        background: linear-gradient(90deg, #1a73e8, #34a853);
        border-radius: 2px;
        width: 0%;
        transition: width 0.3s ease;
      }

      /* Quick Action Buttons */
      .sb-quick-btns {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 2px;
      }

      .sb-quick-btn {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e8eaed;
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 11.5px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
      }

      .sb-quick-btn:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(138, 180, 248, 0.4);
      }

      .sb-quick-btn.active {
        background: rgba(26, 115, 232, 0.25);
        border-color: #8ab4f8;
        color: #8ab4f8;
      }

      /* Live Subtitle Banner (Google Meet style) */
      #sb-live-subtitle-banner {
        position: fixed;
        bottom: 86px;
        left: 50%;
        transform: translateX(-50%);
        max-width: 82%;
        background: rgba(16, 18, 22, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 255, 170, 0.3);
        border-radius: 16px;
        padding: 11px 24px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.65), 0 0 20px rgba(0, 255, 170, 0.15);
        z-index: 999998;
        display: none;
        align-items: center;
        gap: 12px;
        font-family: 'Google Sans', 'Inter', sans-serif;
        animation: sb-banner-in 0.25s ease-out;
      }

      #sb-live-subtitle-banner.visible {
        display: flex;
      }

      @keyframes sb-banner-in {
        from { opacity: 0; transform: translate(-50%, 8px); }
        to { opacity: 1; transform: translate(-50%, 0); }
      }

      .sb-sub-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #00ffaa;
        box-shadow: 0 0 10px #00ffaa;
        flex-shrink: 0;
      }

      .sb-sub-text {
        font-size: 15.5px;
        font-weight: 600;
        color: #ffffff;
        letter-spacing: 0.2px;
      }

      /* ══════════════════════════════════════════════════════════
         MediaPipe Live HUD (Floating Camera & Skeleton Mirror)
         ══════════════════════════════════════════════════════════ */
      #sb-mediapipe-hud {
        position: fixed;
        top: 24px;
        left: 24px;
        width: 320px;
        background: rgba(15, 17, 23, 0.90);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 230, 255, 0.35);
        border-radius: 18px;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 230, 255, 0.12);
        z-index: 999997;
        font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
        user-select: none;
        overflow: hidden;
        transition: opacity 0.2s ease;
      }

      #sb-mediapipe-hud-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 9px 14px;
        cursor: move;
        background: rgba(0, 230, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      }

      .sb-hud-title-wrap {
        display: flex;
        align-items: center;
        gap: 7px;
      }

      .sb-hud-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #00ffa0;
        box-shadow: 0 0 8px #00ffa0;
      }

      .sb-hud-title {
        font-size: 12px;
        font-weight: 700;
        color: #fff;
        letter-spacing: -0.2px;
      }

      .sb-hud-badges {
        display: flex;
        gap: 6px;
        align-items: center;
      }

      .sb-hud-badge {
        font-size: 9.5px;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.1);
        padding: 2px 6px;
        border-radius: 6px;
        color: #8ab4f8;
      }

      #sb-hud-canvas-wrap {
        position: relative;
        width: 320px;
        height: 200px;
        background: #000;
        overflow: hidden;
      }

      #sb-hud-video {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        transform: scaleX(-1);
      }

      #sb-hud-canvas {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
      }

      #sb-hud-footer {
        padding: 8px 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 10.5px;
        background: rgba(255, 255, 255, 0.03);
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        color: #bdc1c6;
      }

      .sb-hud-status-chip {
        display: flex;
        align-items: center;
        gap: 5px;
      }

      /* ══════════════════════════════════════════════════════════
         Google Meet Participant Video Direct Overlay Canvas
         ══════════════════════════════════════════════════════════ */
      #sb-meet-video-skeleton-canvas {
        position: fixed;
        pointer-events: none;
        z-index: 999990;
        border-radius: 12px;
        transition: opacity 0.2s ease;
      }
    `;
    document.head.appendChild(style);

    // 1. Create Main Overlay Panel
    panel = document.createElement('div');
    panel.id = 'sb-overlay-panel';
    panel.innerHTML = `
      <div id="sb-overlay-header">
        <div class="sb-logo-row">
          <div class="sb-logo-icon">🤟</div>
          <span class="sb-title">SignBridge</span>
        </div>
        <div class="sb-header-actions">
          <div id="sb-status-dot"></div>
          <button class="sb-header-btn" id="sb-collapse-btn" title="Minimize">−</button>
          <button class="sb-header-btn" id="sb-close-btn" title="Close">×</button>
        </div>
      </div>
      <div id="sb-overlay-body">
        <div class="sb-status-row">
          <span id="sb-status-text">🔴 Sign Translation Off</span>
          <span id="sb-fps-badge" style="font-size:10px; color:#5f6368;">Ready</span>
        </div>
        <div class="sb-detection-box">
          <div class="sb-det-label">Recognized Sign Gesture</div>
          <div id="sb-detected-sign">—</div>
          <div id="sb-confidence-bar-wrap"><div id="sb-confidence-bar"></div></div>
        </div>
        <div class="sb-quick-btns">
          <button class="sb-quick-btn active" id="sb-toggle-detect" onclick="window.__sbToggleDetect()">
            <span>🤟</span> Sign Mode
          </button>
          <button class="sb-quick-btn active" id="sb-toggle-skeleton" onclick="window.__sbToggleSkeleton()">
            <span>📐</span> Skeleton
          </button>
          <button class="sb-quick-btn active" id="sb-toggle-tts" onclick="window.__sbToggleTTS()">
            <span>🔊</span> Voice TTS
          </button>
          <button class="sb-quick-btn" id="sb-toggle-hud" onclick="window.__sbToggleHud()">
            <span>🪟</span> Preview HUD
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(panel);

    // 2. Create Floating MediaPipe Preview HUD
    mediapipeHud = document.createElement('div');
    mediapipeHud.id = 'sb-mediapipe-hud';
    mediapipeHud.innerHTML = `
      <div id="sb-mediapipe-hud-header">
        <div class="sb-hud-title-wrap">
          <div class="sb-hud-dot"></div>
          <span class="sb-hud-title">MediaPipe Gesture HUD</span>
        </div>
        <div class="sb-hud-badges">
          <span class="sb-hud-badge" id="sb-hud-rt-badge">Rt: 0.94</span>
          <button class="sb-header-btn" id="sb-hud-close-btn" title="Close Preview">×</button>
        </div>
      </div>
      <div id="sb-hud-canvas-wrap">
        <video id="sb-hud-video" autoplay playsinline muted></video>
        <canvas id="sb-hud-canvas" width="320" height="200"></canvas>
      </div>
      <div id="sb-hud-footer">
        <div class="sb-hud-status-chip">
          <span style="color:#ff50dc;">● LH</span>
          <span style="color:#00ffa0;">● RH</span>
          <span style="color:#00e6ff;">● Pose</span>
        </div>
        <span id="sb-hud-tracking-status" style="color:#34a853; font-weight:600;">Tracking Active</span>
      </div>
    `;
    document.body.appendChild(mediapipeHud);

    // 3. Create Direct Google Meet Video Overlay Canvas
    meetVideoCanvas = document.createElement('canvas');
    meetVideoCanvas.id = 'sb-meet-video-skeleton-canvas';
    meetVideoCanvas.width = 640;
    meetVideoCanvas.height = 480;
    document.body.appendChild(meetVideoCanvas);
    meetVideoCtx = meetVideoCanvas.getContext('2d');

    // 4. Create Live Subtitle Banner
    subtitleBanner = document.createElement('div');
    subtitleBanner.id = 'sb-live-subtitle-banner';
    subtitleBanner.innerHTML = `
      <div class="sb-sub-dot"></div>
      <div class="sb-sub-text" id="sb-live-sub-content">Continuous Sign Translation Active</div>
    `;
    document.body.appendChild(subtitleBanner);

    bindDrag();
    bindButtons();
    startRenderLoop();

    console.log(PREFIX, 'MediaPipe Live Gesture Google Meet Overlay Initialized.');
  }

  // ── Drag Functionality ─────────────────────────────────────
  function bindDrag() {
    // Main Panel Drag
    const header = document.getElementById('sb-overlay-header');
    header.addEventListener('mousedown', (e) => {
      if (e.target.classList.contains('sb-header-btn')) return;
      isDragging = true;
      const rect = panel.getBoundingClientRect();
      dragOffsetX = e.clientX - rect.left;
      dragOffsetY = e.clientY - rect.top;
      panel.style.transition = 'none';
    });

    // MediaPipe HUD Drag
    const hudHeader = document.getElementById('sb-mediapipe-hud-header');
    hudHeader.addEventListener('mousedown', (e) => {
      if (e.target.classList.contains('sb-header-btn')) return;
      isHudDragging = true;
      const rect = mediapipeHud.getBoundingClientRect();
      hudOffsetX = e.clientX - rect.left;
      hudOffsetY = e.clientY - rect.top;
    });

    document.addEventListener('mousemove', (e) => {
      if (isDragging) {
        const x = e.clientX - dragOffsetX;
        const y = e.clientY - dragOffsetY;
        panel.style.right = 'auto';
        panel.style.bottom = 'auto';
        panel.style.left = `${Math.max(0, Math.min(x, window.innerWidth - panel.offsetWidth))}px`;
        panel.style.top = `${Math.max(0, Math.min(y, window.innerHeight - panel.offsetHeight))}px`;
      }
      if (isHudDragging) {
        const x = e.clientX - hudOffsetX;
        const y = e.clientY - hudOffsetY;
        mediapipeHud.style.left = `${Math.max(0, Math.min(x, window.innerWidth - mediapipeHud.offsetWidth))}px`;
        mediapipeHud.style.top = `${Math.max(0, Math.min(y, window.innerHeight - mediapipeHud.offsetHeight))}px`;
      }
    });

    document.addEventListener('mouseup', () => {
      isDragging = false;
      isHudDragging = false;
      if (panel) panel.style.transition = 'height 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease';
    });
  }

  // ── Buttons ────────────────────────────────────────────────
  function bindButtons() {
    document.getElementById('sb-collapse-btn').onclick = () => {
      isCollapsed = !isCollapsed;
      panel.classList.toggle('collapsed', isCollapsed);
      document.getElementById('sb-collapse-btn').textContent = isCollapsed ? '+' : '−';
    };
    document.getElementById('sb-close-btn').onclick = () => {
      panel.style.display = 'none';
    };
    document.getElementById('sb-hud-close-btn').onclick = () => {
      mediapipeHud.style.display = 'none';
      showHud = false;
      updateSkeletonButtonState();
    };
  }

  function updateSkeletonButtonState() {
    const btn = document.getElementById('sb-toggle-skeleton');
    if (btn) btn.classList.toggle('active', showSkeleton);
    const hudBtn = document.getElementById('sb-toggle-hud');
    if (hudBtn) hudBtn.classList.toggle('active', showHud);
  }

  // ── Finding & Attaching to Google Meet Video Element ───────
  function findMeetVideoElement() {
    if (activeVideoEl && document.contains(activeVideoEl) && activeVideoEl.videoWidth > 0) {
      return activeVideoEl;
    }

    // Search for Google Meet active videos
    const videos = Array.from(document.querySelectorAll('video'));
    for (const v of videos) {
      if (v.srcObject && v.srcObject.getVideoTracks && v.srcObject.getVideoTracks().length > 0) {
        const trk = v.srcObject.getVideoTracks()[0];
        if (trk.enabled && trk.readyState === 'live') {
          activeVideoEl = v;
          syncHudVideo(v);
          return v;
        }
      }
    }

    if (videos.length > 0) {
      activeVideoEl = videos[0];
      syncHudVideo(videos[0]);
      return videos[0];
    }
    return null;
  }

  function syncHudVideo(v) {
    const hudVideo = document.getElementById('sb-hud-video');
    if (hudVideo && v && v.srcObject && hudVideo.srcObject !== v.srcObject) {
      hudVideo.srcObject = v.srcObject;
    }
  }

  // ── Skeleton Drawing Engine ────────────────────────────────
  function renderMediaPipeSkeleton(ctx, w, h, data) {
    if (!showSkeleton || !data) return;

    // 1. Pose Skeleton (Electric Cyan)
    if (data.pose && data.pose.length >= 8) {
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = 'rgba(0, 230, 255, 0.9)';
      for (const [idx1, idx2] of POSE_CONNECTIONS) {
        if (data.pose[idx1] && data.pose[idx2]) {
          const p1 = data.pose[idx1];
          const p2 = data.pose[idx2];
          ctx.beginPath();
          ctx.moveTo(p1[0] * w, p1[1] * h);
          ctx.lineTo(p2[0] * w, p2[1] * h);
          ctx.stroke();
        }
      }

      // Pose Joint Circles
      for (const p of data.pose) {
        if (!p) continue;
        const x = p[0] * w;
        const y = p[1] * h;
        ctx.fillStyle = '#00f0ff';
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(x, y, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 2. Facial Key Non-Manual Markers (Soft Cyan Dots)
    if (data.face && data.face.length > 0) {
      ctx.fillStyle = 'rgba(180, 225, 255, 0.75)';
      for (const pt of data.face) {
        ctx.beginPath();
        ctx.arc(pt[0] * w, pt[1] * h, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 3. Left Hand Gestures (Neon Magenta / Pink)
    if (data.left_hand && data.left_hand.length === 21) {
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = 'rgba(255, 80, 220, 0.95)';

      for (const [idx1, idx2] of HAND_CONNECTIONS) {
        const p1 = data.left_hand[idx1];
        const p2 = data.left_hand[idx2];
        ctx.beginPath();
        ctx.moveTo(p1[0] * w, p1[1] * h);
        ctx.lineTo(p2[0] * w, p2[1] * h);
        ctx.stroke();
      }

      let minX = w, maxX = 0, minY = h, maxY = 0;
      for (let i = 0; i < data.left_hand.length; i++) {
        const p = data.left_hand[i];
        const px = p[0] * w;
        const py = p[1] * h;
        if (px < minX) minX = px;
        if (px > maxX) maxX = px;
        if (py < minY) minY = py;
        if (py > maxY) maxY = py;

        const isTip = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20);
        ctx.fillStyle = '#ff78e6';
        ctx.beginPath();
        ctx.arc(px, py, isTip ? 5 : 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }

      // Left Hand Bounding Box & Active Tag
      minX = Math.max(0, minX - 10);
      maxX = Math.min(w, maxX + 10);
      minY = Math.max(0, minY - 10);
      maxY = Math.min(h, maxY + 10);

      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(255, 80, 220, 0.7)';
      ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);

      ctx.fillStyle = 'rgba(255, 80, 220, 0.85)';
      ctx.fillRect(minX, Math.max(12, minY - 14), 70, 14);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px "Google Sans", sans-serif';
      ctx.fillText('LH: TRACKED', minX + 4, Math.max(12, minY - 3));

      // Record tip for motion trail
      const tip = data.left_hand[8];
      lhTrail.push([tip[0] * w, tip[1] * h]);
      if (lhTrail.length > MAX_TRAIL) lhTrail.shift();
    } else {
      if (lhTrail.length > 0) lhTrail.shift();
    }

    // 4. Right Hand Gestures (Neon Emerald Green)
    if (data.right_hand && data.right_hand.length === 21) {
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = 'rgba(0, 255, 160, 0.95)';

      for (const [idx1, idx2] of HAND_CONNECTIONS) {
        const p1 = data.right_hand[idx1];
        const p2 = data.right_hand[idx2];
        ctx.beginPath();
        ctx.moveTo(p1[0] * w, p1[1] * h);
        ctx.lineTo(p2[0] * w, p2[1] * h);
        ctx.stroke();
      }

      let minX = w, maxX = 0, minY = h, maxY = 0;
      for (let i = 0; i < data.right_hand.length; i++) {
        const p = data.right_hand[i];
        const px = p[0] * w;
        const py = p[1] * h;
        if (px < minX) minX = px;
        if (px > maxX) maxX = px;
        if (py < minY) minY = py;
        if (py > maxY) maxY = py;

        const isTip = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20);
        ctx.fillStyle = '#50ffbe';
        ctx.beginPath();
        ctx.arc(px, py, isTip ? 5 : 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }

      // Right Hand Bounding Box & Active Tag
      minX = Math.max(0, minX - 10);
      maxX = Math.min(w, maxX + 10);
      minY = Math.max(0, minY - 10);
      maxY = Math.min(h, maxY + 10);

      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(0, 255, 160, 0.7)';
      ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);

      ctx.fillStyle = 'rgba(0, 255, 160, 0.85)';
      ctx.fillRect(minX, Math.max(12, minY - 14), 72, 14);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 9px "Google Sans", sans-serif';
      ctx.fillText('RH: TRACKED', minX + 4, Math.max(12, minY - 3));

      // Record tip for motion trail
      const tip = data.right_hand[8];
      rhTrail.push([tip[0] * w, tip[1] * h]);
      if (rhTrail.length > MAX_TRAIL) rhTrail.shift();
    } else {
      if (rhTrail.length > 0) rhTrail.shift();
    }

    // 5. Kinematic Motion Trails (Gestural Trajectory Curves)
    if (lhTrail.length > 1) {
      for (let t = 1; t < lhTrail.length; t++) {
        const alpha = t / lhTrail.length;
        ctx.lineWidth = Math.max(1, 3 * alpha);
        ctx.strokeStyle = `rgba(255, 100, 220, ${alpha * 0.8})`;
        ctx.beginPath();
        ctx.moveTo(lhTrail[t - 1][0], lhTrail[t - 1][1]);
        ctx.lineTo(lhTrail[t][0], lhTrail[t][1]);
        ctx.stroke();
      }
    }

    if (rhTrail.length > 1) {
      for (let t = 1; t < rhTrail.length; t++) {
        const alpha = t / rhTrail.length;
        ctx.lineWidth = Math.max(1, 3 * alpha);
        ctx.strokeStyle = `rgba(0, 255, 180, ${alpha * 0.8})`;
        ctx.beginPath();
        ctx.moveTo(rhTrail[t - 1][0], rhTrail[t - 1][1]);
        ctx.lineTo(rhTrail[t][0], rhTrail[t][1]);
        ctx.stroke();
      }
    }
  }

  // ── Render Loop (60 FPS requestAnimationFrame) ─────────────
  function startRenderLoop() {
    function loop() {
      // 1. Render onto Floating MediaPipe HUD Canvas
      const hudCanvas = document.getElementById('sb-hud-canvas');
      if (hudCanvas && showHud && mediapipeHud.style.display !== 'none') {
        const hCtx = hudCanvas.getContext('2d');
        hCtx.clearRect(0, 0, hudCanvas.width, hudCanvas.height);
        renderMediaPipeSkeleton(hCtx, hudCanvas.width, hudCanvas.height, currentLandmarks);
      }

      // 2. Position & Render onto Google Meet Active Video Element
      const meetVid = findMeetVideoElement();
      if (meetVid && showSkeleton) {
        const rect = meetVid.getBoundingClientRect();
        if (rect.width > 50 && rect.height > 50) {
          meetVideoCanvas.style.display = 'block';
          meetVideoCanvas.style.left = `${rect.left}px`;
          meetVideoCanvas.style.top = `${rect.top}px`;
          meetVideoCanvas.style.width = `${rect.width}px`;
          meetVideoCanvas.style.height = `${rect.height}px`;

          if (meetVideoCanvas.width !== rect.width || meetVideoCanvas.height !== rect.height) {
            meetVideoCanvas.width = rect.width;
            meetVideoCanvas.height = rect.height;
          }

          meetVideoCtx.clearRect(0, 0, meetVideoCanvas.width, meetVideoCanvas.height);
          renderMediaPipeSkeleton(meetVideoCtx, meetVideoCanvas.width, meetVideoCanvas.height, currentLandmarks);
        } else {
          meetVideoCanvas.style.display = 'none';
        }
      } else {
        meetVideoCanvas.style.display = 'none';
      }

      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  // ── Public API ─────────────────────────────────────────────
  window.__sbOverlay = {
    create: createOverlayPanel,

    setStatus(active, text) {
      const dot = document.getElementById('sb-status-dot');
      const txt = document.getElementById('sb-status-text');
      if (dot) dot.className = active ? 'active' : '';
      if (txt) txt.textContent = active ? '🟢 Sign Translation Active' : (text || '🔴 Inactive');
    },

    updateDetection(sign, confidence) {
      const el = document.getElementById('sb-detected-sign');
      const bar = document.getElementById('sb-confidence-bar');
      if (el) {
        el.textContent = sign || '—';
        el.style.color = '#8ab4f8';
        setTimeout(() => { if (el) el.style.color = '#e8eaed'; }, 700);
      }
      if (bar) bar.style.width = `${Math.round((confidence || 0) * 100)}%`;

      if (sign && sign !== '—') {
        this.showSubtitle(sign);
      }
    },

    updateLandmarks(data) {
      if (!data) return;
      currentLandmarks = {
        pose: data.pose || currentLandmarks.pose,
        left_hand: data.left_hand || null,
        right_hand: data.right_hand || null,
        face: data.face || currentLandmarks.face,
        has_hands: data.has_hands ?? (!!data.left_hand || !!data.right_hand),
        has_left: data.has_left ?? (!!data.left_hand),
        has_right: data.has_right ?? (!!data.right_hand),
        reliability: data.reliability || 0.94,
        timestamp: Date.now()
      };

      const rtBadge = document.getElementById('sb-hud-rt-badge');
      if (rtBadge && data.reliability) {
        rtBadge.textContent = `Rt: ${data.reliability.toFixed(2)}`;
      }

      const trackStatus = document.getElementById('sb-hud-tracking-status');
      if (trackStatus) {
        if (currentLandmarks.has_hands) {
          trackStatus.textContent = 'Gestures Tracked';
          trackStatus.style.color = '#00ffa0';
        } else {
          trackStatus.textContent = 'Searching Hands';
          trackStatus.style.color = '#8ab4f8';
        }
      }
    },

    setVideoSource(vidEl) {
      if (vidEl) {
        activeVideoEl = vidEl;
        syncHudVideo(vidEl);
      }
    },

    showSubtitle(text) {
      if (!subtitleBanner) return;
      const subContent = document.getElementById('sb-live-sub-content');
      if (subContent) subContent.textContent = `"${text}"`;
      subtitleBanner.classList.add('visible');

      if (subtitleTimer) clearTimeout(subtitleTimer);
      subtitleTimer = setTimeout(() => {
        if (subtitleBanner) subtitleBanner.classList.remove('visible');
      }, 4500);
    },

    setProcessing(processing) {
      const dot = document.getElementById('sb-status-dot');
      if (dot) dot.className = processing ? 'processing' : 'active';
    },

    toggleSkeleton() {
      showSkeleton = !showSkeleton;
      updateSkeletonButtonState();
      console.log(PREFIX, 'Skeleton overlay toggled:', showSkeleton);
    },

    toggleHud() {
      showHud = !showHud;
      if (mediapipeHud) {
        mediapipeHud.style.display = showHud ? 'block' : 'none';
      }
      updateSkeletonButtonState();
    },

    show() {
      if (panel) panel.style.display = '';
      if (mediapipeHud && showHud) mediapipeHud.style.display = 'block';
    },

    hide() {
      if (panel) panel.style.display = 'none';
      if (mediapipeHud) mediapipeHud.style.display = 'none';
      if (meetVideoCanvas) meetVideoCanvas.style.display = 'none';
    }
  };

  // Toggle callbacks for content.js
  window.__sbToggleDetect = () => document.dispatchEvent(new CustomEvent('sb:toggle', { detail: 'detect' }));
  window.__sbToggleSkeleton = () => window.__sbOverlay.toggleSkeleton();
  window.__sbToggleHud = () => window.__sbOverlay.toggleHud();
  window.__sbToggleAvatar = () => document.dispatchEvent(new CustomEvent('sb:toggle', { detail: 'avatar' }));
  window.__sbToggleRecord = () => document.dispatchEvent(new CustomEvent('sb:toggle', { detail: 'record' }));
  window.__sbToggleTTS = () => document.dispatchEvent(new CustomEvent('sb:toggle', { detail: 'tts' }));

  console.log(PREFIX, 'Google Flow uiOverlay.js with MediaPipe Live Skeleton loaded.');
})();
