import subprocess
import os
import sys

URLS_FILE = "urls.txt"
RAW_DIR = os.path.join("dataset", "raw_videos")
os.makedirs(RAW_DIR, exist_ok=True)

if not os.path.exists(URLS_FILE):
    print(f"Error: {URLS_FILE} not found!")
    sys.exit(1)

with open(URLS_FILE, "r") as f:
    urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

print(f"==================================================")
print(f"Found {len(urls)} ISH News videos to download.")
print(f"Destination folder: {RAW_DIR}")
print(f"==================================================")

for idx, url in enumerate(urls, 1):
    output_template = os.path.join(RAW_DIR, f"video_{idx:02d}.%(ext)s")
    print(f"\n[+] Downloading Video {idx:02d}/{len(urls):02d}...")
    print(f"    URL: {url}")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "--merge-output-format", "mp4",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "-o", output_template,
        url
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"[OK] Successfully downloaded video_{idx:02d}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to download video_{idx:02d}: {e}")
    except FileNotFoundError:
        print("\n[CRITICAL ERROR] 'yt-dlp' is not installed or not in your PATH!")
        print("Please run: pip install yt-dlp")
        sys.exit(1)

print("\n==================================================")
print("Finished downloading all 10 videos and subtitles!")
print(f"Check folder: {RAW_DIR}")
print("==================================================")
