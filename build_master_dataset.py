import os
import pandas as pd

SOURCE1_CSV = os.path.join("dataset", "source1_ishnews", "source1_metadata.csv")
SOURCE1_DIR = os.path.join("dataset", "source1_ishnews", "landmark_clips")

SOURCE2_CSV = os.path.join("dataset", "source2_benchmarks", "source2_metadata.csv")
SOURCE2_DIR = os.path.join("dataset", "source2_benchmarks", "landmark_clips")

SOURCE3_CSV = os.path.join("dataset", "source3_augmented", "source3_metadata.csv")
SOURCE3_DIR = os.path.join("dataset", "source3_augmented", "landmark_clips")

MASTER_CSV = os.path.join("dataset", "master_dataset.csv")
MASTER_CSV_30K = os.path.join("dataset", "master_dataset_30k.csv")

def compile_master_corpus():
    print("==================================================")
    print("Compiling Master Multi-Source Dataset (Target: 30,000+)")
    print("==================================================")

    records = []

    # 1. Source 1: ISH News
    if os.path.exists(SOURCE1_CSV):
        df1 = pd.read_csv(SOURCE1_CSV)
        for _, r in df1.iterrows():
            abs_path = os.path.abspath(os.path.join(SOURCE1_DIR, r['landmark_file']))
            if os.path.exists(abs_path):
                records.append({
                    "sample_id": r['sample_id'],
                    "source": "ISH_News_Broadcast",
                    "landmark_path": abs_path,
                    "video_file": r.get('video_file', 'N/A'),
                    "num_frames": r['num_frames'],
                    "duration_sec": r['duration_sec'],
                    "sentence": r['sentence']
                })
        print(f"[+] Source 1 (ISH News): {len(records)} verified samples.")

    s1_count = len(records)

    # 2. Source 2: Benchmark
    if os.path.exists(SOURCE2_CSV):
        df2 = pd.read_csv(SOURCE2_CSV)
        for _, r in df2.iterrows():
            abs_path = os.path.abspath(os.path.join(SOURCE2_DIR, r['landmark_file']))
            if os.path.exists(abs_path):
                records.append({
                    "sample_id": r['sample_id'],
                    "source": "ISL_National_Benchmark",
                    "landmark_path": abs_path,
                    "video_file": "N/A",
                    "num_frames": r['num_frames'],
                    "duration_sec": r['duration_sec'],
                    "sentence": r['sentence']
                })
        print(f"[+] Source 2 (ISL Benchmark): {len(records) - s1_count} verified samples.")

    s2_count = len(records) - s1_count

    # 3. Source 3: Kinematic Augmented
    if os.path.exists(SOURCE3_CSV):
        df3 = pd.read_csv(SOURCE3_CSV)
        for _, r in df3.iterrows():
            abs_path = os.path.abspath(os.path.join(SOURCE3_DIR, r['landmark_file']))
            if os.path.exists(abs_path):
                records.append({
                    "sample_id": r['sample_id'],
                    "source": "Kinematic_Augmented",
                    "landmark_path": abs_path,
                    "video_file": "N/A",
                    "num_frames": r['num_frames'],
                    "duration_sec": r['duration_sec'],
                    "sentence": r['sentence']
                })
        print(f"[+] Source 3 (Augmented): {len(records) - s1_count - s2_count} verified samples.")

    if not records:
        print("[!] No records compiled. Please run the collection scripts for Source 1, 2, and 3 first!")
        return

    master_df = pd.DataFrame(records)
    master_df.to_csv(MASTER_CSV, index=False)
    master_df.to_csv(MASTER_CSV_30K, index=False)

    print("\n==================================================")
    print("DATASET COLLECTION COMPLETED SUCCESSFULLY!")
    print(f"Master Metadata File: {MASTER_CSV}")
    print(f"Total Physical Samples Ready on Disk: {len(master_df):,}")
    print("Breakdown by Source:")
    print(master_df['source'].value_counts().to_string())
    print("==================================================")

if __name__ == "__main__":
    compile_master_corpus()
