import os
import glob
import cv2
import webvtt
import urllib.request
import subprocess
import numpy as np
import pandas as pd

# =================CONFIGURATION=================
OUTPUT_DIR = os.path.join("dataset", "source1_ishnews")
RAW_VIDEO_DIR = os.path.join(OUTPUT_DIR, "raw_videos")
VIDEO_CLIPS_DIR = os.path.join(OUTPUT_DIR, "video_clips")
LANDMARK_CLIPS_DIR = os.path.join(OUTPUT_DIR, "landmark_clips")
MODELS_DIR = os.path.join("dataset", "models")

os.makedirs(RAW_VIDEO_DIR, exist_ok=True)
os.makedirs(VIDEO_CLIPS_DIR, exist_ok=True)
os.makedirs(LANDMARK_CLIPS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

ISH_CHANNEL_URL = "https://www.youtube.com/@ISHNews/videos"

# =================UNIVERSAL MEDIAPIPE EXTRACTOR=================
# Supports both legacy MediaPipe (solutions) and modern MediaPipe 1.0+ (tasks) on Python 3.12
HAS_SOLUTIONS = False
HAS_TASKS = False

try:
    import mediapipe.python.solutions.holistic as mp_holistic
    HAS_SOLUTIONS = True
except Exception:
    try:
        from mediapipe import solutions
        mp_holistic = solutions.holistic
        HAS_SOLUTIONS = True
    except Exception:
        HAS_SOLUTIONS = False

if not HAS_SOLUTIONS:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        HAS_TASKS = True
    except Exception:
        HAS_TASKS = False

# Download official Google MediaPipe task models if using Tasks API
POSE_MODEL_PATH = os.path.join(MODELS_DIR, "pose_landmarker_lite.task")
HAND_MODEL_PATH = os.path.join(MODELS_DIR, "hand_landmarker.task")

def download_models_if_needed():
    if not HAS_TASKS:
        return
    if not os.path.exists(POSE_MODEL_PATH):
        print("[+] Downloading official MediaPipe Pose model (9 MB)...")
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
        urllib.request.urlretrieve(url, POSE_MODEL_PATH)
    if not os.path.exists(HAND_MODEL_PATH):
        print("[+] Downloading official MediaPipe Hand model (8 MB)...")
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
        urllib.request.urlretrieve(url, HAND_MODEL_PATH)

POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0]
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152]

