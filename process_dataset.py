import os
import glob
import cv2
import webvtt
import numpy as np
import pandas as pd
import mediapipe as mp

RAW_DIR = os.path.join("dataset", "raw_videos")
OUTPUT_DIR = os.path.join("dataset", "ish_dataset")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "clips")
os.makedirs(CLIPS_DIR, exist_ok=True)

# Selected Landmarks: Total 75 keypoints * 4 values = 300 floats per frame
# 1. Pose: Upper body (9 keypoints)
POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0]
# 2. Face: Eyebrows, Eyes, Lips, Nose, Chin (22 keypoints)
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152]

mp_holistic = mp.solutions.holistic

def extract_landmarks(results):
    """
    Extracts 75 keypoints (Hands, Upper Pose, Face) with [x, y, z, visibility/confidence].
    Output vector: 75 * 4 = 300 floats per frame.
    """
    # Pose landmarks
    if results.pose_landmarks:
        pose = [[results.pose_landmarks.landmark[i].x, results.pose_landmarks.landmark[i].y,
                 results.pose_landmarks.landmark[i].z, results.pose_landmarks.landmark[i].visibility]
                for i in POSE_INDICES]
    else:
        pose = [[0.0] * 4] * len(POSE_INDICES)

    # Face landmarks
    if results.face_landmarks:
        face = [[results.face_landmarks.landmark[i].x, results.face_landmarks.landmark[i].y,
                 results.face_landmarks.landmark[i].z, 1.0]
                for i in FACE_INDICES]
    else:
        face = [[0.0] * 4] * len(FACE_INDICES)

    # Left Hand (21 keypoints)
    if results.left_hand_landmarks:
        lh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.left_hand_landmarks.landmark]
    else:
        lh = [[0.0] * 4] * 21

    # Right Hand (21 keypoints)
    if results.right_hand_landmarks:
        rh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.right_hand_landmarks.landmark]
    else:
        rh = [[0.0] * 4] * 21

    return np.concatenate([pose, face, lh, rh]).flatten()

def time_to_sec(t_str):
    """Converts HH:MM:SS.mmm or MM:SS.mmm string to seconds."""
    parts = t_str.strip().split(':')
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])

def clean_caption_text(text):
    """Removes HTML tags and cleans subtitle artifacts."""
    text = text.replace('\n', ' ').strip()
    # Basic cleaning of tags if any
    while '<' in text and '>' in text:
        start = text.find('<')
        end = text.find('>')
        if start < end:
            text = text[:start] + text[end+1:]
        else:
            break
    return ' '.join(text.split())

def process_all_videos():
    video_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.mp4")))
    if not video_files:
        print(f"[!] No mp4 files found in {RAW_DIR}. Run download_batch.py first!")
        return

    metadata = []
    global_clip_count = 0

    print("==================================================")
    print(f"Starting MediaPipe extraction on {len(video_files)} videos...")
    print(f"Output directory: {CLIPS_DIR}")
    print("==================================================")

    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        for vid_path in video_files:
            base_name = os.path.splitext(os.path.basename(vid_path))[0]
            vtt_matches = glob.glob(os.path.join(RAW_DIR, f"{base_name}*.vtt"))
            
            if not vtt_matches:
                print(f"[!] Skipping {base_name}: No corresponding .vtt subtitle file found.")
                continue
            
            vtt_path = vtt_matches[0]
            print(f"\n[+] Processing: {base_name} ...")

            cap = cv2.VideoCapture(vid_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            try:
                subs = webvtt.read(vtt_path)
            except Exception as e:
                print(f"[!] Failed to parse {vtt_path}: {e}")
                cap.release()
                continue

            for sub in subs:
                text = clean_caption_text(sub.text)
                if not text or len(text) < 4:
                    continue

                try:
                    start_sec = time_to_sec(sub.start)
                    end_sec = time_to_sec(sub.end)
                except Exception:
                    continue

                duration = end_sec - start_sec

                # Keep meaningful continuous sign sentences (between 1.5 and 10 seconds)
                if duration < 1.2 or duration > 10.0:
                    continue

                start_frame = max(0, int(start_sec * fps))
                end_frame = min(total_frames, int(end_sec * fps))

                if end_frame <= start_frame:
                    continue

                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                clip_landmarks = []

                for _ in range(start_frame, end_frame):
                    ret, frame = cap.read()
                    if not ret:
                        break

                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = holistic.process(img_rgb)
                    clip_landmarks.append(extract_landmarks(results))

                # Quality check: Require at least 20 frames per clip
                if len(clip_landmarks) >= 20:
                    clip_filename = f"clip_{global_clip_count:05d}.npy"
                    save_path = os.path.join(CLIPS_DIR, clip_filename)
                    np.save(save_path, np.array(clip_landmarks, dtype=np.float32))

                    metadata.append({
                        "clip_id": global_clip_count,
                        "clip_file": clip_filename,
                        "video_source": base_name,
                        "start_time": sub.start,
                        "end_time": sub.end,
                        "duration_sec": round(duration, 2),
                        "num_frames": len(clip_landmarks),
                        "sentence": text
                    })
                    print(f"    -> Extracted {clip_filename}: \"{text[:45]}...\" ({len(clip_landmarks)} frames)")
                    global_clip_count += 1

            cap.release()

    # Save master metadata CSV
    df = pd.DataFrame(metadata)
    csv_path = os.path.join(OUTPUT_DIR, "metadata.csv")
    df.to_csv(csv_path, index=False)
    
    print("\n==================================================")
    print(f"SUCCESS! Total clips generated: {len(df)}")
    print(f"Clips location: {CLIPS_DIR}")
    print(f"Master metadata: {csv_path}")
    print("==================================================")

if __name__ == "__main__":
    process_all_videos()
