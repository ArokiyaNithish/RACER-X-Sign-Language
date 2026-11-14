"""
=============================================================================
RACER-X: Official IEEE Experimental Robustness & Degradation Graph Generator
Department of AI & DS, Vel Tech R&D Institute of Science and Technology
=============================================================================
This script generates publication-quality IEEE format vector plots for:
  (a) Landmark Occlusion vs Word Error Rate (WER)
  (b) Spatial-Motion Dynamic Conflict vs Word Error Rate (WER)
"""

import os
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

def generate_ieee_graphs():
    # IEEE Publication Styling (Times Roman, matching IEEE Transactions)
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 8.5,
        'axes.labelsize': 8.5,
        'axes.titlesize': 9.0,
        'legend.fontsize': 7.5,
        'xtick.labelsize': 7.5,
        'ytick.labelsize': 7.5,
        'lines.linewidth': 1.6,
        'lines.markersize': 5.0,
        'grid.alpha': 0.35,
        'grid.linestyle': '--'
    })

    # -------------------------------------------------------------
    # 1. Single-Column IEEE Format (Fits perfectly in 1 column: 3.5 inches)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.4), dpi=300)

    # Plot (a): Landmark Occlusion vs WER
    occlusion_pct = [0, 10, 25, 40]
    base_occ = [38.5, 46.2, 55.8, 68.4]
    rel_occ = [27.6, 30.8, 34.5, 41.2]
    racerx_occ = [24.8, 26.9, 29.6, 32.3]

    ax1.plot(occlusion_pct, base_occ, 's--', color='#d9534f', label='Baseline (GRU)', markeredgecolor='black', markeredgewidth=0.4)
    ax1.plot(occlusion_pct, rel_occ, '^-.', color='#f0ad4e', label='Reliability Gate ($R_t$)', markeredgecolor='black', markeredgewidth=0.4)
    ax1.plot(occlusion_pct, racerx_occ, 'o-', color='#0275d8', label='RACER-X (Proposed)', markeredgecolor='black', markeredgewidth=0.4)

    ax1.set_xlabel('Landmark Occlusion Ratio (%)')
    ax1.set_ylabel('Word Error Rate (WER %)')
    ax1.set_title('(a) Landmark Occlusion')
    ax1.set_ylim(20, 75)
    ax1.set_xlim(-2, 42)
    ax1.grid(True)
    ax1.legend(loc='upper left', framealpha=0.92)

    # Plot (b): Spatial-Motion Dynamic Conflict vs WER
    conflict_labels = ['Clean', 'Jitter', 'Blur', 'Crossings']
    x_idx = np.arange(len(conflict_labels))
    base_conf = [38.5, 44.1, 52.7, 65.0]
    rel_conf = [27.6, 29.8, 33.1, 39.4]
    racerx_conf = [24.8, 26.6, 28.7, 31.0]

    ax2.plot(x_idx, base_conf, 's--', color='#d9534f', label='Baseline (GRU)', markeredgecolor='black', markeredgewidth=0.4)
    ax2.plot(x_idx, rel_conf, '^-.', color='#f0ad4e', label='Reliability Gate ($R_t$)', markeredgecolor='black', markeredgewidth=0.4)
    ax2.plot(x_idx, racerx_conf, 'o-', color='#0275d8', label='RACER-X (Proposed)', markeredgecolor='black', markeredgewidth=0.4)

    ax2.set_xticks(x_idx)
    ax2.set_xticklabels(conflict_labels)
    ax2.set_xlabel('Spatial-Motion Conflict Condition')
    ax2.set_ylabel('Word Error Rate (WER %)')
    ax2.set_title('(b) Dynamic Motion Conflict')
    ax2.set_ylim(20, 75)
    ax2.grid(True)
    ax2.legend(loc='upper left', framealpha=0.92)

    plt.tight_layout()

    os.makedirs('figures', exist_ok=True)
    out_png = os.path.join('figures', 'robustness_curves.png')
    out_pdf = os.path.join('figures', 'robustness_curves.pdf')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.savefig(out_pdf, bbox_inches='tight')
    # Save root copy as well for Overleaf convenience
    plt.savefig('robustness_curves.png', dpi=300, bbox_inches='tight')
    plt.savefig('robustness_curves.pdf', bbox_inches='tight')

    print(f"[+] IEEE Robustness Curve saved: {out_png}")
    print(f"[+] Vector PDF format saved:     {out_pdf}")

if __name__ == "__main__":
    generate_ieee_graphs()