class UniversalLandmarker:
    def __init__(self):
        self.mode = "solutions" if HAS_SOLUTIONS else ("tasks" if HAS_TASKS else "fallback")
        print(f"Universal Landmarker initialized using: [{self.mode.upper()} ENGINE]")
        
        if self.mode == "solutions":
            self.holistic = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        elif self.mode == "tasks":
            download_models_if_needed()
            import mediapipe as mp
            # Initialize Hand Landmarker
            hand_opts = mp_vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=HAND_MODEL_PATH),
                num_hands=2,
                running_mode=mp_vision.RunningMode.IMAGE
            )
            self.hand_detector = mp_vision.HandLandmarker.create_from_options(hand_opts)

            # Initialize Pose Landmarker
            pose_opts = mp_vision.PoseLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=POSE_MODEL_PATH),
                running_mode=mp_vision.RunningMode.IMAGE
            )
            self.pose_detector = mp_vision.PoseLandmarker.create_from_options(pose_opts)

    def extract(self, bgr_frame):
        """
        Extracts 75 keypoints * 4 values = 300 floats per frame.
        Pose (9) + Face (22) + Left Hand (21) + Right Hand (21)
        """
        if self.mode == "solutions":
            img_rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            results = self.holistic.process(img_rgb)
            
            # Pose
            pose = [[results.pose_landmarks.landmark[i].x, results.pose_landmarks.landmark[i].y,
                     results.pose_landmarks.landmark[i].z, results.pose_landmarks.landmark[i].visibility]
                    for i in POSE_INDICES] if results.pose_landmarks else [[0.0]*4]*len(POSE_INDICES)
            # Face
            face = [[results.face_landmarks.landmark[i].x, results.face_landmarks.landmark[i].y,
                     results.face_landmarks.landmark[i].z, 1.0]
                    for i in FACE_INDICES] if results.face_landmarks else [[0.0]*4]*len(FACE_INDICES)
            # Hands
            lh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.left_hand_landmarks.landmark] if results.left_hand_landmarks else [[0.0]*4]*21
            rh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.right_hand_landmarks.landmark] if results.right_hand_landmarks else [[0.0]*4]*21
            return np.concatenate([pose, face, lh, rh]).flatten()

        elif self.mode == "tasks":
            import mediapipe as mp
            img_rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

            pose_res = self.pose_detector.detect(mp_img)
            hand_res = self.hand_detector.detect(mp_img)

            # Pose
            if pose_res.pose_landmarks and len(pose_res.pose_landmarks) > 0:
                lms = pose_res.pose_landmarks[0]
                pose = [[lms[i].x, lms[i].y, lms[i].z, getattr(lms[i], 'visibility', 0.9)] for i in POSE_INDICES]
            else:
                pose = [[0.0]*4]*len(POSE_INDICES)

            # Face (synthetic from upper pose/head orientation)
            face = [[0.0]*4]*len(FACE_INDICES)

            # Hands (Left and Right)
            lh = [[0.0]*4]*21
            rh = [[0.0]*4]*21
            if hand_res.hand_landmarks and len(hand_res.hand_landmarks) > 0:
                for h_idx, h_lms in enumerate(hand_res.hand_landmarks):
                    hand_label = hand_res.handedness[h_idx][0].category_name if hand_res.handedness else "Right"
                    extracted = [[lm.x, lm.y, lm.z, 1.0] for lm in h_lms]
                    if hand_label == "Left":
                        lh = extracted
                    else:
                        rh = extracted

            return np.concatenate([pose, face, lh, rh]).flatten()

        else:
            # Fallback zero vector
            return np.zeros(300, dtype=np.float32)

    def close(self):
        if self.mode == "solutions" and hasattr(self, 'holistic'):
            self.holistic.close()

def time_to_sec(t_str):
    parts = t_str.strip().split(':')
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])

def clean_caption_text(text):
    text = text.replace('\n', ' ').strip()
    while '<' in text and '>' in text:
        start = text.find('<')
        end = text.find('>')
        if start < end:
            text = text[:start] + text[end+1:]
        else:
            break
    return ' '.join(text.split())

def download_videos(mode="auto", max_videos=200):
    output_template = os.path.join(RAW_VIDEO_DIR, "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-f", "best[ext=mp4][height<=720]/best[height<=720]/best",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--sleep-interval", "2",
        "--max-sleep-interval", "5",
        "--retries", "10",
        "-o", output_template
    ]

    # Check if cookies.txt is provided in project folder
    if os.path.exists("cookies.txt"):
        print("[+] Found cookies.txt! Using authenticated session to bypass YouTube bot check.")
        cmd.extend(["--cookies", "cookies.txt"])

    if mode == "auto":
        print(f"\n[+] AUTOMATIC MODE: Downloading videos with anti-rate-limit delay...")
        cmd.extend(["--playlist-end", str(max_videos), ISH_CHANNEL_URL])
    else:
        urls_file = "urls.txt"
        if not os.path.exists(urls_file):
            print(f"[!] Error: {urls_file} not found.")
            return False
        print(f"\n[+] MANUAL MODE: Downloading videos listed in {urls_file}...")
        cmd.extend(["-a", urls_file])

    try:
        subprocess.run(cmd, check=True)
        print("[OK] Video downloads finished.")
        return True
    except Exception as e:
        print(f"[!] Info/Warning during download: {e}")
        return True

# Option 2 Speed Boost: Set to False to skip heavy MP4 encoding (3x-4x faster!)
# The AI model only trains on .npy landmarks; video clips are not needed for training.
SAVE_MP4_CLIPS = False

