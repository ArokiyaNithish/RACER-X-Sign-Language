import os
import sys
import time
import json
import base64
import numpy as np
import cv2
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from racer_model import RacerXNetwork

# -------------------------------------------------------------
# Configuration & Paths (Directly from RACER-X Project)
# -------------------------------------------------------------
CHECKPOINT_PATH = os.path.join("checkpoints", "best_racer_x.pth")
VOCAB_PATH = os.path.join("checkpoints", "vocab.json")
CLEAN_CSV = os.path.join("dataset", "master_dataset_clean.csv")
MODEL_DIR = "models"
HOLISTIC_TASK_PATH = os.path.join(MODEL_DIR, "holistic_landmarker.task")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
WINDOW_SIZE = 40  # Sliding sequence window ~ 1.3 seconds
MIN_FRAMES = 15

# 75 selected landmark indices (9 pose, 22 face, 21 left hand, 21 right hand)
POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0]
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152]

app = FastAPI(title="RACER-X Sign Language Recognition Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Model & Vocabulary Initialization
# -------------------------------------------------------------
vocab = {}
inv_vocab = {}
prior_penalty = None
model = None
landmarker = None

def ensure_task_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.exists(HOLISTIC_TASK_PATH):
        print("[+] Downloading MediaPipe Holistic task bundle (~13.6 MB)...")
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task"
        urllib.request.urlretrieve(url, HOLISTIC_TASK_PATH)
        print("[+] Download complete!")

def init_system():
    global model, vocab, inv_vocab, prior_penalty, landmarker

    # 1. Holistic Landmarker
    ensure_task_model()
    base_options = python.BaseOptions(model_asset_path=HOLISTIC_TASK_PATH)
    options = vision.HolisticLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_segmentation_mask=False
    )
    landmarker = vision.HolisticLandmarker.create_from_options(options)
    print("[+] MediaPipe Holistic Landmarker loaded.")

    # 2. Vocabulary & Class Prior Penalty
    if os.path.exists(VOCAB_PATH):
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            vocab = json.load(f)
        inv_vocab = {v: k for k, v in vocab.items()}
        print(f"[+] Loaded RACER-X Vocabulary: {len(vocab)} unique classes.")

    vocab_size = len(vocab) if vocab else 2748
    prior_penalty = torch.zeros(vocab_size)
    if os.path.exists(CLEAN_CSV):
        try:
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
            print("[+] Computed Bayesian prior frequency discount.")
        except Exception as e:
            print(f"[!] Warning computing prior: {e}")

    # 3. RACER-X Network & Weights
    model = RacerXNetwork(vocab_size=vocab_size).to(DEVICE)
    if os.path.exists(CHECKPOINT_PATH):
        try:
            checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            model.load_state_dict(state_dict)
            print(f"[+] Successfully loaded RACER-X model checkpoint from {CHECKPOINT_PATH}")
        except Exception as e:
            print(f"[!] Error loading checkpoint: {e}")
    else:
        print(f"[!] Warning: Checkpoint not found at {CHECKPOINT_PATH}")

    model.eval()
    print(f"[+] Model active on compute device: {DEVICE}")

# -------------------------------------------------------------
# Landmark Feature Extraction & Kinematics
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

def compute_kinematics(seq):
    T = seq.shape[0]
    reshaped = seq.reshape(T, 75, 4)
    P = reshaped[:, :, :3]
    C = reshaped[:, :, 3]

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
    kappa = np.clip(norm_cross_va / (np.power(norm_v, 3) + 1e-4), 0.0, 10.0)

    dot_vaj = np.sum(cross_va * J, axis=-1)
    tau = np.clip(dot_vaj / (np.power(norm_cross_va, 2) + 1e-4), -10.0, 10.0)

    jerk_magnitude = np.linalg.norm(J, axis=-1).mean(axis=-1, keepdims=True)
    mean_conf = C.mean(axis=-1, keepdims=True)
    R = mean_conf * np.exp(-0.5 * jerk_magnitude)

    P_flat = np.nan_to_num(P_norm.reshape(T, -1), nan=0.0)
    V_flat = np.nan_to_num(V.reshape(T, -1), nan=0.0)
    A_flat = np.nan_to_num(A.reshape(T, -1), nan=0.0)
    J_flat = np.nan_to_num(J.reshape(T, -1), nan=0.0)
    kappa_flat = np.nan_to_num(kappa.reshape(T, -1), nan=0.0)
    tau_flat = np.nan_to_num(tau.reshape(T, -1), nan=0.0)

    M_flat = np.concatenate([V_flat, A_flat, J_flat, kappa_flat, tau_flat], axis=-1)
    R = np.nan_to_num(R, nan=0.0)

    return P_flat, M_flat, R

def ctc_greedy_decode(log_probs, inv_vocab, prior_penalty=None):
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
# REST Endpoints
# -------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "service": "RACER-X Sign Language Recognition API",
        "status": "online",
        "device": str(DEVICE),
        "vocab_size": len(vocab)
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time()}

