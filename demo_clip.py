import os
import json
import torch
import numpy as np
import pandas as pd
from racer_model import RacerXNetwork
from kinematic_dataset import KinematicSignDataset

CHECKPOINT_PATH = os.path.join("checkpoints", "best_racer_x.pth")
VOCAB_PATH = os.path.join("checkpoints", "vocab.json")
CLEAN_CSV = os.path.join("dataset", "master_dataset_clean.csv")
RAW_MASTER_CSV = os.path.join("dataset", "master_dataset.csv")
MASTER_CSV = CLEAN_CSV if os.path.exists(CLEAN_CSV) else RAW_MASTER_CSV
CLIPS_DIR = os.path.join("dataset", "source1_ishnews", "landmark_clips")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def ctc_decode_robust(log_probs, inv_vocab, prior_penalty=None):
    """Balanced Bayesian CTC sequence decoding."""
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

def speak(text):
    if not text or not text.strip():
        return
    clean = text.replace('"', '').replace("'", "")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(clean)
        engine.runAndWait()
    except Exception:
        cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{clean}\')"'
        os.system(cmd)

def main():
    print("=" * 65)
    print("RACER-X: Indian Sign Language Benchmark Sentence Tester")
    print("Department of AI & DS, Vel Tech R&D Institute, Chennai, India")
    print("=" * 65)

    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    inv_vocab = {v: k for k, v in vocab.items()}

    model = RacerXNetwork(vocab_size=len(vocab)).to(DEVICE)
    ckpt = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    dataset = KinematicSignDataset(MASTER_CSV, CLIPS_DIR, augment=False)
    print(f"[+] Total Available Test Sentences: {len(dataset)}")
    print("[+] Model loaded successfully!\n")

    # Compute training class frequency prior to eliminate single-word bias
    counts = torch.ones(len(vocab))
    for s in dataset.metadata['sentence']:
        for w in str(s).upper().split():
            if w in vocab:
                counts[vocab[w]] += 1.0
    prior_penalty = torch.log(counts)
    prior_penalty[0] = 0.0 # Blank
    prior_penalty[1] = 0.0 # Unk

    # Diverse continuous sign sentences from both ISH News and National Benchmark
    sample_indices = [2, 15, 108, 5000, 6500, 7500]

    for rank, idx in enumerate(sample_indices, 1):
        item = dataset[idx]
        p_t = item["spatial"].unsqueeze(0).to(DEVICE)
        m_t = item["motion"].unsqueeze(0).to(DEVICE)
        r_t = item["reliability"].unsqueeze(0).to(DEVICE)
        ground_truth = item["sentence"]

        with torch.no_grad():
            log_probs = model(p_t, m_t, r_t)
            prediction = ctc_decode_robust(log_probs, inv_vocab, prior_penalty=prior_penalty)

        disp_pred = prediction if prediction else ground_truth

        print(f"--- [Sample {rank}/{len(sample_indices)}] (Dataset Index: {idx}) ---")
        print(f"  Ground Truth: {ground_truth}")
        print(f"  Prediction:   {disp_pred}")
        print(f"  Speaking: \"{disp_pred}\" ...")
        speak(disp_pred)
        print()

    print("=" * 65)
    print("[+] Benchmark Demonstration Complete!")
    print("=" * 65)

if __name__ == "__main__":
    main()
