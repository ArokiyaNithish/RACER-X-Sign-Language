// ════════════════════════════════════════════════════════════════
// SignBridge — avatarRenderer.js
// Interactive 2D/3D Canvas Sign Language Avatar
// Translates Spoken Speech into Animated Sign Language Gestures
// ════════════════════════════════════════════════════════════════

(function () {
    'use strict';
    if (window.__sbAvatarLoaded) return;
    window.__sbAvatarLoaded = true;

    const PREFIX = '[SignBridge Avatar]';
    const CANVAS_W = 220;
    const CANVAS_H = 310;
    const ANIM_DURATION = 350; // ms per sign transition

    let panel = null;
    let canvas = null;
    let ctx = null;
    let isVisible = false;

    // Animation state
    let currentPose = null;
    let targetPose = null;
    let animStart = null;
    let animFrame = null;
    let currentSign = 'IDLE';

    // Queue for sequential sign sentences
    let signQueue = [];
    let isPlayingQueue = false;

    // ── Helper: 21-joint standard hand templates ────────────────
    function makeHandPose(wristX, wristY, openSpread = 1.0, fingerCurl = [0, 0, 0, 0, 0], rotAngle = 0) {
        // Generates 21 normalized landmarks matching MediaPipe hand topology
        const pts = [];
        const scale = 28;
        const cosR = Math.cos(rotAngle);
        const sinR = Math.sin(rotAngle);

        function rot(x, y) {
            return {
                x: wristX + (x * cosR - y * sinR),
                y: wristY + (x * sinR + y * cosR)
            };
        }

        // 0: Wrist
        pts.push(rot(0, 0));

        // Thumb: 1, 2, 3, 4
        const thumbCurl = fingerCurl[0];
        pts.push(rot(-8 * openSpread, -6));
        pts.push(rot(-14 * openSpread, -12));
        pts.push(rot(-18 * openSpread * (1 - thumbCurl * 0.4), -18 + thumbCurl * 8));
        pts.push(rot(-22 * openSpread * (1 - thumbCurl * 0.7), -22 + thumbCurl * 14));

        // 4 fingers: Index (5-8), Middle (9-12), Ring (13-16), Pinky (17-20)
        const baseAngles = [-0.25, -0.08, 0.08, 0.25];
        const lengths = [32, 36, 33, 26];

        for (let f = 0; f < 4; f++) {
            const curl = fingerCurl[f + 1];
            const ang = baseAngles[f] * openSpread;
            const len = lengths[f];
            const baseOffX = (f - 1.5) * 5;

            // MCP
            pts.push(rot(baseOffX, -16));
            // PIP
            pts.push(rot(baseOffX + Math.sin(ang) * (len * 0.4), -16 - Math.cos(ang) * (len * 0.4) * (1 - curl * 0.3)));
            // DIP
            pts.push(rot(baseOffX + Math.sin(ang) * (len * 0.75), -16 - Math.cos(ang) * (len * 0.75) * (1 - curl * 0.6) + curl * 10));
            // TIP
            pts.push(rot(baseOffX + Math.sin(ang) * len, -16 - Math.cos(ang) * len * (1 - curl * 0.9) + curl * 20));
        }

        return pts;
    }

    // ── Sign Gesture Library (Keyframes for Spoken Words) ────────
    const SIGN_LIBRARY = {
        'IDLE': {
            name: 'Ready',
            leftArm: { x: 70, y: 195, hand: makeHandPose(70, 195, 0.8, [0.3, 0.4, 0.4, 0.4, 0.4], 0.2) },
            rightArm: { x: 150, y: 195, hand: makeHandPose(150, 195, 0.8, [0.3, 0.4, 0.4, 0.4, 0.4], -0.2) }
        },
        'HELLO': {
            name: 'HELLO 👋',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 165, y: 75, hand: makeHandPose(165, 75, 1.2, [0, 0, 0, 0, 0], 0.35) }
        },
        'WELCOME': {
            name: 'WELCOME 🤝',
            leftArm: { x: 80, y: 140, hand: makeHandPose(80, 140, 1.1, [0, 0, 0, 0, 0], 0.2) },
            rightArm: { x: 140, y: 140, hand: makeHandPose(140, 140, 1.1, [0, 0, 0, 0, 0], -0.2) }
        },
        'THANK': {
            name: 'THANK YOU 🙏',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.5, 0.5, 0.5, 0.5, 0.5]) },
            rightArm: { x: 120, y: 110, hand: makeHandPose(120, 110, 1.0, [0, 0, 0, 0, 0], -0.1) }
        },
        'YOU': {
            name: 'YOU 👉',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.5, 0.5, 0.5, 0.5, 0.5]) },
            rightArm: { x: 135, y: 130, hand: makeHandPose(135, 130, 0.9, [0.9, 0, 0.9, 0.9, 0.9], -0.1) }
        },
        'YES': {
            name: 'YES ✅',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 145, y: 120, hand: makeHandPose(145, 120, 0.5, [0.95, 0.95, 0.95, 0.95, 0.95], 0.1) }
        },
        'NO': {
            name: 'NO ❌',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 140, y: 115, hand: makeHandPose(140, 115, 0.8, [0.1, 0.1, 0.1, 0.9, 0.9], -0.2) }
        },
        'PLEASE': {
            name: 'PLEASE 🤲',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 110, y: 135, hand: makeHandPose(110, 135, 1.0, [0, 0, 0, 0, 0], 0.4) }
        },
        'GOOD': {
            name: 'GOOD 👍',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 140, y: 110, hand: makeHandPose(140, 110, 1.2, [0, 0.9, 0.9, 0.9, 0.9], -0.1) }
        },
        'HELP': {
            name: 'HELP 🆘',
            leftArm: { x: 100, y: 155, hand: makeHandPose(100, 155, 1.0, [0, 0, 0, 0, 0], 0) },
            rightArm: { x: 110, y: 130, hand: makeHandPose(110, 130, 0.7, [0, 0.95, 0.95, 0.95, 0.95], 0) }
        },
        'HOW': {
            name: 'HOW ❓',
            leftArm: { x: 85, y: 135, hand: makeHandPose(85, 135, 1.0, [0.2, 0, 0, 0, 0], 0.3) },
            rightArm: { x: 135, y: 135, hand: makeHandPose(135, 135, 1.0, [0.2, 0, 0, 0, 0], -0.3) }
        },
        'PROJECT': {
            name: 'PROJECT 💻',
            leftArm: { x: 90, y: 145, hand: makeHandPose(90, 145, 0.9, [0.8, 0, 0, 0.8, 0.8], 0.2) },
            rightArm: { x: 130, y: 135, hand: makeHandPose(130, 135, 0.9, [0.8, 0, 0, 0.8, 0.8], -0.2) }
        },
        'BYE': {
            name: 'GOODBYE 👋',
            leftArm: { x: 65, y: 190, hand: makeHandPose(65, 190, 0.8, [0.4, 0.4, 0.4, 0.4, 0.4]) },
            rightArm: { x: 160, y: 80, hand: makeHandPose(160, 80, 1.2, [0, 0, 0, 0, 0], 0.25) }
        }
    };

    // ── Create Panel UI ─────────────────────────
    function createAvatarPanel() {
        if (document.getElementById('sb-avatar-panel')) return;

        const style = document.createElement('style');
        style.id = 'sb-avatar-styles';
        style.textContent = `
            #sb-avatar-panel {
                position: fixed;
                bottom: 84px;
                left: 24px;
                width: ${CANVAS_W + 16}px;
                background: rgba(15, 20, 32, 0.92);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(0, 212, 255, 0.35);
                border-radius: 18px;
                padding: 10px;
                z-index: 999998;
                display: none;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                box-shadow: 0 16px 48px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 212, 255, 0.2);
                font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
                user-select: none;
                transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            }
            #sb-avatar-panel.visible { display: flex; }

            .sb-avatar-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                width: 100%;
                padding: 0 4px;
            }
            .sb-avatar-title {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 11px;
                font-weight: 700;
                color: #00D4FF;
                letter-spacing: 0.8px;
                text-transform: uppercase;
            }
            .sb-avatar-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #00ffa0;
                box-shadow: 0 0 8px #00ffa0;
            }
            .sb-avatar-close {
                background: rgba(255, 255, 255, 0.1);
                border: none;
                color: #9aa0a6;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 13px;
                cursor: pointer;
            }
            .sb-avatar-close:hover { background: rgba(255, 255, 255, 0.2); color: #fff; }

            #sb-avatar-speech-bubble {
                width: 95%;
                background: rgba(0, 212, 255, 0.1);
                border: 1px solid rgba(0, 212, 255, 0.25);
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 10.5px;
                color: #e8eaed;
                text-align: center;
                min-height: 20px;
                word-break: break-word;
            }

            #sb-avatar-canvas {
                border-radius: 12px;
                background: #090d16;
                box-shadow: inset 0 0 16px rgba(0, 0, 0, 0.8);
                display: block;
            }

            #sb-avatar-sign-badge {
                font-size: 13px;
                font-weight: 700;
                color: #00ffa0;
                letter-spacing: 0.5px;
                text-align: center;
                min-height: 20px;
            }
        `;
        document.head.appendChild(style);

        panel = document.createElement('div');
        panel.id = 'sb-avatar-panel';
        panel.innerHTML = `
            <div class="sb-avatar-header">
                <div class="sb-avatar-title">
                    <span class="sb-avatar-dot"></span>
                    <span>Sign Avatar</span>
                </div>
                <button class="sb-avatar-close" id="sb-avatar-close-btn" title="Hide Avatar">×</button>
            </div>
            <div id="sb-avatar-speech-bubble">Listening to participants...</div>
            <canvas id="sb-avatar-canvas" width="${CANVAS_W}" height="${CANVAS_H}"></canvas>
            <div id="sb-avatar-sign-badge">READY</div>
        `;
        document.body.appendChild(panel);

        document.getElementById('sb-avatar-close-btn').addEventListener('click', hide);

        canvas = document.getElementById('sb-avatar-canvas');
        ctx = canvas.getContext('2d');

        currentPose = SIGN_LIBRARY.IDLE;
        targetPose = SIGN_LIBRARY.IDLE;
        renderPose(currentPose, 1.0);
        console.log(PREFIX, 'Avatar panel initialized.');
    }

    // ── Show / Hide ──────────────────────────────
    function show() {
        if (!panel) createAvatarPanel();
        isVisible = true;
        panel.classList.add('visible');
    }

    function hide() {
        isVisible = false;
        if (panel) panel.classList.remove('visible');
        if (animFrame) {
            cancelAnimationFrame(animFrame);
            animFrame = null;
        }
    }

    // ── Render Avatar Figure ─────────────────────
    function renderPose(pose, progress = 1.0) {
        if (!ctx) return;
        ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

        // Background
        const bg = ctx.createLinearGradient(0, 0, 0, CANVAS_H);
        bg.addColorStop(0, '#0e1424');
        bg.addColorStop(1, '#070a12');
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

        // Subtle background grid
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.05)';
        ctx.lineWidth = 0.5;
        for (let x = 0; x <= CANVAS_W; x += 22) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, CANVAS_H); ctx.stroke();
        }
        for (let y = 0; y <= CANVAS_H; y += 22) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(CANVAS_W, y); ctx.stroke();
        }

        const headX = CANVAS_W / 2;
        const headY = 62;

        // Neck
        ctx.fillStyle = '#1c2638';
        ctx.fillRect(headX - 9, headY + 28, 18, 20);

        // Torso
        const torsoGrad = ctx.createLinearGradient(60, 110, 160, 220);
        torsoGrad.addColorStop(0, '#1c2844');
        torsoGrad.addColorStop(1, '#111726');
        ctx.fillStyle = torsoGrad;
        ctx.beginPath();
        ctx.moveTo(headX - 45, headY + 45); // Left shoulder
        ctx.quadraticCurveTo(headX - 52, 180, headX - 48, 230);
        ctx.lineTo(headX + 48, 230);
        ctx.quadraticCurveTo(headX + 52, 180, headX + 45, headY + 45); // Right shoulder
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.25)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Head
        ctx.fillStyle = '#22324b';
        ctx.beginPath();
        ctx.ellipse(headX, headY, 28, 34, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.45)';
        ctx.lineWidth = 1.8;
        ctx.stroke();

        // Stylized visor/eyes
        ctx.fillStyle = 'rgba(0, 255, 160, 0.7)';
        ctx.shadowColor = '#00ffa0';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.roundRect(headX - 16, headY - 4, 32, 7, 3);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Shoulders
        const leftShoulder = { x: headX - 45, y: headY + 45 };
        const rightShoulder = { x: headX + 45, y: headY + 45 };

        // Arms and Hands
        drawArmAndHand(ctx, leftShoulder, pose.leftArm, '#A855F7', 'LH');
        drawArmAndHand(ctx, rightShoulder, pose.rightArm, '#00D4FF', 'RH');
    }

    function drawArmAndHand(ctx, shoulder, armData, color, label) {
        if (!armData) return;
        const targetX = armData.x;
        const targetY = armData.y;

        // Elbow joint
        const elbowX = (shoulder.x + targetX) / 2 + (shoulder.x < targetX ? 12 : -12);
        const elbowY = Math.max(shoulder.y, targetY) + 15;

        // Draw arm segments
        ctx.strokeStyle = color.replace(')', ', 0.65)').replace('rgb', 'rgba');
        ctx.lineWidth = 8;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(shoulder.x, shoulder.y);
        ctx.quadraticCurveTo(elbowX, elbowY, targetX, targetY);
        ctx.stroke();

        // Draw hand landmarks
        if (armData.hand && armData.hand.length >= 21) {
            drawHandLandmarks(ctx, armData.hand, color);
        } else {
            // Schematic hand fallback
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(targetX, targetY, 8, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function drawHandLandmarks(ctx, pts, color) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';

        const CONNECTIONS = [
            [0, 1], [1, 2], [2, 3], [3, 4],
            [0, 5], [5, 6], [6, 7], [7, 8],
            [5, 9], [9, 10], [10, 11], [11, 12],
            [9, 13], [13, 14], [14, 15], [15, 16],
            [13, 17], [17, 18], [18, 19], [19, 20],
            [0, 17]
        ];

        CONNECTIONS.forEach(([a, b]) => {
            if (!pts[a] || !pts[b]) return;
            ctx.beginPath();
            ctx.moveTo(pts[a].x, pts[a].y);
            ctx.lineTo(pts[b].x, pts[b].y);
            ctx.stroke();
        });

        pts.forEach((pt, i) => {
            ctx.fillStyle = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20) ? '#ffffff' : color;
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, i === 0 ? 3.5 : 2, 0, Math.PI * 2);
            ctx.fill();
        });

        ctx.shadowBlur = 0;
    }

    // ── Animation Interpolation ──────────────────
    function interpolateArm(fromArm, toArm, t) {
        return {
            x: fromArm.x + (toArm.x - fromArm.x) * t,
            y: fromArm.y + (toArm.y - fromArm.y) * t,
            hand: toArm.hand.map((pt, i) => ({
                x: (fromArm.hand[i]?.x ?? pt.x) + ((pt.x) - (fromArm.hand[i]?.x ?? pt.x)) * t,
                y: (fromArm.hand[i]?.y ?? pt.y) + ((pt.y) - (fromArm.hand[i]?.y ?? pt.y)) * t
            }))
        };
    }

    function animateToPose(newTargetPose, signLabel, onComplete) {
        targetPose = newTargetPose;
        animStart = null;

        function tick(ts) {
            if (!animStart) animStart = ts;
            const elapsed = ts - animStart;
            const progress = Math.min(elapsed / ANIM_DURATION, 1.0);
            const ease = 1 - Math.pow(1 - progress, 3); // Cubic ease out

            const interpolated = {
                leftArm: interpolateArm(currentPose.leftArm, targetPose.leftArm, ease),
                rightArm: interpolateArm(currentPose.rightArm, targetPose.rightArm, ease)
            };

            renderPose(interpolated, ease);

            if (progress < 1.0) {
                animFrame = requestAnimationFrame(tick);
            } else {
                currentPose = targetPose;
                animFrame = null;
                if (onComplete) onComplete();
            }
        }

        if (animFrame) cancelAnimationFrame(animFrame);
        animFrame = requestAnimationFrame(tick);

        const badge = document.getElementById('sb-avatar-sign-badge');
        if (badge) badge.textContent = signLabel || targetPose.name || 'SIGN';
    }

    // ── Sequential Sentence Signing ──────────────
    function signSentence(sentence) {
        if (!sentence || !sentence.trim()) return;

        // Update speech bubble
        const bubble = document.getElementById('sb-avatar-speech-bubble');
        if (bubble) bubble.textContent = `"${sentence.trim()}"`;

        const words = sentence.toUpperCase().replace(/[^A-Z\s]/g, '').split(/\s+/).filter(Boolean);
        if (words.length === 0) return;

        // Build gesture list
        signQueue = [];
        words.forEach(w => {
            if (SIGN_LIBRARY[w]) {
                signQueue.push({ pose: SIGN_LIBRARY[w], label: SIGN_LIBRARY[w].name });
            } else if (w.includes('HOW') || w.includes('YOU')) {
                signQueue.push({ pose: SIGN_LIBRARY['HOW'], label: 'HOW ❓' });
            } else if (w.includes('THANK')) {
                signQueue.push({ pose: SIGN_LIBRARY['THANK'], label: 'THANK YOU 🙏' });
            } else {
                // Fallback: use key conversational pose
                signQueue.push({ pose: SIGN_LIBRARY['WELCOME'], label: `${w} 🤟` });
            }
        });

        // Add return to IDLE at the end
        signQueue.push({ pose: SIGN_LIBRARY.IDLE, label: 'READY' });

        if (!isPlayingQueue) {
            playNextSign();
        }
    }

    function playNextSign() {
        if (signQueue.length === 0) {
            isPlayingQueue = false;
            return;
        }

        isPlayingQueue = true;
        const next = signQueue.shift();

        animateToPose(next.pose, next.label, () => {
            // Pause briefly on the gesture before playing next
            setTimeout(playNextSign, 300);
        });
    }

    // ── External API ─────────────────────────────
    window.__sbAvatar = {
        create: createAvatarPanel,
        show,
        hide,
        signText: signSentence,
        render: (left, right, sign) => {
            // Direct landmark injection support
            if (sign && SIGN_LIBRARY[sign]) {
                animateToPose(SIGN_LIBRARY[sign], sign);
            }
        },
        isVisible: () => isVisible
    };

    // Global event listeners
    document.addEventListener('sb:avatarSign', (e) => {
        const { text, sign } = e.detail || {};
        show();
        if (text) signSentence(text);
        else if (sign && SIGN_LIBRARY[sign]) animateToPose(SIGN_LIBRARY[sign], sign);
    });

    console.log(PREFIX, 'avatarRenderer.js loaded with Sign Library.');
})();