# -------------------------------------------------------------
# WebSocket Handler for Chrome Extension
# -------------------------------------------------------------
@app.websocket("/ws/sign-recognition")
async def websocket_sign_endpoint(websocket: WebSocket, token: str = Query(None)):
    await websocket.accept()
    print(f"[+] Chrome Extension connected to /ws/sign-recognition (token={token})")

    frame_buffer = []
    last_emit_time = 0
    last_prediction = ""
    silence_counter = 0

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except Exception:
                continue

            msg_type = data.get("type", "frame")
            if msg_type == "frame":
                b64_data = data.get("data")
                if not b64_data:
                    continue

                try:
                    img_bytes = base64.b64decode(b64_data)
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                except Exception:
                    continue

                if frame is None:
                    continue

                # Run Holistic landmark detection
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                
                try:
                    res = landmarker.detect(mp_img)
                    lm_vec = extract_landmarks(res)
                    frame_buffer.append(lm_vec)
                except Exception:
                    continue

                if len(frame_buffer) > WINDOW_SIZE:
                    frame_buffer.pop(0)

                # Check if hands are actively signing
                has_left = bool(res.left_hand_landmarks and len(res.left_hand_landmarks) == 21)
                has_right = bool(res.right_hand_landmarks and len(res.right_hand_landmarks) == 21)
                has_hands = has_left or has_right

                # Extract normalized coordinates for Google Meet Live MediaPipe Overlay
                pose_pts = []
                if res.pose_landmarks and len(res.pose_landmarks) > 24:
                    for idx in [11, 12, 13, 14, 15, 16, 23, 24]:
                        lm = res.pose_landmarks[idx]
                        pose_pts.append([round(float(lm.x), 4), round(float(lm.y), 4)])

                lh_pts = []
                if has_left:
                    lh_pts = [[round(float(lm.x), 4), round(float(lm.y), 4)] for lm in res.left_hand_landmarks]

                rh_pts = []
                if has_right:
                    rh_pts = [[round(float(lm.x), 4), round(float(lm.y), 4)] for lm in res.right_hand_landmarks]

                face_pts = []
                if res.face_landmarks and len(res.face_landmarks) > 300:
                    for idx in [33, 133, 362, 263, 70, 105, 300, 334, 0, 13, 14, 17, 61, 291]:
                        lm = res.face_landmarks[idx]
                        face_pts.append([round(float(lm.x), 4), round(float(lm.y), 4)])

                now = time.time()

                # Stream live MediaPipe landmark geometry for Google Meet overlay
                try:
                    await websocket.send_text(json.dumps({
                        "type": "landmarks",
                        "pose": pose_pts,
                        "left_hand": lh_pts,
                        "right_hand": rh_pts,
                        "face": face_pts,
                        "has_hands": has_hands,
                        "has_left": has_left,
                        "has_right": has_right,
                        "timestamp": int(now * 1000)
                    }))
                except Exception:
                    pass

                if has_hands:
                    silence_counter = 0
                else:
                    silence_counter += 1

                # Run RACER-X inference when signing is active
                if len(frame_buffer) >= MIN_FRAMES and has_hands and (now - last_emit_time) > 0.35:
                    seq_arr = np.array(frame_buffer)
                    P_f, M_f, R_f = compute_kinematics(seq_arr)

                    p_tensor = torch.tensor(P_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
                    m_tensor = torch.tensor(M_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)
                    r_tensor = torch.tensor(R_f, dtype=torch.float32, device=DEVICE).unsqueeze(0)

                    with torch.no_grad():
                        log_probs = model(p_tensor, m_tensor, r_tensor)
                        decoded_text = ctc_greedy_decode(log_probs, inv_vocab, prior_penalty=prior_penalty)

                    if decoded_text and decoded_text.strip():
                        last_emit_time = now
                        last_prediction = decoded_text
                        await websocket.send_text(json.dumps({
                            "type": "recognition",
                            "text": decoded_text.title(),
                            "raw_sign": decoded_text,
                            "confidence": float(np.mean(R_f)),
                            "timestamp": int(now * 1000)
                        }))

                # When hands rest, emit complete phrase for spoken TTS
                if silence_counter == 15 and last_prediction:
                    await websocket.send_text(json.dumps({
                        "type": "phrase_ready",
                        "text": last_prediction.title(),
                        "timestamp": int(now * 1000)
                    }))
                    last_prediction = ""

    except WebSocketDisconnect:
        print("[-] Chrome Extension disconnected from /ws/sign-recognition")
    except Exception as e:
        print(f"[!] WebSocket loop error: {e}")

# -------------------------------------------------------------
# Main Startup
# -------------------------------------------------------------
if __name__ == "__main__":
    init_system()
    print("\n" + "=" * 65)
    print("  RACER-X Sign Language Project -> Chrome Extension Bridge")
    print("  Listening on: http://localhost:8000 and ws://localhost:8000")
    print("=" * 65 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
