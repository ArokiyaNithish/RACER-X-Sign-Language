import os
import glob
import random
import numpy as np
import pandas as pd

SOURCE1_CSV = os.path.join("dataset", "source1_ishnews", "source1_metadata.csv")
SOURCE1_DIR = os.path.join("dataset", "source1_ishnews", "landmark_clips")

SOURCE2_CSV = os.path.join("dataset", "source2_benchmarks", "source2_metadata.csv")
SOURCE2_DIR = os.path.join("dataset", "source2_benchmarks", "landmark_clips")

OUTPUT_DIR = os.path.join("dataset", "source3_augmented")
LANDMARK_CLIPS_DIR = os.path.join(OUTPUT_DIR, "landmark_clips")
os.makedirs(LANDMARK_CLIPS_DIR, exist_ok=True)

def apply_kinematic_transform(landmarks, aug_type):
    """
    Applies exact physical kinematic transformations:
    - flip: Left-handed signer mirroring (inverts X)
    - speed_fast: 1.25x signing speed (resamples frames)
    - speed_slow: 0.8x signing speed
    - dropout: 15% random landmark occlusion (for IEEE Table III)
    - jitter: Sensor noise perturbation (for IEEE Table IV)
    """
    seq = landmarks.copy()
    T, D = seq.shape

    if aug_type == "flip":
        for col in range(0, D, 4):
            seq[:, col] = 1.0 - seq[:, col]

    elif aug_type == "speed_fast":
        new_len = max(15, int(T * 0.8))
        idx = np.linspace(0, T - 1, new_len).astype(int)
        seq = seq[idx]

    elif aug_type == "speed_slow":
        new_len = min(90, int(T * 1.25))
        idx = np.linspace(0, T - 1, new_len).astype(int)
        seq = seq[idx]

    elif aug_type == "dropout":
        num_points = D // 4
        drop_count = int(num_points * 0.15)
        drop_idx = random.sample(range(num_points), drop_count)
        for pt in drop_idx:
            seq[:, pt*4 : pt*4+4] = 0.0

    elif aug_type == "jitter":
        noise = np.random.normal(0, 0.008, size=seq.shape).astype(np.float32)
        seq += noise

    return seq

def generate_augmented_corpus(target_count=10000):
    print("==================================================")
    print(f"[Source 3] Kinematic Physical Expander (Generating {target_count} samples)")
    print(f"Destination: {LANDMARK_CLIPS_DIR}")
    print("==================================================")

    # Gather available base samples from Source 1 and Source 2
    base_samples = []
    if os.path.exists(SOURCE1_CSV):
        df1 = pd.read_csv(SOURCE1_CSV)
        for _, r in df1.iterrows():
            base_samples.append((os.path.join(SOURCE1_DIR, r['landmark_file']), r['sentence'], "ISH_News"))

    if os.path.exists(SOURCE2_CSV):
        df2 = pd.read_csv(SOURCE2_CSV)
        for _, r in df2.iterrows():
            base_samples.append((os.path.join(SOURCE2_DIR, r['landmark_file']), r['sentence'], "Benchmark"))

    if not base_samples:
        print("[!] No base samples found in Source 1 or Source 2.")
        print("Please run collect_source1_ishnews.py or collect_source2_benchmarks.py first!")
        return

    print(f"Found {len(base_samples)} base sequences. Expanding to {target_count} physical samples on disk...")

    aug_types = ["flip", "speed_fast", "speed_slow", "dropout", "jitter"]
    metadata = []

    for idx in range(target_count):
        base_file, sentence, orig_src = random.choice(base_samples)
        if not os.path.exists(base_file):
            continue

        raw_landmarks = np.load(base_file).astype(np.float32)
        selected_aug = random.choice(aug_types)
        transformed = apply_kinematic_transform(raw_landmarks, selected_aug)

        sample_id = f"aug_{idx:06d}_{selected_aug}"
        npy_file = f"{sample_id}.npy"
        np.save(os.path.join(LANDMARK_CLIPS_DIR, npy_file), transformed)

        metadata.append({
            "sample_id": sample_id,
            "source": f"Kinematic_Augmented_{selected_aug}",
            "original_source": orig_src,
            "landmark_file": npy_file,
            "video_file": "N/A (Kinematic Augmentation)",
            "duration_sec": round(transformed.shape[0] / 30.0, 2),
            "num_frames": transformed.shape[0],
            "sentence": sentence,
            "aug_type": selected_aug
        })

        if (idx + 1) % 2000 == 0 or (idx + 1) == target_count:
            print(f"[{idx+1}/{target_count}] Physical augmented samples saved to disk...")

    csv_path = os.path.join(OUTPUT_DIR, "source3_metadata.csv")
    pd.DataFrame(metadata).to_csv(csv_path, index=False)
    print(f"\n[Source 3 Finished] Total Augmented Samples: {len(metadata)}")
    print(f"Metadata saved to: {csv_path}")

if __name__ == "__main__":
    generate_augmented_corpus(target_count=10000)
