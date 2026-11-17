"""
=============================================================================
RACER-X: Official IEEE Flowchart & Pipeline Diagram Generator
Department of AI & DS, Vel Tech R&D Institute of Science and Technology
=============================================================================
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_flowchart(output_path="figures/racerx_flowchart.png"):
    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica']
    })

    # Color Palette (Professional Modern IEEE Palette)
    c_blue   = "#005A9C"  # Input / Extraction
    c_teal   = "#008080"  # Kinematics / Attention
    c_amber  = "#D97706"  # Gating / Reliability
    c_purple = "#6B21A8"  # Causal Recurrent Core
    c_green  = "#15803D"  # Decoder & Real-Time Output
    c_bg_box = "#F8FAFC"  # Box fill background
    c_border = "#334155"  # Edge color

    # Helper function to draw rounded boxes
    def draw_box(x, y, w, h, title, subtitle, fill_c, border_c, title_c="#FFFFFF", sub_c="#334155"):
        # Header rect
        hh = h * 0.38
        header = patches.FancyBboxPatch(
            (x, y + h - hh), w, hh,
            boxstyle="round,pad=0.2,rounding_size=1.5",
            facecolor=fill_c, edgecolor=border_c, linewidth=1.2
        )
        ax.add_patch(header)
        # Body rect
        body = patches.FancyBboxPatch(
            (x, y), w, h - hh,
            boxstyle="round,pad=0.2,rounding_size=1.5",
            facecolor=c_bg_box, edgecolor=border_c, linewidth=1.2
        )
        ax.add_patch(body)

        # Header Title
        ax.text(x + w/2, y + h - hh/2, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color=title_c)
        # Body Subtitle
        ax.text(x + w/2, y + (h - hh)/2, subtitle, ha='center', va='center',
                fontsize=7.2, color=sub_c, multialignment='center')

    # Helper function to draw arrows
    def draw_arrow(x1, y1, x2, y2, label="", color="#334155", lw=1.3):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=11)
        )
        if label:
            ax.text((x1 + x2)/2, (y1 + y2)/2 + 1.8, label, ha='center', va='bottom',
                    fontsize=6.8, fontweight='bold', color=color)

    # -------------------------------------------------------------
    # STAGE 1: Video Ingestion & Landmark Extraction
    # -------------------------------------------------------------
    draw_box(2, 68, 17, 26, "1. Video Input", "WebRTC Interceptor\nContinuous Stream $I_t$\n(15-30 FPS Web Video)", c_blue, c_border)
    draw_arrow(19, 81, 23, 81, "Frame")

    draw_box(23, 68, 20, 26, "2. MediaPipe Holistic", "75 3D Keypoints $(P_t)$\nPose (9), Face (22), Hands (42)\nAnatomical Mid-Shoulder Norm", c_blue, c_border)
    draw_arrow(43, 81, 48, 81, "Normalized $\\hat{P}_t$")

    # -------------------------------------------------------------
    # STAGE 2: Dual Geometric & Spatial Stream (Branching)
    # -------------------------------------------------------------
    # Top Branch: Differential Kinematics
    draw_box(48, 77, 23, 21, "3A. Frenet Kinematics", "Discrete Curvature $\\kappa_t$\nInstantaneous Torsion $\\tau_t$\nSE(3) Rotation Invariant", c_teal, c_border)
    
    # Bottom Branch: Bilateral Attention
    draw_box(48, 51, 23, 21, "3B. Bilateral Attention", "Cross-Hand Context $S_t$\nDominant ($P_{RH}$) vs Base ($P_{LH}$)\nSpatial Dot-Product Attention", c_teal, c_border)

    # -------------------------------------------------------------
    # STAGE 3: Reliability & Agreement Gating
    # -------------------------------------------------------------
    draw_box(76, 64, 22, 28, "4. Adaptive Gating", "Tracking Reliability $R_t$\nSpatial Agreement $A_t$\n$g_t = \\sigma(W_g x + \\alpha_R R_t + \\alpha_A A_t)$\nFreezes on Blur & Occlusion", c_amber, c_border)

    # Connect dual branches to Gating
    draw_arrow(71, 87, 76, 80, "$M_t, \\kappa_t, \\tau_t$")
    draw_arrow(71, 61, 76, 74, "$S_t$")

    # -------------------------------------------------------------
    # STAGE 4: Causal Recurrent State Updating (Lower Deck)
    # -------------------------------------------------------------
    draw_box(74, 10, 24, 30, "5. RACER Causal Cell", "Candidate State $\\tilde{H}_t = \\tanh(...)$\n$H_t = g_t \\odot \\tilde{H}_t + (1 - g_t) \\odot H_{t-1}$\nPhysics Loss $\\mathcal{L}_{\\text{physics}}$ Penalty\nPreserves Uncorrupted Memory", c_purple, c_border)

    # Arrow from Gating down to Recurrent Core
    draw_arrow(87, 64, 87, 40, "Dynamic Gate $g_t$")

    # Recurrent loopback self-arrow
    arc = patches.Arc((74, 25), 6, 12, angle=0, theta1=90, theta2=270, color=c_purple, lw=1.3)
    ax.add_patch(arc)
    ax.annotate("", xy=(74, 31), xytext=(72, 25),
                arrowprops=dict(arrowstyle="-|>", color=c_purple, lw=1.3, mutation_scale=9))
    ax.text(68, 25, "State $H_{t-1}$", fontsize=6.8, color=c_purple, ha='center', va='center')

    # -------------------------------------------------------------
    # STAGE 5: Bayesian Decoding & Language Refinement
    # -------------------------------------------------------------
    draw_box(38, 10, 26, 30, "6. Bayesian CTC Decoder", "Prior Discounted Search:\n$\\log P_{\\text{bal}} = \\log P_{\\text{CTC}} - \\beta \\log P_{\\text{prior}}$\n2,748 Indian Sign Vocabulary\nMitigates Class Frequency Bias", c_green, c_border)
    draw_arrow(74, 25, 64, 25, "Hidden State $H_t$")

    # -------------------------------------------------------------
    # STAGE 6: Real-Time Assistive Output (Google Meet)
    # -------------------------------------------------------------
    draw_box(2, 10, 26, 30, "7. Real-Time Assistive UI", "Google Meet / Zoom WebRTC Integration\nDOM Live Subtitles Overlay\nSynchronized Speech Voice (TTS)\nLatency: 24.3 ms (~41.2 FPS)", c_green, c_border)
    draw_arrow(38, 25, 28, 25, "Decoded Gloss $Y$")

    # Top banner outline box
    rect_back = patches.Rectangle((1, 4), 98, 93, linewidth=1.0, edgecolor="#CBD5E1", facecolor='none', linestyle=':')
    ax.add_patch(rect_back)
    ax.text(50, 98, "RACER-X: END-TO-END CAUSAL SIGN LANGUAGE TRANSLATION PIPELINE",
            ha='center', va='center', fontsize=9.2, fontweight='bold', color="#002B49")

    plt.tight_layout()
    os.makedirs('figures', exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig('racerx_flowchart.png', dpi=300, bbox_inches='tight')
    print(f"[+] Flowchart generated successfully: {output_path}")

if __name__ == "__main__":
    draw_flowchart()
