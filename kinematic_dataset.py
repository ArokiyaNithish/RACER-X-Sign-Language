import os
import random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

class KinematicSignDataset(Dataset):
    """
    Kinematic Sign Language Dataset for RACER-X.
    Extracts Position (P), Velocity (V), Acceleration (A), Jerk (J), and Reliability (R).
    Performs on-the-fly Kinematic Augmentations to expand dataset scale past 25,000+ samples.
    """
    def __init__(self, metadata_csv, clips_dir, max_frames=64, augment=True):
        self.metadata = pd.read_csv(metadata_csv)
        self.clips_dir = clips_dir
        self.max_frames = max_frames
        self.augment = augment

        # Vocabulary builder (maps unique words to integer tokens for CTC loss)
        self.vocab = {"<blank>": 0, "<unk>": 1}
        for sent in self.metadata['sentence']:
            words = str(sent).upper().split()
            for w in words:
                if w not in self.vocab:
                    self.vocab[w] = len(self.vocab)
        self.inv_vocab = {v: k for k, v in self.vocab.items()}

    def __len__(self):
        return len(self.metadata)

    def _apply_augmentations(self, sequence):
        """
        Applies on-the-fly augmentations:
        1. Horizontal Flip (Simulates Left-Handed Signers)
        2. Speed Scaling (Fast / Slow signing)
        3. Landmark Dropout (Simulates Webcam Occlusion / Table III)
        4. Spatial Jitter (Simulates Sensor Noise)
        """
        seq = sequence.copy()
        T, D = seq.shape

        if not self.augment:
            return seq

        # 1. Horizontal Flip (50% probability)
        if random.random() < 0.5:
            # Invert X coordinates (every 4th element starting at index 0)
            for i in range(0, D, 4):
                seq[:, i] = 1.0 - seq[:, i]

        # 2. Landmark Dropout (30% probability, drops 10-20% of points)
        if random.random() < 0.3:
            num_points = D // 4
            drop_count = int(num_points * random.uniform(0.1, 0.25))
            drop_indices = random.sample(range(num_points), drop_count)
            for pt in drop_indices:
                seq[:, pt*4 : pt*4+4] = 0.0

        # 3. Spatial Jitter (adds subtle Gaussian noise to positions)
        if random.random() < 0.3:
            noise = np.random.normal(0, 0.008, size=seq.shape).astype(np.float32)
            seq += noise

        # 4. Temporal Speed Scaling (interpolates sequence length)
        if random.random() < 0.5 and T > 20:
            scale_factor = random.uniform(0.85, 1.2)
            new_len = max(15, min(self.max_frames, int(T * scale_factor)))
            indices = np.linspace(0, T - 1, new_len).astype(int)
            seq = seq[indices]

        return seq

    def _compute_kinematics(self, seq):
        """
        Computes 4-tier kinematics from normalized keypoints:
        Position (P), Velocity (V), Acceleration (A), Jerk (J), and Reliability (R).
        """
        T = seq.shape[0]

        # Extract [x, y, z] coordinates and confidence [c]
        # seq shape: (T, 75 * 4) -> 75 landmarks * 4 values [x, y, z, conf]
        reshaped = seq.reshape(T, 75, 4)
        P = reshaped[:, :, :3]  # (T, 75, 3)
        C = reshaped[:, :, 3]   # (T, 75) Confidence

        # 1. Adaptive Torso-Invariant Normalization
        # Centers coordinates relative to the mid-shoulder anchor and dynamically scales
        # by the torso dimension. Prevents distortion from camera distance or video crop.
        left_shoulder = P[:, 0, :]
        right_shoulder = P[:, 1, :]
        mid_shoulder = (left_shoulder + right_shoulder) / 2.0
        raw_scale = np.linalg.norm(left_shoulder - right_shoulder, axis=-1, keepdims=True)
        # Bounded adaptive scale: prevents zero-division and excessive amplification
        scale = np.clip(raw_scale, 0.10, 2.0)
        P_norm = (P - mid_shoulder[:, np.newaxis, :]) / scale[:, np.newaxis, :]

        # 2. Velocity (V = P_t - P_{t-1})
        V = np.zeros_like(P_norm)
        V[1:] = P_norm[1:] - P_norm[:-1]

        # 3. Acceleration (A = V_t - V_{t-1})
        A = np.zeros_like(V)
        A[1:] = V[1:] - V[:-1]

        # 4. Jerk (J = A_t - A_{t-1})
        J = np.zeros_like(A)
        J[1:] = A[1:] - A[:-1]

        # 5. Innovation 1: Frenet-Serret Differential Geometry (Curvature kappa & Torsion tau)
        # Models sharp finger bends and 3D out-of-plane rotational twists
        cross_va = np.cross(V, A)                                               # (T, 75, 3)
        norm_cross_va = np.linalg.norm(cross_va, axis=-1)                       # (T, 75)
        norm_v = np.linalg.norm(V, axis=-1)                                     # (T, 75)
        kappa = norm_cross_va / (np.power(norm_v, 3) + 1e-4)                    # (T, 75) Curvature
        kappa = np.clip(kappa, 0.0, 10.0)

        dot_vaj = np.sum(cross_va * J, axis=-1)                                 # (T, 75)
        tau = dot_vaj / (np.power(norm_cross_va, 2) + 1e-4)                     # (T, 75) 3D Torsion
        tau = np.clip(tau, -10.0, 10.0)

        # 6. Reliability score R_t per frame (combines visibility and jerk smoothness)
        # Lower score when landmarks jitter erratically or confidence is low
        jerk_magnitude = np.linalg.norm(J, axis=-1).mean(axis=-1, keepdims=True)  # (T, 1)
        mean_conf = C.mean(axis=-1, keepdims=True)                               # (T, 1)
        R = mean_conf * np.exp(-0.5 * jerk_magnitude)                             # (T, 1)

        # Flatten features per frame with full NaN/Inf guards
        P_flat = np.nan_to_num(P_norm.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0)   # (T, 225)
        V_flat = np.nan_to_num(V.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0)        # (T, 225)
        A_flat = np.nan_to_num(A.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0)        # (T, 225)
        J_flat = np.nan_to_num(J.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0)        # (T, 225)
        kappa_flat = np.nan_to_num(kappa.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0) # (T, 75)
        tau_flat = np.nan_to_num(tau.reshape(T, -1), nan=0.0, posinf=0.0, neginf=0.0)     # (T, 75)

        # Combined kinematic & differential geometric motion vector (825 dimensions)
        M_flat = np.concatenate([V_flat, A_flat, J_flat, kappa_flat, tau_flat], axis=-1)  # (T, 825)
        R = np.nan_to_num(R, nan=0.0, posinf=0.0, neginf=0.0)

        return P_flat, V_flat, M_flat, R

    def __getitem__(self, idx):
        row = self.metadata.iloc[idx]
        if 'landmark_path' in row and os.path.exists(str(row['landmark_path'])):
            clip_path = str(row['landmark_path'])
        elif 'clip_file' in row:
            clip_path = os.path.join(self.clips_dir, str(row['clip_file']))
        elif 'landmark_file' in row:
            clip_path = os.path.join(self.clips_dir, str(row['landmark_file']))
        else:
            raise KeyError("No valid landmark path or file column found in dataset metadata.")

        # Load raw landmarks (T, D)
        raw_landmarks = np.load(clip_path).astype(np.float32)
        raw_landmarks = np.nan_to_num(raw_landmarks, nan=0.0, posinf=0.0, neginf=0.0)

        # Standardize feature dimension to exactly 300 (75 landmarks * 4: x, y, z, conf)
        # Ensures seamless compatibility across Source 1 (292), Source 2 (300), and test videos
        if raw_landmarks.ndim == 1:
            raw_landmarks = raw_landmarks.reshape(1, -1)
        if raw_landmarks.shape[1] < 300:
            pad_width = 300 - raw_landmarks.shape[1]
            raw_landmarks = np.pad(raw_landmarks, ((0, 0), (0, pad_width)), mode='constant')
        elif raw_landmarks.shape[1] > 300:
            raw_landmarks = raw_landmarks[:, :300]

        # Apply on-the-fly augmentation
        augmented = self._apply_augmentations(raw_landmarks)

        # Compute Kinematics, Differential Geometry & Reliability
        P_flat, V_flat, M_flat, R = self._compute_kinematics(augmented)

        # Truncate or Pad to max_frames
        T = P_flat.shape[0]
        if T > self.max_frames:
            P_flat = P_flat[:self.max_frames]
            V_flat = V_flat[:self.max_frames]
            M_flat = M_flat[:self.max_frames]
            R = R[:self.max_frames]
            actual_len = self.max_frames
        else:
            pad_len = self.max_frames - T
            P_flat = np.pad(P_flat, ((0, pad_len), (0, 0)), mode='constant')
            V_flat = np.pad(V_flat, ((0, pad_len), (0, 0)), mode='constant')
            M_flat = np.pad(M_flat, ((0, pad_len), (0, 0)), mode='constant')
            R = np.pad(R, ((0, pad_len), (0, 0)), mode='constant')
            actual_len = T

        # Target tokenization for CTC loss
        words = str(row['sentence']).upper().split()
        target_tokens = [self.vocab.get(w, 1) for w in words]

        return {
            "spatial": torch.tensor(P_flat, dtype=torch.float32),      # (max_frames, 225)
            "velocity": torch.tensor(V_flat, dtype=torch.float32),     # (max_frames, 225)
            "motion": torch.tensor(M_flat, dtype=torch.float32),        # (max_frames, 825)
            "reliability": torch.tensor(R, dtype=torch.float32),        # (max_frames, 1)
            "seq_len": torch.tensor(actual_len, dtype=torch.long),
            "target": torch.tensor(target_tokens, dtype=torch.long),
            "target_len": torch.tensor(len(target_tokens), dtype=torch.long),
            "sentence": row['sentence']
        }
