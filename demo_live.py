import os
import sys
import time
import json
import queue
import threading
import urllib.request
import numpy as np
import cv2
import torch
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from racer_model import RacerXNetwork

# -------------------------------------------------------------
# Configuration & Paths
# -------------------------------------------------------------
CHECKPOINT_PATH = os.path.join("checkpoints", "best_racer_x.pth")
VOCAB_PATH = os.path.join("checkpoints", "vocab.json")
MODEL_DIR = "models"
HOLISTIC_TASK_PATH = os.path.join(MODEL_DIR, "holistic_landmarker.task")
WINDOW_NAME = "RACER-X: Real-Time Continuous Sign-to-Speech System"

# Selected Landmark Indices (75 landmarks * 4 values = 300 values)
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
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24)
]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------------------------------------
# Ensure Model Asset Exists
# -------------------------------------------------------------
def ensure_task_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.exists(HOLISTIC_TASK_PATH):
        print("[+] Downloading MediaPipe Holistic task bundle (~13.6 MB)...")
        url = "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task"
        urllib.request.urlretrieve(url, HOLISTIC_TASK_PATH)
        print("[+] Download complete!")

# -------------------------------------------------------------
# Asynchronous Text-to-Speech Worker (Non-blocking)
# -------------------------------------------------------------
speech_queue = queue.Queue()

def tts_worker():
    """Background worker for speaking recognized sentences without stalling video FPS."""
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
# Landmark Extraction & Normalization
# -------------------------------------------------------------
def extract_landmarks_from_tasks(res):
    """
    Extracts 75 keypoints (Hands, Upper Pose, Face) with [x, y, z, visibility/confidence].
    Output vector: 75 * 4 = 300 floats per frame.
    """
    # 1. Pose landmarks (9 keypoints)
    if res.pose_landmarks and len(res.pose_landmarks) > max(POSE_INDICES):
        pose = [[res.pose_landmarks[i].x, res.pose_landmarks[i].y, res.pose_landmarks[i].z,
                 getattr(res.pose_landmarks[i], 'visibility', 1.0)]
                for i in POSE_INDICES]
    else:
        pose = [[0.0] * 4] * len(POSE_INDICES)

    # 2. Face landmarks (22 keypoints)
    if res.face_landmarks and len(res.face_landmarks) > max(FACE_INDICES):
        face = [[res.face_landmarks[i].x, res.face_landmarks[i].y, res.face_landmarks[i].z, 1.0]
                for i in FACE_INDICES]
    else:
        face = [[0.0] * 4] * len(FACE_INDICES)

    # 3. Left Hand (21 keypoints)
    if res.left_hand_landmarks and len(res.left_hand_landmarks) == 21:
        lh = [[lm.x, lm.y, lm.z, 1.0] for lm in res.left_hand_landmarks]
    else:
        lh = [[0.0] * 4] * 21

    # 4. Right Hand (21 keypoints)
    if res.right_hand_landmarks and len(res.right_hand_landmarks) == 21:
        rh = [[lm.x, lm.y, lm.z, 1.0] for lm in res.right_hand_landmarks]
    else:
        rh = [[0.0] * 4] * 21

    # Total 73 keypoints -> 292 floats; pad to 75 keypoints (300 floats)
    raw = np.concatenate([pose, face, lh, rh]).flatten()
    if len(raw) < 300:
        raw = np.pad(raw, (0, 300 - len(raw)), mode='constant')
    return raw[:300].astype(np.float32)

def draw_custom_skeleton(frame, res):
    """Draws glowing joints and connections on the OpenCV frame."""
    h, w, _ = frame.shape

    # Draw Pose / Arms
    if res.pose_landmarks and len(res.pose_landmarks) > 24:
        for idx1, idx2 in POSE_CONNECTIONS:
            p1 = res.pose_landmarks[idx1]
            p2 = res.pose_landmarks[idx2]
            pt1 = (int(p1.x * w), int(p1.y * h))
            pt2 = (int(p2.x * w), int(p2.y * h))
            cv2.line(frame, pt1, pt2, (80, 200, 255), 2)
            cv2.circle(frame, pt1, 4, (0, 255, 255), -1)
            cv2.circle(frame, pt2, 4, (0, 255, 255), -1)

    # Draw Left Hand (Purple/Pink)
    if res.left_hand_landmarks and len(res.left_hand_landmarks) == 21:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in res.left_hand_landmarks]
        for idx1, idx2 in HAND_CONNECTIONS:
            cv2.line(frame, pts[idx1], pts[idx2], (255, 100, 200), 2)
        for pt in pts:
            cv2.circle(frame, pt, 4, (255, 0, 255), -1)

    # Draw Right Hand (Cyan/Green)
    if res.right_hand_landmarks and len(res.right_hand_landmarks) == 21:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in res.right_hand_landmarks]
        for idx1, idx2 in HAND_CONNECTIONS:
            cv2.line(frame, pts[idx1], pts[idx2], (0, 255, 180), 2)
        for pt in pts:
            cv2.circle(frame, pt, 4, (0, 255, 0), -1)

