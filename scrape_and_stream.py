import os
import glob
import cv2
import webvtt
import subprocess
import numpy as np
import pandas as pd
import mediapipe as mp

# =================CONFIGURATION=================
OUTPUT_DIR = os.path.join("dataset", "ish_dataset")
RAW_VIDEO_DIR = os.path.join(OUTPUT_DIR, "raw_videos")
VIDEO_CLIPS_DIR = os.path.join(OUTPUT_DIR, "video_clips")
LANDMARK_CLIPS_DIR = os.path.join(OUTPUT_DIR, "landmark_clips")

os.makedirs(RAW_VIDEO_DIR, exist_ok=True)
os.makedirs(VIDEO_CLIPS_DIR, exist_ok=True)
os.makedirs(LANDMARK_CLIPS_DIR, exist_ok=True)

# 1 TB Storage enabled: Keep all raw videos and segmented MP4 clips
KEEP_RAW_VIDEOS = True

# Target number of videos to download if scraping playlist/channel
MAX_VIDEOS = 150

# Selected Landmarks: 75 keypoints * 4 = 300 dimensions per frame
# 1. Pose: Upper body (9 points)
POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0]
# 2. Face: Eyebrows, Eyes, Lips, Nose, Chin (22 points)
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152]

# Setup MediaPipe Holistic with robust fallback imports
try:
    import mediapipe.python.solutions.holistic as mp_holistic
except (ImportError, AttributeError):
    try:
        from mediapipe import solutions
        mp_holistic = solutions.holistic
    except (ImportError, AttributeError):
        import mediapipe as mp
        mp_holistic = mp.solutions.holistic

def extract_landmarks(results):
    if results.pose_landmarks:
        pose = [[results.pose_landmarks.landmark[i].x, results.pose_landmarks.landmark[i].y,
                 results.pose_landmarks.landmark[i].z, results.pose_landmarks.landmark[i].visibility]
                for i in POSE_INDICES]
    else:
        pose = [[0.0] * 4] * len(POSE_INDICES)

    if results.face_landmarks:
        face = [[results.face_landmarks.landmark[i].x, results.face_landmarks.landmark[i].y,
                 results.face_landmarks.landmark[i].z, 1.0]
                for i in FACE_INDICES]
    else:
        face = [[0.0] * 4] * len(FACE_INDICES)

    if results.left_hand_landmarks:
        lh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.left_hand_landmarks.landmark]
    else:
        lh = [[0.0] * 4] * 21

    if results.right_hand_landmarks:
        rh = [[lm.x, lm.y, lm.z, 1.0] for lm in results.right_hand_landmarks.landmark]
    else:
        rh = [[0.0] * 4] * 21

    return np.concatenate([pose, face, lh, rh]).flatten()

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

def download_videos_from_source(source_url_or_file):
    """
    Downloads videos and English subtitles into RAW_VIDEO_DIR using yt-dlp.
    Supports either a playlist URL or a urls.txt file.
    """
    print(f"\n[+] Starting batch download from: {source_url_or_file}")
    output_template = os.path.join(RAW_VIDEO_DIR, "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "--merge-output-format", "mp4",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--max-downloads", str(MAX_VIDEOS),
        "-o", output_template
    ]

    if os.path.exists(source_url_or_file):
        cmd.extend(["-a", source_url_or_file])
    else:
        cmd.append(source_url_or_file)

    try:
        subprocess.run(cmd, check=True)
        print("[OK] Video downloads completed successfully.")
    except Exception as e:
        print(f"[!] Warning during download: {e}")

def process_downloaded_videos():
    """
    Iterates through all downloaded MP4s, reads matching VTT subtitles,
    slices video clips, extracts MediaPipe landmarks, and builds metadata.csv.
    """
    video_files = sorted(glob.glob(os.path.join(RAW_VIDEO_DIR, "*.mp4")))
    if not video_files:
        print(f"[!] No mp4 files found in {RAW_VIDEO_DIR}.")
        return

    print("==================================================")
    print(f"High-Capacity Dataset Extractor (1 TB Storage Mode)")
    print(f"Total videos to process: {len(video_files)}")
    print(f"Video clips directory: {VIDEO_CLIPS_DIR}")
    print(f"Landmarks directory: {LANDMARK_CLIPS_DIR}")
    print("==================================================")

    metadata = []
    global_clip_count = 0

    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        for vid_idx, vid_path in enumerate(video_files, 1):
            vid_id = os.path.splitext(os.path.basename(vid_path))[0]
            vtt_matches = glob.glob(os.path.join(RAW_VIDEO_DIR, f"{vid_id}*.vtt"))

            if not vtt_matches:
                print(f"[!] Skipping {vid_id}: Subtitle .vtt file not found.")
                continue

            vtt_path = vtt_matches[0]
            print(f"\n[Video {vid_idx}/{len(video_files)}] Processing: {vid_id}...")

            cap = cv2.VideoCapture(vid_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            try:
                subs = webvtt.read(vtt_path)
            except Exception as e:
                print(f"[!] Error parsing subtitles for {vid_id}: {e}")
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
                if duration < 1.2 or duration > 10.0:
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

                    clip_frames.append(frame)
                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = holistic.process(img_rgb)
                    clip_landmarks.append(extract_landmarks(results))

                if len(clip_landmarks) >= 20:
                    clip_id_str = f"clip_{global_clip_count:06d}"
                    
                    # 1. Save .npy landmark array
                    npy_filename = f"{clip_id_str}.npy"
                    npy_path = os.path.join(LANDMARK_CLIPS_DIR, npy_filename)
                    np.save(npy_path, np.array(clip_landmarks, dtype=np.float32))

                    # 2. Save .mp4 video clip (since storage is 1 TB!)
                    mp4_filename = f"{clip_id_str}.mp4"
                    mp4_path = os.path.join(VIDEO_CLIPS_DIR, mp4_filename)
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))
                    for f in clip_frames:
                        out.write(f)
                    out.release()

                    metadata.append({
                        "clip_id": global_clip_count,
                        "clip_file": npy_filename,
                        "video_clip": mp4_filename,
                        "video_source": vid_id,
                        "start_time": sub.start,
                        "end_time": sub.end,
                        "duration_sec": round(duration, 2),
                        "num_frames": len(clip_landmarks),
                        "sentence": text
                    })
                    global_clip_count += 1
                    clips_in_video += 1

            cap.release()
            print(f"   -> Extracted {clips_in_video} sentence clips (Total so far: {global_clip_count})")

    # Save Master CSV
    df = pd.DataFrame(metadata)
    csv_path = os.path.join(OUTPUT_DIR, "metadata.csv")
    df.to_csv(csv_path, index=False)

    print("\n==================================================")
    print(f"EXTRACTION COMPLETE!")
    print(f"Total Sentences Extracted: {len(df)}")
    print(f"Saved Video Clips (.mp4): {VIDEO_CLIPS_DIR}")
    print(f"Saved Landmark Clips (.npy): {LANDMARK_CLIPS_DIR}")
    print(f"Master Metadata CSV: {csv_path}")
    print("==================================================")

if __name__ == "__main__":
    # If urls.txt exists, download from it, or pass an entire ISH News Playlist URL
    source = "urls.txt"
    download_videos_from_source(source)
    process_downloaded_videos()