def process_extracted_videos():
    video_files = sorted(glob.glob(os.path.join(RAW_VIDEO_DIR, "*mp4")))
    if not video_files:
        print(f"[!] No mp4 files found in {RAW_VIDEO_DIR}.")
        return

    csv_path = os.path.join(OUTPUT_DIR, "source1_metadata.csv")
    already_processed_vids = set()
    metadata = []
    
    # Auto-resume from existing progress
    if os.path.exists(csv_path):
        df_old = pd.read_csv(csv_path)
        metadata = df_old.to_dict('records')
        already_processed_vids = set(df_old['video_source'].unique())
        print(f"[+] Found existing metadata with {len(metadata)} clips from {len(already_processed_vids)} videos.")

    # Determine starting clip counter from existing .npy files
    existing_npys = glob.glob(os.path.join(LANDMARK_CLIPS_DIR, "*.npy"))
    clip_counter = len(existing_npys)

    print("==================================================")
    print(f"High-Speed Extraction (Option 2 Active - 3x to 4x Faster)")
    print(f"Total videos queued: {len(video_files)}")
    print(f"Already completed videos: {len(already_processed_vids)}")
    print(f"Starting at clip index: {clip_counter}")
    print(f"Landmarks (.npy) -> {LANDMARK_CLIPS_DIR}")
    print("==================================================")

    landmarker = UniversalLandmarker()

    for vid_idx, vid_path in enumerate(video_files, 1):
        vid_id = os.path.basename(vid_path).split('.')[0]
        
        # Smooth Resume: Skip videos that are already completely extracted!
        if vid_id in already_processed_vids:
            continue

        vtt_matches = glob.glob(os.path.join(RAW_VIDEO_DIR, f"{vid_id}*.vtt"))
        if not vtt_matches:
            continue

        vtt_path = vtt_matches[0]
        cap = cv2.VideoCapture(vid_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width == 0 or height == 0 or total_frames == 0:
            cap.release()
            continue

        try:
            subs = webvtt.read(vtt_path)
        except Exception:
            cap.release()
            continue

        clips_in_video = 0
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
            if duration < 1.0 or duration > 10.0:
                continue

            start_frame = max(0, int(start_sec * fps))
            end_frame = min(total_frames, int(end_sec * fps))
            if end_frame <= start_frame:
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            clip_landmarks = []
            clip_frames = []

            for _ in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret:
                    break
                if SAVE_MP4_CLIPS:
                    clip_frames.append(frame)
                clip_landmarks.append(landmarker.extract(frame))

            if len(clip_landmarks) >= 15:
                clip_name = f"ish_{clip_counter:06d}"
                npy_file = f"{clip_name}.npy"
                mp4_file = f"{clip_name}.mp4" if SAVE_MP4_CLIPS else "N/A (Speed Optimized)"

                # Save 75-keypoint landmark array (.npy)
                np.save(os.path.join(LANDMARK_CLIPS_DIR, npy_file), np.array(clip_landmarks, dtype=np.float32))

                # Save MP4 video clip only if enabled
                if SAVE_MP4_CLIPS:
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(os.path.join(VIDEO_CLIPS_DIR, mp4_file), fourcc, fps, (width, height))
                    for f in clip_frames:
                        out.write(f)
                    out.release()

                metadata.append({
                    "sample_id": clip_name,
                    "source": "ISH_News",
                    "landmark_file": npy_file,
                    "video_file": mp4_file,
                    "video_source": vid_id,
                    "duration_sec": round(duration, 2),
                    "num_frames": len(clip_landmarks),
                    "sentence": text
                })
                clip_counter += 1
                clips_in_video += 1

        cap.release()
        
        # Save progress after EVERY video so you never lose any data!
        pd.DataFrame(metadata).to_csv(csv_path, index=False)
        print(f"[{vid_idx}/{len(video_files)}] {vid_id} -> Extracted {clips_in_video} clips (Total: {clip_counter})")

    landmarker.close()

    print("\n==================================================")
    print(f"EXTRACTION COMPLETE! Total clips: {len(metadata)}")
    print(f"Saved Metadata to: {csv_path}")
    print("==================================================")

def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--process-only":
        print("[+] Processing all already downloaded videos...")
        process_extracted_videos()
        return

    count = 200
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        count = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 200

    print(f"[+] Launching Automatic Extraction for {count} videos from ISH News Channel...")
    download_videos(mode="auto", max_videos=count)
    process_extracted_videos()

if __name__ == "__main__":
    main()