def compute_kinematics(seq):
    """
    Computes Position (P), Velocity (V), Acceleration (A), Jerk (J),
    Frenet-Serret Curvature (kappa), Torsion (tau), and Reliability (R_t).
    Matches KinematicSignDataset exactly.
    """
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

    # Frenet-Serret Curvature & Torsion
    cross_va = np.cross(V, A)
    norm_cross_va = np.linalg.norm(cross_va, axis=-1)
    norm_v = np.linalg.norm(V, axis=-1)
    kappa = norm_cross_va / (np.power(norm_v, 3) + 1e-4)
    kappa = np.clip(kappa, 0.0, 10.0)

    dot_vaj = np.sum(cross_va * J, axis=-1)
    tau = dot_vaj / (np.power(norm_cross_va, 2) + 1e-4)
    tau = np.clip(tau, -10.0, 10.0)

    # Reliability R_t
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

def ctc_greedy_decode(log_probs, inv_vocab, prior_penalty=None):
    """Greedy CTC sequence decoding with Bayesian frequency balancing."""
    lp = log_probs.squeeze(0)
    if prior_penalty is not None:
        lp = lp - (0.35 * prior_penalty.to(lp.device).unsqueeze(0))
    pred_indices = torch.argmax(lp, dim=-1).cpu().numpy()
    collapsed = []
    prev = None
    for idx in pred_indices:
        if idx != prev:
            if idx > 1:
                collapsed.append(idx)
            prev = idx
    words = [inv_vocab.get(i, "") for i in collapsed if i in inv_vocab]
    return " ".join([w for w in words if w])

