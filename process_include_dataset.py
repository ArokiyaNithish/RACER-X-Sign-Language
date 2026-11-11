import os
import glob
import json
import shutil
import numpy as np
import pandas as pd

RAW_EXTRACT_DIR = os.path.join("dataset", "include_raw")
TARGET_DIR = os.path.join("dataset", "source2_benchmarks")
LANDMARK_CLIPS_DIR = os.path.join(TARGET_DIR, "landmark_clips")
os.makedirs(LANDMARK_CLIPS_DIR, exist_ok=True)

POSE_INDICES = [11, 12, 13, 14, 15, 16, 23, 24, 0] # 9 points
FACE_INDICES = [33, 133, 159, 145, 362, 263, 386, 374, 70, 63, 105, 66, 300, 293, 334, 296, 0, 13, 14, 17, 1, 152] # 22 points

def standardize_include():
    print("=" * 65)
    print("RACER-X: Standardizing Real Human Sign Landmarks")
    print("Department of AI & DS, Vel Tech R&D Institute, Chennai, India")
    print("=" * 65)

    if not os.path.exists(RAW_EXTRACT_DIR):
        print(f"[-] Error: {RAW_EXTRACT_DIR} not found. Please run run_extract_and_integrate.bat!")
        return

    # Check for parquet or npy or csv files inside extracted folder
    parquet_files = glob.glob(os.path.join(RAW_EXTRACT_DIR, "**", "*.parquet"), recursive=True)
    csv_files = glob.glob(os.path.join(RAW_EXTRACT_DIR, "**", "*.csv"), recursive=True)
    npy_files = glob.glob(os.path.join(RAW_EXTRACT_DIR, "**", "*.npy"), recursive=True)

    print(f"[+] Found files in archive: Parquet={len(parquet_files)}, CSV={len(csv_files)}, NPY={len(npy_files)}")

    metadata = []
    clip_count = 0

    if parquet_files:
        print(f"[+] Processing {len(parquet_files)} real gesture takes (Parquet format)...")
        for p_file in parquet_files:
            try:
                df = pd.read_parquet(p_file)
                # Google GISLR landmark structure: frame, row_id, type, landmark_index, x, y, z
                if 'frame' in df.columns and 'type' in df.columns:
                    frames = sorted(df['frame'].unique())
                    num_frames = len(frames)
                    if num_frames < 10:
                        continue

                    # Class name from directory or file name
                    class_name = os.path.basename(os.path.dirname(p_file)).upper().replace('_', ' ')
                    if not class_name or class_name == "INCLUDE_RAW":
                        class_name = os.path.basename(p_file).split('.')[0].upper()

                    landmarks = np.zeros((num_frames, 300), dtype=np.float32)

                    for f_idx, fr in enumerate(frames):
                        f_data = df[df['frame'] == fr]
                        
                        # Pose (9)
                        pose_data = f_data[f_data['type'] == 'pose']
                        for p_i, p_idx in enumerate(POSE_INDICES):
                            lm = pose_data[pose_data['landmark_index'] == p_idx]
                            if not lm.empty:
                                landmarks[f_idx, p_i*4 : p_i*4+4] = [lm['x'].values[0], lm['y'].values[0], lm['z'].values[0], 0.9]

                        # Face (22)
                        face_data = f_data[f_data['type'] == 'face']
                        face_start = 9 * 4
                        for f_i, fc_idx in enumerate(FACE_INDICES):
                            lm = face_data[face_data['landmark_index'] == fc_idx]
                            if not lm.empty:
                                landmarks[f_idx, face_start + f_i*4 : face_start + f_i*4+4] = [lm['x'].values[0], lm['y'].values[0], lm['z'].values[0], 1.0]

                        # Left Hand (21)
                        lh_data = f_data[f_data['type'] == 'left_hand']
                        lh_start = (9 + 22) * 4
                        for h_i in range(21):
                            lm = lh_data[lh_data['landmark_index'] == h_i]
                            if not lm.empty:
                                landmarks[f_idx, lh_start + h_i*4 : lh_start + h_i*4+4] = [lm['x'].values[0], lm['y'].values[0], lm['z'].values[0], 1.0]

                        # Right Hand (21)
                        rh_data = f_data[f_data['type'] == 'right_hand']
                        rh_start = (9 + 22 + 21) * 4
                        for h_i in range(21):
                            lm = rh_data[rh_data['landmark_index'] == h_i]
                            if not lm.empty:
                                landmarks[f_idx, rh_start + h_i*4 : rh_start + h_i*4+4] = [lm['x'].values[0], lm['y'].values[0], lm['z'].values[0], 1.0]

                    sample_id = f"real_isl_{clip_count:06d}"
                    npy_name = f"{sample_id}.npy"
                    np.save(os.path.join(LANDMARK_CLIPS_DIR, npy_name), landmarks)

                    metadata.append({
                        "sample_id": sample_id,
                        "source": "AI4Bharat_INCLUDE_Real",
                        "landmark_file": npy_name,
                        "video_file": os.path.basename(p_file),
                        "duration_sec": round(num_frames / 30.0, 2),
                        "num_frames": num_frames,
                        "sentence": class_name
                    })
                    clip_count += 1

                    if clip_count % 500 == 0:
                        print(f"[+] Standardized {clip_count} real human sign files...")

            except Exception as e:
                continue

    elif npy_files:
        print(f"[+] Processing {len(npy_files)} existing npy landmark files...")
        for n_file in npy_files:
            try:
                arr = np.load(n_file).astype(np.float32)
                if arr.ndim == 1:
                    arr = arr.reshape(1, -1)
                if arr.shape[1] < 300:
                    arr = np.pad(arr, ((0,0), (0, 300 - arr.shape[1])), mode='constant')
                else:
                    arr = arr[:, :300]

                class_name = os.path.basename(os.path.dirname(n_file)).upper().replace('_', ' ')
                sample_id = f"real_isl_{clip_count:06d}"
                npy_name = f"{sample_id}.npy"
                np.save(os.path.join(LANDMARK_CLIPS_DIR, npy_name), arr)

                metadata.append({
                    "sample_id": sample_id,
                    "source": "AI4Bharat_INCLUDE_Real",
                    "landmark_file": npy_name,
                    "video_file": os.path.basename(n_file),
                    "duration_sec": round(arr.shape[0] / 30.0, 2),
                    "num_frames": arr.shape[0],
                    "sentence": class_name
                })
                clip_count += 1
            except Exception:
                continue

    if metadata:
        meta_csv = os.path.join(TARGET_DIR, "source2_metadata.csv")
        pd.DataFrame(metadata).to_csv(meta_csv, index=False)
        print(f"\n[OK] Successfully standardized {len(metadata)} real human ISL gesture files!")
        print(f"[OK] Replaced synthetic data with real sign kinematics in: {meta_csv}")
        
        # Trigger rebuild of master dataset
        import build_master_dataset
        build_master_dataset.compile_master_corpus()
        
        import clean_and_rebuild_dataset
        clean_and_rebuild_dataset.build_clean_corpus()

        print("\n==================================================")
        print("REAL DATASET INTEGRATION COMPLETE!")
        print("Your model is now ready to train on 100% real human signing!")
        print("Run: run_train_phase3.bat to begin training.")
        print("==================================================")
    else:
        print("[!] No valid landmark files could be processed. Please check extracted folder structure.")

if __name__ == "__main__":
    standardize_include()
