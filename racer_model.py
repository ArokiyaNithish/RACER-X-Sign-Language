import torch
import torch.nn as nn
import torch.nn.functional as F

class BilateralCrossAttention(nn.Module):
    """
    Innovation 3: Bilateral Cross-Hand Attention between
    Dominant Articulator (Right Hand) and Supportive Anchor (Left Hand).
    Models co-articulation for two-handed Indian Sign Language signs.
    """
    def __init__(self, hand_dim=63, attn_dim=64):
        super(BilateralCrossAttention, self).__init__()
        self.query = nn.Linear(hand_dim, attn_dim)
        self.key = nn.Linear(hand_dim, attn_dim)
        self.value = nn.Linear(hand_dim, attn_dim)
        self.scale = attn_dim ** 0.5
        self.out_proj = nn.Linear(attn_dim, hand_dim)

    def forward(self, right_hand, left_hand):
        # right_hand: (batch, 63), left_hand: (batch, 63)
        Q = self.query(right_hand).unsqueeze(1)  # (batch, 1, attn_dim)
        K = self.key(left_hand).unsqueeze(1)    # (batch, 1, attn_dim)
        V = self.value(left_hand).unsqueeze(1)  # (batch, 1, attn_dim)

        scores = torch.bmm(Q, K.transpose(1, 2)) / self.scale  # (batch, 1, 1)
        attn_weights = F.softmax(scores, dim=-1)
        context = torch.bmm(attn_weights, V).squeeze(1)        # (batch, attn_dim)
        return self.out_proj(context)                          # (batch, 63)

class RacerXCell(nn.Module):
    """
    RACER-X Recurrent Cell.
    Conditions temporal memory updates on:
      1. Spatial evidence (S_t) with Bilateral Hand Attention
      2. Kinematic & Differential Geometric motion (M_t: V, A, J, kappa, tau)
      3. Observation Reliability (R_t)
      4. Spatial-Motion Agreement (A_t)
    Suppresses memory updates when inputs are noisy, occluded, or conflicting.
    """
    def __init__(self, spatial_dim=225, motion_dim=825, hidden_dim=256):
        super(RacerXCell, self).__init__()
        self.hidden_dim = hidden_dim

        # Innovation 3: Bilateral Cross-Hand Attention Module
        self.bilateral_attn = BilateralCrossAttention(hand_dim=63, attn_dim=64)

        # 1. Feature projections (Spatial dimension expanded with bilateral attention features)
        self.fc_spatial = nn.Linear(spatial_dim + 63, hidden_dim)
        self.fc_motion = nn.Linear(motion_dim, hidden_dim)

        # 2. Agreement projections (f_sp, f_mp)
        self.proj_sp = nn.Linear(hidden_dim, 64)
        self.proj_mp = nn.Linear(hidden_dim, 64)

        # 3. Candidate recurrent state projection (f_h)
        self.fc_candidate = nn.Linear(hidden_dim * 2 + hidden_dim, hidden_dim)

        # 4. Conflict & Reliability conditioned Gate (f_g)
        # Inputs: [S_t, M_t, H_{t-1}, R_t, A_t]
        self.fc_gate = nn.Linear(hidden_dim * 2 + hidden_dim + 2, hidden_dim)

    def forward(self, P_t, M_t, R_t, H_prev):
        """
        P_t: (batch, 225) Spatial keypoints
        M_t: (batch, 825) Motion + Differential Geometry (V, A, J, kappa, tau)
        R_t: (batch, 1) Reliability score
        H_prev: (batch, hidden_dim) Previous recurrent state
        """
        # Step 1a: Innovation 3 - Bilateral Attention between Left and Right Hands
        # Left Hand coords: 93 to 156 (21 keypoints * 3), Right Hand coords: 156 to 219
        lh = P_t[:, 93:156]
        rh = P_t[:, 156:219]
        bilateral_ctx = self.bilateral_attn(rh, lh)  # (batch, 63)
        augmented_spatial = torch.cat([P_t, bilateral_ctx], dim=-1)

        # Step 1b: Spatial & Motion embeddings
        S_t = F.relu(self.fc_spatial(augmented_spatial))
        M_t_feat = F.relu(self.fc_motion(M_t))

        # Step 2: Spatial-Motion Agreement A_t (Cosine similarity)
        sp_emb = F.normalize(self.proj_sp(S_t), p=2, dim=-1)
        mp_emb = F.normalize(self.proj_mp(M_t_feat), p=2, dim=-1)
        A_t = torch.sum(sp_emb * mp_emb, dim=-1, keepdim=True)  # (batch, 1) in [-1, 1]

        # Step 3: Candidate recurrent state H_tilde
        combined_features = torch.cat([S_t, M_t_feat, H_prev], dim=-1)
        H_tilde = torch.tanh(self.fc_candidate(combined_features))

        # Step 4: Conflict & Reliability Conditioned Gate g_t
        gate_input = torch.cat([S_t, M_t_feat, H_prev, R_t, A_t], dim=-1)
        g_t = torch.sigmoid(self.fc_gate(gate_input))

        # Step 5: State Update (Eq. 11 in paper)
        # If R_t is low or A_t is conflicting, g_t -> 0, preserving H_prev!
        H_t = g_t * H_tilde + (1.0 - g_t) * H_prev

        return H_t, g_t, A_t