# -------------------------------------------------------------
# Main Live Demo Function
# -------------------------------------------------------------
def run_live_demo():
    print("=" * 65)
    print("RACER-X: Continuous Indian Sign-to-Speech System")
    print("Department of AI & DS, Vel Tech R&D Institute, Chennai, India")
    print("=" * 65)

    # 1. Ensure Model Asset Exists
    ensure_task_model()

    # 2. Load Vocabulary
    if not os.path.exists(VOCAB_PATH):
        print(f"[-] Error: Vocabulary file not found at {VOCAB_PATH}")
        return
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    inv_vocab = {v: k for k, v in vocab.items()}
    vocab_size = len(vocab)
    print(f"[+] Loaded Vocabulary: {vocab_size} unique Indian Sign Language tokens.")

    # Compute class prior frequency discount
    prior_penalty = torch.zeros(vocab_size)
    if os.path.exists(CLEAN_CSV):
        import pandas as pd
        df_meta = pd.read_csv(CLEAN_CSV)
        counts = torch.ones(vocab_size)
        for s in df_meta['sentence']:
            for w in str(s).upper().split():
                if w in vocab:
                    counts[vocab[w]] += 1.0
        prior_penalty = torch.log(counts)
        prior_penalty[0] = 0.0
        prior_penalty[1] = 0.0

    # 3. Load Model Checkpoint
    if not os.path.exists(CHECKPOINT_PATH):
        print(f"[-] Error: Checkpoint file not found at {CHECKPOINT_PATH}")
        return
    model = RacerXNetwork(vocab_size=vocab_size).to(DEVICE)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    print(f"[+] Loaded Model Weights from: {CHECKPOINT_PATH}")
    print(f"[+] Using Compute Device: {DEVICE}")

    # 4. Initialize MediaPipe Holistic Landmarker (Tasks API)
    print("[+] Initializing MediaPipe Tasks Holistic Landmarker...")
    base_options = python.BaseOptions(model_asset_path=HOLISTIC_TASK_PATH)
    options = vision.HolisticLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_segmentation_mask=False
    )
    landmarker = vision.HolisticLandmarker.create_from_options(options)

    # 5. Initialize Camera
    print("[+] Initializing camera feed...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[-] Warning: Camera 0 not available. Trying camera index 1...")
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] Error: No camera detected. Please connect a webcam.")
        landmarker.close()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Sliding Buffer for Sequence Recognition (40 frames ~ 1.2s)
    BUFFER_SIZE = 40
    frame_buffer = []

    last_prediction = ""
    current_sentence = ""
    prev_spoken_sentence = ""
    auto_speak = True
    active_motion = False
    avg_rel = 1.0

    fps_timer = time.time()
    frame_count = 0
    current_fps = 30.0
    silence_frames = 0

    print("\n" + "=" * 65)
    print("CONTROLS:")
    print("  [q / ESC] : Quit Application")
    print("  [c]       : Clear Subtitle")
    print("  [s]       : Speak Sentence Out Loud Now")
    print("  [m]       : Toggle Auto-Speech (Currently ON)")
    print("=" * 65 + "\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("[-] Failed to read frame from camera.")
            break

        # Mirror view for intuitive user experience
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Convert to MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect landmarks
        results = landmarker.detect(mp_image)

        # Draw glowing joints and skeleton on screen
        draw_custom_skeleton(frame, results)

        # Extract 75 landmarks
        lm_vec = extract_landmarks_from_tasks(results)
        frame_buffer.append(lm_vec)
        if len(frame_buffer) > BUFFER_SIZE:
            frame_buffer.pop(0)

        # Determine whether hands are actively signing
        has_hands = bool((results.left_hand_landmarks and len(results.left_hand_landmarks) > 0) or
                         (results.right_hand_landmarks and len(results.right_hand_landmarks) > 0))

        if has_hands:
            active_motion = True
            silence_frames = 0
        else:
            silence_frames += 1
            if silence_frames > 20:
                active_motion = False

        # Neural Inference every 3 frames when signing
        if len(frame_buffer) >= 20 and active_motion and (frame_count % 3 == 0):
            seq_arr = np.array(frame_buffer)
            P_f, M_f, R_f = compute_kinematics(seq_arr)
            avg_rel = float(np.mean(R_f))

            p_tensor = torch.tensor(P_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
            m_tensor = torch.tensor(M_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
            r_tensor = torch.tensor(R_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)

            with torch.no_grad():
                log_probs = model(p_tensor, m_tensor, r_tensor)
                decoded_text = ctc_greedy_decode(log_probs, inv_vocab, prior_penalty=prior_penalty)

            if decoded_text and decoded_text != last_prediction:
                last_prediction = decoded_text
                current_sentence = decoded_text

        # Auto-speak when sign sentence completes (hands rest)
        if silence_frames == 18 and current_sentence and current_sentence != prev_spoken_sentence:
            if auto_speak:
                speak_async(current_sentence)
            prev_spoken_sentence = current_sentence

        # FPS counter
        frame_count += 1
        if frame_count % 10 == 0:
            elapsed = time.time() - fps_timer
            if elapsed > 0:
                current_fps = 10.0 / elapsed
            fps_timer = time.time()

        # ---------------------------------------------------------
        # UI Overlay & Subtitles
        # ---------------------------------------------------------
        # Top HUD Banner
        cv2.rectangle(frame, (0, 0), (w, 80), (20, 20, 20), -1)
        cv2.putText(frame, "RACER-X: Indian Sign-to-Speech Communication System", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS: {current_fps:.1f}  |  Reliability R_t: {avg_rel:.2f}  |  Audio: {'ON' if auto_speak else 'MUTED'}",
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 2)

        status_text = "SIGNING DETECTED" if active_motion else "STANDBY / NEUTRAL"
        status_color = (0, 255, 0) if active_motion else (150, 150, 150)
        cv2.putText(frame, status_text, (w - 280, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

        # Bottom Subtitle Banner
        sub_h = 100
        cv2.rectangle(frame, (0, h - sub_h), (w, h), (15, 15, 15), -1)
        cv2.line(frame, (0, h - sub_h), (w, h - sub_h), (0, 255, 180), 2)

        cv2.putText(frame, "RECOGNIZED SIGN TRANSLATION:", (20, h - 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        display_sub = current_sentence if current_sentence else "Waiting for signing..."
        sub_col = (0, 255, 120) if current_sentence else (100, 100, 100)
        cv2.putText(frame, display_sub[:75], (20, h - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, sub_col, 2)

        # Render Window
        cv2.imshow(WINDOW_NAME, frame)

        # Keyboard Interactions
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("[+] Exiting live demo...")
            break
        elif key == ord('c'):
            current_sentence = ""
            last_prediction = ""
        elif key == ord('s'):
            if current_sentence:
                speak_async(current_sentence)
        elif key == ord('m'):
            auto_speak = not auto_speak
            print(f"[+] Auto-speech: {'ENABLED' if auto_speak else 'MUTED'}")

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    speech_queue.put(None)

if __name__ == "__main__":
    run_live_demo()
