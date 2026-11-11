import os
import sys
import time
import json
import argparse
import queue
import threading
from collections import deque
import numpy as np
import cv2
import torch
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from racer_model import RacerXNetwork

# -------------------------------------------------------------
# Configuration & Constants
# -------------------------------------------------------------
CHECKPOINT_PATH = os.path.join("checkpoints", "best_racer_x.pth")
VOCAB_PATH = os.path.join("checkpoints", "vocab.json")
MODEL_DIR = "models"
HOLISTIC_TASK_PATH = os.path.join(MODEL_DIR, "holistic_landmarker.task")
WINDOW_NAME = "RACER-X: Continuous Sign Language Video Translation (MediaPipe Live)"

POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0]  # 9 landmarks
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152] # 22 landmarks

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]

POSE_CONNECTIONS = [
    (11, 12), # Shoulder-to-shoulder
    (11, 13), (13, 15), # Left arm: Shoulder -> Elbow -> Wrist
    (12, 14), (14, 16), # Right arm: Shoulder -> Elbow -> Wrist
    (11, 23), (12, 24), # Torso sides
    (23, 24)  # Hip line
]

# Key facial non-manual sign contours
FACE_KEY_POINTS = [
    33, 133, 159, 145,       # Left eye
    362, 263, 386, 374,      # Right eye
    70, 63, 105, 66,         # Left eyebrow
    300, 293, 334, 296,      # Right eyebrow
    0, 13, 14, 17, 61, 291   # Mouth and lips
]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------------------------------------
# Asynchronous Text-to-Speech Worker
# -------------------------------------------------------------
speech_queue = queue.Queue()

def tts_worker():
    tts_engine = None
    try:
        import pyttsx3
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', 150)
    except Exception:
        tts_engine = None

    while True:
        text = speech_queue.get()
        if text is None:
            break
        text = text.strip()
        if not text:
            speech_queue.task_done()
            continue

        try:
            if tts_engine:
                tts_engine.say(text)
                tts_engine.runAndWait()
            else:
                clean_text = text.replace('"', '').replace("'", "")
                cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{clean_text}\')"'
                os.system(cmd)
        except Exception:
            pass
        speech_queue.task_done()

tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

def speak_async(text):
    if text and text.strip():
        speech_queue.put(text)

# -------------------------------------------------------------
# Feature Extraction Functions
# -------------------------------------------------------------
def extract_landmarks(res):
    if res.pose_landmarks and len(res.pose_landmarks) > max(POSE_INDICES):
        pose = [[res.pose_landmarks[i].x, res.pose_landmarks[i].y, res.pose_landmarks[i].z,
                 getattr(res.pose_landmarks[i], 'visibility', 1.0)]
                for i in POSE_INDICES]
    else:
        pose = [[0.0] * 4] * len(POSE_INDICES)

    if res.face_landmarks and len(res.face_landmarks) > max(FACE_INDICES):
        face = [[res.face_landmarks[i].x, res.face_landmarks[i].y, res.face_landmarks[i].z, 1.0]
                for i in FACE_INDICES]
    else:
        face = [[0.0] * 4] * len(FACE_INDICES)

    if res.left_hand_landmarks and len(res.left_hand_landmarks) == 21:
        lh = [[lm.x, lm.y, lm.z, 1.0] for lm in res.left_hand_landmarks]
    else:
        lh = [[0.0] * 4] * 21

    if res.right_hand_landmarks and len(res.right_hand_landmarks) == 21:
        rh = [[lm.x, lm.y, lm.z, 1.0] for lm in res.right_hand_landmarks]
    else:
        rh = [[0.0] * 4] * 21

    raw = np.concatenate([pose, face, lh, rh]).flatten()
    if len(raw) < 300:
        raw = np.pad(raw, (0, 300 - len(raw)), mode='constant')
    return raw[:300].astype(np.float32)

