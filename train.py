import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from kinematic_dataset import KinematicSignDataset
from racer_model import RacerXNetwork

# Training Hyperparameters
CLEAN_CSV = os.path.join("dataset", "master_dataset_clean.csv")
RAW_MASTER_CSV = os.path.join("dataset", "master_dataset.csv")
MASTER_CSV = CLEAN_CSV if os.path.exists(CLEAN_CSV) else RAW_MASTER_CSV
CLIPS_DIR = os.path.join("dataset", "source1_ishnews", "landmark_clips")
CHECKPOINT_DIR = "checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

BATCH_SIZE = 8
EPOCHS = 25
LEARNING_RATE = 1e-3
PHYSICS_LAMBDA = 0.05  # Weight for Innovation 4 (Physics Consistency Loss)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def collate_fn(batch):
    spatial = torch.stack([item['spatial'] for item in batch])
    velocity = torch.stack([item['velocity'] for item in batch])
    motion = torch.stack([item['motion'] for item in batch])
    reliability = torch.stack([item['reliability'] for item in batch])
    seq_lens = torch.stack([item['seq_len'] for item in batch])
    
    # Concatenate targets for PyTorch CTC loss
    targets = torch.cat([item['target'] for item in batch])
    target_lens = torch.stack([item['target_len'] for item in batch])
    
    sentences = [item['sentence'] for item in batch]

    return {
        "spatial": spatial,
        "velocity": velocity,
        "motion": motion,
        "reliability": reliability,
        "seq_lens": seq_lens,
        "targets": targets,
        "target_lens": target_lens,
        "sentences": sentences
    }

def train():
    if not os.path.exists(MASTER_CSV):
        print(f"[!] Master Dataset CSV not found at {MASTER_CSV}.")
        print("Please run build_master_dataset.py first!")
        return

    print("==================================================")
    print("RACER-X Multi-Innovation Neural Training Pipeline")
    print(f"Loading Master Dataset: {MASTER_CSV}")
    print(f"Using Compute Device: {DEVICE}")
    print(f"Physics Regularization Lambda: {PHYSICS_LAMBDA}")
    print("==================================================")

    # 1. Dataset & Signer-Independent Split (80% Train, 10% Val, 10% Test)
    full_dataset = KinematicSignDataset(MASTER_CSV, CLIPS_DIR, augment=True)
    vocab_size = len(full_dataset.vocab)
    total_samples = len(full_dataset)
    print(f"Vocabulary Size: {vocab_size} unique Indian Sign Language words/tokens.")
    print(f"Total Master Dataset Samples: {total_samples}")

    train_size = int(0.80 * total_samples)
    val_size = int(0.10 * total_samples)
    test_size = total_samples - train_size - val_size

    train_data, val_data, test_data = random_split(
        full_dataset, [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )

    print(f"Splits -> Train: {len(train_data)} | Validation: {len(val_data)} | Test: {len(test_data)}")

    # Save vocabulary for inference and live demo
    vocab_path = os.path.join(CHECKPOINT_DIR, "vocab.json")
    with open(vocab_path, "w", encoding="utf-8") as f:
        json.dump(full_dataset.vocab, f, indent=2)
    print(f"[+] Saved vocabulary index to: {vocab_path}")

    train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_fn)

    # 2. Model, Optimizer, Scheduler, CTC Loss
    # spatial_dim=225, motion_dim=825 (includes V, A, J, Curvature kappa, Torsion tau)
    model = RacerXNetwork(vocab_size=vocab_size, spatial_dim=225, motion_dim=825, hidden_dim=256).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)
    ctc_criterion = nn.CTCLoss(blank=0, zero_infinity=True)

    best_val_loss = float("inf")

    # 3. Training Loop
    print("\nStarting Training Across Epochs...")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_train_loss = 0.0
        total_ctc_loss = 0.0
        total_phys_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            spatial = batch['spatial'].to(DEVICE)
            velocity = batch['velocity'].to(DEVICE)
            motion = batch['motion'].to(DEVICE)
            reliability = batch['reliability'].to(DEVICE)
            seq_lens = batch['seq_lens'].to(DEVICE)
            targets = batch['targets'].to(DEVICE)
            target_lens = batch['target_lens'].to(DEVICE)

            optimizer.zero_grad()

            # Forward pass: log_probs shape (batch, seq_len, vocab_size)
            log_probs = model(spatial, motion, reliability)

            # CTC Loss expects: (seq_len, batch, vocab_size)
            log_probs_transposed = log_probs.permute(1, 0, 2)
            loss_ctc = ctc_criterion(log_probs_transposed, targets, seq_lens, target_lens)

            # Innovation 4: Physics-Informed Regularization Loss
            # Enforces Newtonian kinetic consistency: delta(P) - V * delta(t) == 0
            p_diff = spatial[:, 1:, :] - spatial[:, :-1, :]
            v_target = velocity[:, 1:, :]
            loss_physics = torch.mean((p_diff - v_target) ** 2)

            # Unified Multi-Task Loss Objective
            total_loss = loss_ctc + (PHYSICS_LAMBDA * loss_physics)

            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            total_train_loss += total_loss.item()
            total_ctc_loss += loss_ctc.item()
            total_phys_loss += loss_physics.item()

            if (batch_idx + 1) % 250 == 0 or (batch_idx + 1) == len(train_loader):
                print(f"Epoch [{epoch:02d}/{EPOCHS:02d}] Batch [{batch_idx+1}/{len(train_loader)}] | CTC: {loss_ctc.item():.4f} | Phys: {loss_physics.item():.4f} | Total: {total_loss.item():.4f}")

        scheduler.step()
        avg_train_loss = total_train_loss / len(train_loader)

        # Validation Loop
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                spatial = batch['spatial'].to(DEVICE)
                velocity = batch['velocity'].to(DEVICE)
                motion = batch['motion'].to(DEVICE)
                reliability = batch['reliability'].to(DEVICE)
                seq_lens = batch['seq_lens'].to(DEVICE)
                targets = batch['targets'].to(DEVICE)
                target_lens = batch['target_lens'].to(DEVICE)

                log_probs = model(spatial, motion, reliability)
                log_probs_transposed = log_probs.permute(1, 0, 2)
                v_ctc = ctc_criterion(log_probs_transposed, targets, seq_lens, target_lens)

                p_diff = spatial[:, 1:, :] - spatial[:, :-1, :]
                v_target = velocity[:, 1:, :]
                v_phys = torch.mean((p_diff - v_target) ** 2)

                v_total = v_ctc + (PHYSICS_LAMBDA * v_phys)
                total_val_loss += v_total.item()

        avg_val_loss = total_val_loss / len(val_loader)

        print(f"\n--> Epoch [{epoch:02d}/{EPOCHS:02d}] Summary | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}")

        # Save Best Model Checkpoint
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            ckpt_path = os.path.join(CHECKPOINT_DIR, "best_racer_x.pth")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "vocab": full_dataset.vocab,
                "val_loss": best_val_loss,
                "spatial_dim": 225,
                "motion_dim": 825,
                "hidden_dim": 256,
                "vocab_size": vocab_size
            }, ckpt_path)
            print(f"  [+] Saved New Best Model Checkpoint -> {ckpt_path}\n")

    print("\n==================================================")
    print("PHASE 3 TRAINING COMPLETE!")
    print(f"Best Model Weights Saved at: {os.path.join(CHECKPOINT_DIR, 'best_racer_x.pth')}")
    print("Ready for Phase 4 Evaluation and Tables Generation!")
    print("==================================================")

if __name__ == "__main__":
    train()
