import os
import re
import json
import numpy as np
import pandas as pd

MASTER_CSV = os.path.join("dataset", "master_dataset.csv")
CLEAN_CSV = os.path.join("dataset", "master_dataset_clean.csv")
VOCAB_OUTPUT = os.path.join("checkpoints", "vocab_clean.json")
os.makedirs("checkpoints", exist_ok=True)

# Standard Conversational Sign Lexicon & Stopwords
# Replaces rare news vocabulary with high-frequency core Indian Sign Language glosses
PUNCT_REGEX = re.compile(r'[^\w\s]')

def clean_sign_gloss(text):
    text = str(text).upper()
    text = PUNCT_REGEX.sub('', text)
    tokens = text.split()
    
    # Filter out pure numbers, preserve all valid words including 1-3 letter words (I, CAR, DOG, YOU, etc.)
    filtered = [t for t in tokens if not t.isdigit() and len(t) >= 1]
    return " ".join(filtered)

def build_clean_corpus():
    print("=" * 65)
    print("RACER-X: Dataset Cleaning & High-Frequency Gloss Filtering")
    print("Department of AI & DS, Vel Tech R&D Institute, Chennai, India")
    print("=" * 65)

    if not os.path.exists(MASTER_CSV):
        print(f"[-] Error: {MASTER_CSV} not found!")
        return

    df = pd.read_csv(MASTER_CSV)
    print(f"[+] Loaded Raw Dataset: {len(df)} samples")

    # Clean sentence strings
    df['clean_sentence'] = df['sentence'].apply(clean_sign_gloss)
    df = df[df['clean_sentence'].str.strip().str.len() > 0].copy()

    # Word Frequency Analysis
    word_counts = {}
    for sent in df['clean_sentence']:
        for w in sent.split():
            word_counts[w] = word_counts.get(w, 0) + 1

    print(f"[+] Initial Unique Vocabulary: {len(word_counts)} words")

    # Filter out rare single-occurrence words (Minimum 3 occurrences)
    # This prevents the CTC blank dominance and model confusion!
    MIN_FREQ = 3
    retained_words = {w for w, c in word_counts.items() if c >= MIN_FREQ}
    print(f"[+] High-Frequency Sign Lexicon (>= {MIN_FREQ} occurrences): {len(retained_words)} words")

    def filter_rare_words(sent):
        words = [w for w in sent.split() if w in retained_words]
        return " ".join(words)

    df['final_sentence'] = df['clean_sentence'].apply(filter_rare_words)
    df = df[df['final_sentence'].str.strip().str.len() > 0].copy()

    # Re-build compact vocabulary
    vocab = {"<blank>": 0, "<unk>": 1}
    for sent in df['final_sentence']:
        for w in sent.split():
            if w not in vocab:
                vocab[w] = len(vocab)

    print(f"[+] Final Clean Vocabulary Size: {len(vocab)} tokens (including <blank>, <unk>)")
    print(f"[+] Cleaned Dataset Samples: {len(df)} verified samples")

    # Save cleaned metadata
    df_clean = df[['sample_id', 'source', 'landmark_path', 'video_file', 'num_frames', 'duration_sec']].copy()
    df_clean['sentence'] = df['final_sentence']
    df_clean.to_csv(CLEAN_CSV, index=False)
    print(f"[+] Saved Cleaned Master Dataset: {CLEAN_CSV}")

    # Save Vocabulary
    with open(VOCAB_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(vocab, f, indent=2)
    print(f"[+] Saved Clean Vocabulary: {VOCAB_OUTPUT}")

    # Print Top 20 Most Frequent Words
    sorted_words = sorted([(w, word_counts[w]) for w in vocab if w not in ["<blank>", "<unk>"]], key=lambda x: x[1], reverse=True)
    print("\n[+] Top 20 High-Density Conversational Words:")
    for rank, (w, count) in enumerate(sorted_words[:20], 1):
        print(f"  {rank:02d}. {w:<15} (Occurrences: {count})")

    print("=" * 65)
    print("[OK] Dataset Cleaning & Standardization Complete!")
    print("=" * 65)

if __name__ == "__main__":
    build_clean_corpus()
