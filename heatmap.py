"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Error Level Analysis (ELA) Heatmap
══════════════════════════════════════════════════════════════════════════════

Uses the same forensic technique as professional fact-checkers (Bellingcat):
Error Level Analysis detects JPEG re-save artifacts invisible to the naked eye
but which reveal exactly where an image has been locally edited or composited.

Method:
  1. Re-save the image at a known JPEG quality (90%)
  2. Compute the pixel-difference between original and re-saved
  3. Amplify the diff ×15 — edited regions retain high error, authentic
     regions converge toward uniform low error after re-compression
  4. Overlay a red (high ELA = suspicious) / green (low ELA = authentic)
     heatmap on the original image

Zero API cost — runs entirely with OpenCV and Pillow.
══════════════════════════════════════════════════════════════════════════════
"""

import io
import numpy as np
from typing import Dict, Any
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import logging
logger = logging.getLogger("trustcheck.heatmap")


def generate_heatmap(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run ELA (Error Level Analysis) on the image.

    Returns:
        dict with: heatmap_image_bytes, grid_scores, overall_assessment,
                   hotspots, ela_max, ela_mean, method
    """
    try:
        return _run_ela(image_bytes)
    except Exception as e:
        logger.error(f"ELA failed: {e}")
        return {
            "heatmap_image_bytes": None,
            "grid_scores": [[0.5] * 3 for _ in range(3)],
            "overall_assessment": f"ELA analysis failed: {e}",
            "hotspots": [],
            "ela_max": 0.0,
            "ela_mean": 0.0,
            "method": "ela_failed",
        }


def _run_ela(image_bytes: bytes) -> Dict[str, Any]:
    """Core ELA computation."""
    # ── Load original ────────────────────────────────────────────
    orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # ── Re-save at known quality and reload ──────────────────────
    buf = io.BytesIO()
    orig.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")

    # ── Compute pixel-level difference ───────────────────────────
    orig_arr  = np.array(orig,     dtype=np.float32)
    rsav_arr  = np.array(resaved,  dtype=np.float32)
    diff      = np.abs(orig_arr - rsav_arr)          # shape (H, W, 3)
    ela_map   = diff.max(axis=2)                     # collapse channels → (H, W)

    # Amplify so small differences become visible
    AMPLIFY   = 15
    ela_amp   = np.clip(ela_map * AMPLIFY, 0, 255)
    ela_norm  = ela_amp / 255.0                      # 0-1

    # ── Compute 3×3 grid scores ──────────────────────────────────
    H, W = ela_norm.shape
    grid_scores = []
    for r in range(3):
        row = []
        for c in range(3):
            rh = slice(r * H // 3, (r + 1) * H // 3)
            cw = slice(c * W // 3, (c + 1) * W // 3)
            cell_mean = float(ela_norm[rh, cw].mean())
            row.append(round(cell_mean, 3))
        grid_scores.append(row)

    ela_max  = float(ela_norm.max())
    ela_mean = float(ela_norm.mean())

    # ── Find hot-spots (cells > mean + 1.5 stddev) ───────────────
    flat    = [grid_scores[r][c] for r in range(3) for c in range(3)]
    mn, sd  = np.mean(flat), np.std(flat)
    labels  = [
        ["Top-Left",    "Top-Center",    "Top-Right"   ],
        ["Mid-Left",    "Mid-Center",    "Mid-Right"   ],
        ["Bot-Left",    "Bot-Center",    "Bot-Right"   ],
    ]
    hotspots = []
    for r in range(3):
        for c in range(3):
            score = grid_scores[r][c]
            if score > mn + 1.5 * sd and score > 0.1:
                hotspots.append(
                    f"{labels[r][c]} — ELA score {score:.0%} "
                    f"(JPEG re-save artifacts detected)"
                )

    # ── Assess overall ───────────────────────────────────────────
    if ela_mean < 0.04:
        overall = (
            "ELA is uniform and low — image appears to be an original capture "
            "with no detectable local editing."
        )
    elif ela_mean < 0.10:
        overall = (
            f"Moderate ELA signal (mean={ela_mean:.1%}). "
            "Slight editing artifacts detected; may be a lightly processed image."
        )
    else:
        overall = (
            f"High ELA signal (mean={ela_mean:.1%}, max={ela_max:.1%}). "
            "Strong JPEG re-save inconsistencies indicate region-level editing or compositing."
        )

    # ── Render overlay ───────────────────────────────────────────
    heatmap_bytes = _render_ela_overlay(orig, ela_norm, grid_scores, labels)

    return {
        "heatmap_image_bytes": heatmap_bytes,
        "grid_scores":         grid_scores,
        "overall_assessment":  overall,
        "hotspots":            hotspots,
        "ela_max":             round(ela_max, 4),
        "ela_mean":            round(ela_mean, 4),
        "method":              "ela_local",
    }


def _render_ela_overlay(
    orig: Image.Image,
    ela_norm: np.ndarray,
    grid_scores: list,
    labels: list,
) -> bytes:
    """Render ELA heatmap overlay on original image."""
    img_arr = np.array(orig)
    H, W    = ela_norm.shape

    cmap = LinearSegmentedColormap.from_list(
        "ela_cmap",
        [(0.0, "#00C853"), (0.3, "#FFD600"), (0.6, "#FF9100"), (1.0, "#FF1744")],
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=110)
    fig.patch.set_facecolor("#0E1117")

    # Left — original
    axes[0].imshow(img_arr)
    axes[0].set_title("Original Image", color="#FAFAFA", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Right — ELA overlay
    axes[1].imshow(img_arr)
    axes[1].imshow(ela_norm, cmap=cmap, alpha=0.55, vmin=0, vmax=1)

    # Grid lines
    for i in range(1, 3):
        axes[1].axhline(y=H * i / 3, color="white", linewidth=0.8, alpha=0.4)
        axes[1].axvline(x=W * i / 3, color="white", linewidth=0.8, alpha=0.4)

    # Score labels
    for r in range(3):
        for c in range(3):
            score = grid_scores[r][c]
            cy = H * (r + 0.5) / 3
            cx = W * (c + 0.5) / 3
            color = "#FF1744" if score > 0.15 else "#FFD600" if score > 0.07 else "#00C853"
            axes[1].text(
                cx, cy, f"{score:.0%}",
                ha="center", va="center", fontsize=13, fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=color, alpha=0.85),
            )

    axes[1].set_title("ELA Forensic Heatmap", color="#FAFAFA", fontsize=11, fontweight="bold")
    axes[1].axis("off")

    fig.suptitle(
        "Error Level Analysis — Red = editing artifacts · Green = original pixels",
        color="#B0BEC5", fontsize=9, y=0.02,
    )
    plt.tight_layout(rect=[0, 0.04, 1, 1])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#0E1117", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