class RacerXNetwork(nn.Module):
    """
    Complete Continuous Sign Recognition Network with RACER-X Recurrent Core,
    Dynamic Uncertainty-Scaled CTC sequence decoder, and Physics regularization.
    """
    def __init__(self, vocab_size, spatial_dim=225, motion_dim=825, hidden_dim=256, num_layers=2):
        super(RacerXNetwork, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.vocab_size = vocab_size

        # RACER-X recurrent layer
        self.cell_layer1 = RacerXCell(spatial_dim, motion_dim, hidden_dim)
        
        # Second recurrent layer (GRU) for higher-level temporal sequence modeling
        self.rnn_layer2 = nn.GRU(hidden_dim, hidden_dim, batch_first=True)

        # Classification head (Linear projection to vocabulary size)
        self.classifier = nn.Linear(hidden_dim, vocab_size)

    def forward(self, spatial_seq, motion_seq, reliability_seq):
        """
        spatial_seq: (batch, seq_len, 225)
        motion_seq: (batch, seq_len, 825)
        reliability_seq: (batch, seq_len, 1)
        """
        batch_size, seq_len, _ = spatial_seq.shape
        device = spatial_seq.device

        # Initialize recurrent state
        H_t = torch.zeros(batch_size, self.hidden_dim, device=device)
        layer1_outputs = []

        # Causal temporal processing frame by frame
        for t in range(seq_len):
            P_t = spatial_seq[:, t, :]
            M_t = motion_seq[:, t, :]
            R_t = reliability_seq[:, t, :]

            H_t, _, _ = self.cell_layer1(P_t, M_t, R_t, H_t)
            layer1_outputs.append(H_t.unsqueeze(1))

        # Stack outputs along time dimension: (batch, seq_len, hidden_dim)
        h_seq1 = torch.cat(layer1_outputs, dim=1)

        # Pass through second temporal layer
        h_seq2, _ = self.rnn_layer2(h_seq1)

        # Compute raw logits for each timestep: (batch, seq_len, vocab_size)
        logits = self.classifier(h_seq2)

        # Innovation 2: Reliability-Conditioned Temperature-Scaled Softmax
        # T_t = 1.0 + alpha * (1.0 - R_t), where alpha = 0.5
        # Softens output probability distribution when tracking is unreliable
        T_t = 1.0 + 0.5 * (1.0 - reliability_seq)  # (batch, seq_len, 1)
        scaled_logits = logits / T_t

        # Log-softmax for CTC loss
        log_probs = F.log_softmax(scaled_logits, dim=-1)

        return log_probs