def draw_skeleton(frame, res, lh_trail=None, rh_trail=None):
    """
    Renders the sign language skeleton on the video frame using MediaPipe Holistic landmarks.
    Shows pose connections, face markers, and vibrant bilateral hand gestures with tracking boxes.
    """
    h, w, _ = frame.shape

    # 1. Pose Upper Body & Arm Skeleton (Electric Cyan)
    if res.pose_landmarks and len(res.pose_landmarks) > 24:
        for idx1, idx2 in POSE_CONNECTIONS:
            p1, p2 = res.pose_landmarks[idx1], res.pose_landmarks[idx2]
            pt1 = (int(p1.x * w), int(p1.y * h))
            pt2 = (int(p2.x * w), int(p2.y * h))
            cv2.line(frame, pt1, pt2, (40, 190, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, pt1, 4, (0, 240, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt2, 4, (0, 240, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt1, 2, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt2, 2, (255, 255, 255), -1, cv2.LINE_AA)

    # 2. Facial Key Non-Manual Markers (Subtle soft cyan dots)
    if res.face_landmarks and len(res.face_landmarks) > 300:
        for f_idx in FACE_KEY_POINTS:
            lm = res.face_landmarks[f_idx]
            pt = (int(lm.x * w), int(lm.y * h))
            cv2.circle(frame, pt, 2, (200, 230, 255), -1, cv2.LINE_AA)

    # 3. Left Hand Gestures (Neon Magenta / Pink)
    if res.left_hand_landmarks and len(res.left_hand_landmarks) == 21:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in res.left_hand_landmarks]
        for idx1, idx2 in HAND_CONNECTIONS:
            cv2.line(frame, pts[idx1], pts[idx2], (255, 80, 220), 2, cv2.LINE_AA)
        for i, pt in enumerate(pts):
            radius = 5 if i in [4, 8, 12, 16, 20] else 3
            cv2.circle(frame, pt, radius, (255, 140, 240), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 1, (255, 255, 255), -1, cv2.LINE_AA)

        # Left Hand Bounding Box & Active Tag
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x, max_x = max(0, min(xs) - 12), min(w - 1, max(xs) + 12)
        min_y, max_y = max(0, min(ys) - 12), min(h - 1, max(ys) + 12)
        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (255, 80, 220), 1, cv2.LINE_AA)
        cv2.putText(frame, "LH: TRACKED", (min_x, max(15, min_y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 140, 240), 1, cv2.LINE_AA)

        if lh_trail is not None and len(pts) > 8:
            lh_trail.append(pts[8])  # Track index fingertip
    else:
        if lh_trail is not None and len(lh_trail) > 0:
            lh_trail.popleft()

    # 4. Right Hand Gestures (Neon Emerald Green)
    if res.right_hand_landmarks and len(res.right_hand_landmarks) == 21:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in res.right_hand_landmarks]
        for idx1, idx2 in HAND_CONNECTIONS:
            cv2.line(frame, pts[idx1], pts[idx2], (0, 255, 160), 2, cv2.LINE_AA)
        for i, pt in enumerate(pts):
            radius = 5 if i in [4, 8, 12, 16, 20] else 3
            cv2.circle(frame, pt, radius, (80, 255, 200), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 1, (255, 255, 255), -1, cv2.LINE_AA)

        # Right Hand Bounding Box & Active Tag
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x, max_x = max(0, min(xs) - 12), min(w - 1, max(xs) + 12)
        min_y, max_y = max(0, min(ys) - 12), min(h - 1, max(ys) + 12)
        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (0, 255, 160), 1, cv2.LINE_AA)
        cv2.putText(frame, "RH: TRACKED", (min_x, max(15, min_y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 255, 200), 1, cv2.LINE_AA)

        if rh_trail is not None and len(pts) > 8:
            rh_trail.append(pts[8])  # Track index fingertip
    else:
        if rh_trail is not None and len(rh_trail) > 0:
            rh_trail.popleft()

    # 5. Kinematic Motion Trails (Gestural Trajectory)
    if lh_trail and len(lh_trail) > 1:
        for t in range(1, len(lh_trail)):
            alpha = t / len(lh_trail)
            thickness = max(1, int(3 * alpha))
            cv2.line(frame, lh_trail[t - 1], lh_trail[t], (255, 100, 220), thickness, cv2.LINE_AA)

    if rh_trail and len(rh_trail) > 1:
        for t in range(1, len(rh_trail)):
            alpha = t / len(rh_trail)
            thickness = max(1, int(3 * alpha))
            cv2.line(frame, rh_trail[t - 1], rh_trail[t], (0, 255, 180), thickness, cv2.LINE_AA)

def compute_kinematics(seq):
    T = seq.shape[0]
    reshaped = seq.reshape(T, 75, 4)
    P = reshaped[:, :, :3]
    C = reshaped[:, :, 3]

    # Adaptive Torso-Invariant Normalization
    left_shoulder = P[:, 0, :]
    right_shoulder = P[:, 1, :]
    mid_shoulder = (left_shoulder + right_shoulder) / 2.0
    raw_scale = np.linalg.norm(left_shoulder - right_shoulder, axis=-1, keepdims=True)
    scale = np.clip(raw_scale, 0.10, 2.0)
    P_norm = (P - mid_shoulder[:, np.newaxis, :]) / scale[:, np.newaxis, :]

    V = np.zeros_like(P_norm)
    V[1:] = P_norm[1:] - P_norm[:-1]

    A = np.zeros_like(V)
    A[1:] = V[1:] - V[:-1]

    J = np.zeros_like(A)
    J[1:] = A[1:] - A[:-1]

    cross_va = np.cross(V, A)
    norm_cross_va = np.linalg.norm(cross_va, axis=-1)
    norm_v = np.linalg.norm(V, axis=-1)
    kappa = norm_cross_va / (np.power(norm_v, 3) + 1e-4)
    kappa = np.clip(kappa, 0.0, 10.0)

    dot_vaj = np.sum(cross_va * J, axis=-1)
    tau = dot_vaj / (np.power(norm_cross_va, 2) + 1e-4)
    tau = np.clip(tau, -10.0, 10.0)

    jerk_magnitude = np.linalg.norm(J, axis=-1).mean(axis=-1, keepdims=True)
    mean_conf = C.mean(axis=-1, keepdims=True)
    R = mean_conf * np.exp(-0.5 * jerk_magnitude)

    P_flat = P_norm.reshape(T, -1)
    V_flat = V.reshape(T, -1)
    A_flat = A.reshape(T, -1)
    J_flat = J.reshape(T, -1)
    kappa_flat = kappa.reshape(T, -1)
    tau_flat = tau.reshape(T, -1)

    M_flat = np.concatenate([V_flat, A_flat, J_flat, kappa_flat, tau_flat], axis=-1)
    return P_flat, M_flat, R

CLEAN_CSV = os.path.join("dataset", "master_dataset_clean.csv")

def ctc_decode_robust(log_probs, inv_vocab, prior_penalty=None):
    """
    Balanced Bayesian CTC sequence decoding.
    Discounts high-frequency prior tokens to ensure diverse, accurate recognition.
    """
    lp = log_probs.squeeze(0)
    if prior_penalty is not None:
        lp = lp - (0.35 * prior_penalty.to(lp.device).unsqueeze(0))

    pred_indices = torch.argmax(lp, dim=-1).cpu().numpy()
    collapsed = []
    prev = None
    for idx in pred_indices:
        if idx != prev:
            if idx > 1:  # skip blank (0) and unk (1)
                collapsed.append(idx)
            prev = idx
    words = [inv_vocab.get(i, "") for i in collapsed if i in inv_vocab]
    return " ".join([w for w in words if w])

# -------------------------------------------------------------
# Main Video Processor
# -------------------------------------------------------------
def process_video(video_path, output_path=None, show_display=True):
    print("=" * 70)
    print("RACER-X: MediaPipe Live Gesture Video Translator")
    print("Department of AI & DS, Vel Tech R&D Institute, Chennai, India")
    print("=" * 70)

    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        print(f"[-] Error: Video file not found: {video_path}")
        print("[!] Please check the path and try again.")
        return

    # Automatically set output path if not given
    if not output_path:
        base, ext = os.path.splitext(os.path.basename(video_path))
        output_path = f"output_{base}.mp4"

    # Load Vocab
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    inv_vocab = {v: k for k, v in vocab.items()}

    # Compute class prior frequency discount
    prior_penalty = torch.zeros(len(vocab))
    if os.path.exists(CLEAN_CSV):
        try:
            import pandas as pd
            df_meta = pd.read_csv(CLEAN_CSV)
            counts = torch.ones(len(vocab))
            for s in df_meta['sentence']:
                for w in str(s).upper().split():
                    if w in vocab:
                        counts[vocab[w]] += 1.0
            prior_penalty = torch.log(counts)
            prior_penalty[0] = 0.0
            prior_penalty[1] = 0.0
        except Exception:
            pass

    # Load Model
    print(f"[+] Loading RACER-X model checkpoint on {DEVICE}...")
    model = RacerXNetwork(vocab_size=len(vocab)).to(DEVICE)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Load MediaPipe Tasks Holistic
    print(f"[+] Initializing MediaPipe Holistic Landmarker ({HOLISTIC_TASK_PATH})...")
    base_options = python.BaseOptions(model_asset_path=HOLISTIC_TASK_PATH)
    options = vision.HolisticLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_segmentation_mask=False
    )
    landmarker = vision.HolisticLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[+] Loaded Video: {os.path.basename(video_path)}")
    print(f"[+] Dimensions: {orig_w}x{orig_h} | Frames: {total_frames} | FPS: {video_fps:.1f}")

    # Determine render resolution (scale to width 1280 for responsive rendering)
    render_w = 1280 if orig_w > 1280 else orig_w
    render_h = int(orig_h * (render_w / orig_w)) if orig_w > 1280 else orig_h
    # Ensure even dimensions for codec compatibility
    if render_w % 2 != 0: render_w -= 1
    if render_h % 2 != 0: render_h -= 1

    # Initialize VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(output_path, fourcc, video_fps, (render_w, render_h))
    print(f"[+] Output Recording Initialized -> {output_path} ({render_w}x{render_h})")

    BUFFER_SIZE = 48
    frame_buffer = []
    current_sentence = ""
    last_spoken = ""
    avg_rel = 1.0
    paused = False

    lh_trail = deque(maxlen=14)
    rh_trail = deque(maxlen=14)

    if show_display:
        print("\nCONTROLS:")
        print("  [SPACE]   : Pause / Play Live Stream")
        print("  [r]       : Restart Video from Frame 0")
        print("  [s]       : Speak Current Sentence via SpeechSynthesizer")
        print("  [q / ESC] : Finish & Save Video Output\n")

    frame_idx = 0
    start_time = time.time()
    t_prev = time.time()
    current_fps = video_fps

    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print(f"\n[+] Completed processing all {frame_idx} frames.")
                break
            frame_idx += 1

            if frame.shape[1] != render_w or frame.shape[0] != render_h:
                frame = cv2.resize(frame, (render_w, render_h), interpolation=cv2.INTER_AREA)

            h, w = frame.shape[:2]

            # MediaPipe Landmark Detection
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = landmarker.detect(mp_img)

            # Draw MediaPipe Gestures on Frame
            draw_skeleton(frame, results, lh_trail, rh_trail)

            # Extract landmarks for RACER-X inference
            lm_vec = extract_landmarks(results)
            frame_buffer.append(lm_vec)
            if len(frame_buffer) > BUFFER_SIZE:
                frame_buffer.pop(0)

            # Neural prediction every 4 frames
            if len(frame_buffer) >= 20 and frame_idx % 4 == 0:
                seq_arr = np.array(frame_buffer)
                P_f, M_f, R_f = compute_kinematics(seq_arr)
                avg_rel = float(np.mean(R_f))

                p_t = torch.tensor(P_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
                m_t = torch.tensor(M_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
                r_t = torch.tensor(R_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)

                with torch.no_grad():
                    log_probs = model(p_t, m_t, r_t)
                    decoded = ctc_decode_robust(log_probs, inv_vocab, prior_penalty=prior_penalty)

                if decoded and decoded.strip():
                    current_sentence = decoded

            # Compute real-time FPS
            t_now = time.time()
            dt = t_now - t_prev
            if dt > 0:
                current_fps = 0.8 * current_fps + 0.2 * (1.0 / dt)
            t_prev = t_now

        # ---------------------------------------------------------
        # Google Flow Style Glassmorphic HUD Overlays
        # ---------------------------------------------------------
        overlay = frame.copy()

        # 1. Top HUD Glass Bar
        hud_h = 75
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (12, 14, 20), -1)
        # Accent separator line
        cv2.line(overlay, (0, hud_h), (w, hud_h), (45, 55, 75), 1)

        # 2. Bottom Glass Subtitle Bar
        sub_h = 95
        cv2.rectangle(overlay, (0, h - sub_h), (w, h), (10, 12, 18), -1)
        cv2.line(overlay, (0, h - sub_h), (w, h - sub_h), (0, 230, 180), 2)

        # Blend overlays for translucent dark glass look
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

        # Top Bar Content
        # Glowing Live Badge
        badge_color = (0, 255, 140) if (results.left_hand_landmarks or results.right_hand_landmarks) else (80, 160, 255)
        cv2.circle(frame, (25, 26), 6, badge_color, -1, cv2.LINE_AA)
        cv2.putText(frame, "LIVE MEDIAPIPE GESTURE STREAM", (40, 31),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)

        # File & FPS
        fps_text = f"FPS: {current_fps:.1f} | {os.path.basename(video_path)}"
        cv2.putText(frame, fps_text, (w - 380, 31),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 210, 225), 1, cv2.LINE_AA)

        # Reliability Badge
        rel_color = (0, 255, 150) if avg_rel >= 0.85 else ((0, 220, 255) if avg_rel >= 0.70 else (80, 120, 255))
        rel_status = "EXCELLENT" if avg_rel >= 0.85 else ("STABLE" if avg_rel >= 0.70 else "RECOVERY")
        rel_text = f"Reliability Rt: {avg_rel:.2f} ({rel_status}) | Frame: {frame_idx}/{total_frames} | {'PAUSED' if paused else 'LIVE'}"
        cv2.putText(frame, rel_text, (25, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, rel_color, 1, cv2.LINE_AA)

        # Bottom Bar Subtitle
        cv2.putText(frame, "CONTINUOUS SIGN TRANSLATION (BAYESIAN CTC):", (25, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 175, 195), 1, cv2.LINE_AA)

        disp_text = current_sentence if current_sentence else "Analyzing sign stream..."
        col = (0, 255, 160) if current_sentence else (120, 135, 150)

        # Drop shadow for high readability
        cv2.putText(frame, disp_text[:70], (27, h - 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, disp_text[:70], (25, h - 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, col, 2, cv2.LINE_AA)

        # Write frame to video file
        out_writer.write(frame)

        # Display window
        if show_display:
            cv2.imshow(WINDOW_NAME, frame)
            delay = int(1000 / video_fps) if not paused else 50
            key = cv2.waitKey(max(1, delay)) & 0xFF
            if key == ord('q') or key == 27:
                print("\n[!] User terminated playback. Saving video output...")
                break
            elif key == 32:  # SPACE
                paused = not paused
                print(f"[!] Playback {'PAUSED' if paused else 'RESUMED'}")
            elif key == ord('r'):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_idx = 0
                frame_buffer = []
                lh_trail.clear()
                rh_trail.clear()
                print("[!] Video restarted from frame 0.")
            elif key == ord('s'):
                if current_sentence and current_sentence != last_spoken:
                    speak_async(current_sentence)
                    last_spoken = current_sentence
                    print(f"[TTS] Speaking: \"{current_sentence}\"")
        else:
            if frame_idx % 60 == 0:
                elapsed = time.time() - start_time
                pct = (frame_idx / total_frames) * 100 if total_frames else 0
                print(f"[+] Progress: {frame_idx}/{total_frames} ({pct:.1f}%) | Rt: {avg_rel:.2f} | Speed: {frame_idx/elapsed:.1f} fps")

    cap.release()
    out_writer.release()
    if show_display:
        cv2.destroyAllWindows()
    landmarker.close()
    speech_queue.put(None)

    total_time = time.time() - start_time
    print("=" * 70)
    print(f"[+] Output Video Successfully Generated: {output_path}")
    print(f"[+] Processed {frame_idx} frames in {total_time:.1f} seconds ({frame_idx/max(1, total_time):.1f} fps).")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RACER-X MediaPipe Live Video Translator")
    parser.add_argument("--video", nargs="*", default=[], help="Path to input sign language MP4 video file")
    parser.add_argument("--output", default="", help="Path for rendered output video file (e.g. output_123456.mp4)")
    parser.add_argument("--no-display", action="store_true", help="Run without opening GUI window (faster rendering)")
    args = parser.parse_args()

    v_path = " ".join(args.video).strip().strip('"').strip("'")
    if not v_path:
        # Check if 123456.mp4 is in the current directory as standard project video
        if os.path.exists("123456.mp4"):
            v_path = "123456.mp4"
            print(f"[+] Defaulting to project video: {v_path}")
        else:
            print("\n" + "=" * 60)
            print("Please enter the path or filename of your video file:")
            print("Example: 123456.mp4 or C:\\path\\to\\video.mp4")
            print("=" * 60)
            v_path = input("Video File Path: ").strip().strip('"').strip("'")

    out_p = args.output.strip().strip('"').strip("'")
    if not out_p:
        out_p = None

    process_video(v_path, output_path=out_p, show_display=not args.no_display)
