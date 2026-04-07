"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Video Analysis Module
══════════════════════════════════════════════════════════════════════════════

Uses OpenCV to sample keyframes from uploaded videos, then scores each frame
for AI-generation likelihood via HuggingFace.  Generates a matplotlib risk
timeline chart and identifies the most suspicious frames.

Pipeline:
  1. OpenCV VideoCapture → extract frames at configurable intervals
  2. Each frame → HF AI-detection model (same as authenticity.py)
  3. Aggregate scores → risk timeline (matplotlib)
  4. Return structured report + chart image bytes
══════════════════════════════════════════════════════════════════════════════
"""

import io
import cv2
import numpy as np
import tempfile
import os
from typing import Dict, Any, List, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt

from authenticity import analyze_image_authenticity, compute_file_hash
from llm_router import encode_image_to_base64

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

DEFAULT_SAMPLE_INTERVAL = 2.0    # Sample one frame every N seconds
MAX_FRAMES_TO_ANALYZE = 20       # Cap total frames to avoid API overload
SUSPICIOUS_THRESHOLD = 0.6       # AI-score above this = suspicious


def extract_frames(
    video_bytes: bytes,
    interval_sec: float = DEFAULT_SAMPLE_INTERVAL,
    max_frames: int = MAX_FRAMES_TO_ANALYZE,
) -> List[Tuple[float, np.ndarray]]:
    """
    Extract frames from video bytes at the specified interval.

    Returns list of (timestamp_seconds, frame_ndarray) tuples.
    """
    # Write video bytes to a temp file for OpenCV
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.write(video_bytes)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    frames = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return frames

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        # Calculate frame indices to sample
        frame_interval = int(fps * interval_sec)
        if frame_interval < 1:
            frame_interval = 1

        frame_idx = 0
        while len(frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            timestamp = frame_idx / fps
            frames.append((timestamp, frame))
            frame_idx += frame_interval

        cap.release()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return frames


def frame_to_jpeg_bytes(frame: np.ndarray, quality: int = 85) -> bytes:
    """Encode an OpenCV frame (BGR ndarray) to JPEG bytes."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not success:
        return b""
    return buffer.tobytes()


def analyze_video(
    video_bytes: bytes,
    interval_sec: float = DEFAULT_SAMPLE_INTERVAL,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Full video analysis pipeline:
      1. Extract keyframes via OpenCV
      2. Score each frame for AI-generation
      3. Build risk timeline chart
      4. Identify suspicious keyframes

    Args:
        video_bytes: Raw video file bytes
        interval_sec: Seconds between sampled frames
        progress_callback: Optional callable(current, total) for progress bars

    Returns:
        dict with: overall_verdict, frame_scores, timeline_image_bytes,
                   suspicious_frames, total_frames, sha256
    """
    sha256 = compute_file_hash(video_bytes)

    # Step 1: Extract frames
    frames = extract_frames(video_bytes, interval_sec)
    if not frames:
        return {
            "overall_verdict": "error",
            "details": "Could not extract frames from the video. The file may be corrupted or in an unsupported format.",
            "frame_scores": [],
            "timeline_image_bytes": None,
            "suspicious_frames": [],
            "total_frames": 0,
            "sha256": sha256,
        }

    # Step 2: Score each frame (parallelized)
    frame_count = len(frames)
    frame_scores = [None] * frame_count
    suspicious_frames = []

    # Prepare JPEG bytes for frames
    frame_payloads = []  # list of (index, timestamp, jpeg_bytes)
    for i, (timestamp, frame) in enumerate(frames):
        if progress_callback:
            progress_callback(i + 1, frame_count)
        jpeg_bytes = frame_to_jpeg_bytes(frame)
        frame_payloads.append((i, timestamp, jpeg_bytes))

    # Run authenticity checks in a small thread pool to parallelize network/model calls
    from concurrent.futures import ThreadPoolExecutor, as_completed

    max_workers = min(4, max(1, frame_count))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {}
        for idx, timestamp, jpeg in frame_payloads:
            if not jpeg:
                # Mark error immediately
                frame_scores[idx] = {
                    "timestamp": timestamp,
                    "ai_score": 0.0,
                    "verdict": "error",
                    "frame_index": idx,
                }
                continue
            fut = executor.submit(analyze_image_authenticity, jpeg)
            future_to_index[fut] = (idx, timestamp, jpeg)

        for fut in as_completed(future_to_index):
            idx, timestamp, jpeg = future_to_index[fut]
            try:
                result = fut.result()
            except Exception:
                result = {"verdict": "error", "confidence": 0.0}

            ai_score = result.get("confidence", 0.0)
            if result.get("verdict") == "likely_authentic":
                ai_score = 1.0 - ai_score

            frame_entry = {
                "timestamp": timestamp,
                "ai_score": ai_score,
                "verdict": result.get("verdict", "inconclusive"),
                "frame_index": idx,
            }
            frame_scores[idx] = frame_entry

            if ai_score >= SUSPICIOUS_THRESHOLD:
                suspicious_frames.append({**frame_entry, "image_bytes": jpeg})

    # Step 3: Generate timeline chart
    timeline_bytes = _generate_risk_timeline(frame_scores)

    # Step 4: Compute overall verdict
    avg_ai_score = np.mean([f["ai_score"] for f in frame_scores]) if frame_scores else 0
    if avg_ai_score > 0.6:
        overall = "likely_ai_generated"
    elif avg_ai_score > 0.35:
        overall = "inconclusive"
    else:
        overall = "likely_authentic"

    return {
        "overall_verdict": overall,
        "average_ai_score": float(avg_ai_score),
        "details": f"Analyzed {len(frames)} frames. Average AI-score: {avg_ai_score:.1%}. "
                   f"Suspicious frames: {len(suspicious_frames)}/{len(frames)}.",
        "frame_scores": frame_scores,
        "timeline_image_bytes": timeline_bytes,
        "suspicious_frames": suspicious_frames,
        "total_frames": len(frames),
        "sha256": sha256,
    }


def _generate_risk_timeline(frame_scores: List[Dict]) -> bytes:
    """
    Create a matplotlib risk-timeline chart from frame scores.

    X-axis = timestamp (seconds), Y-axis = AI-generation risk score.
    Colour-coded: green (safe) → yellow (caution) → red (suspicious).

    Returns PNG image as bytes.
    """
    if not frame_scores:
        return b""

    timestamps = [f["timestamp"] for f in frame_scores]
    scores = [f["ai_score"] for f in frame_scores]

    fig, ax = plt.subplots(figsize=(12, 4), dpi=120)
    fig.patch.set_facecolor("#0E1117")
    ax.set_facecolor("#0E1117")

    # Colour each bar by risk level
    colors = []
    for s in scores:
        if s >= 0.65:
            colors.append("#FF1744")    # Red — high risk
        elif s >= 0.35:
            colors.append("#FF9100")    # Orange — medium
        else:
            colors.append("#00C853")    # Green — low risk

    ax.bar(timestamps, scores, width=max(1.0, timestamps[-1] / len(timestamps) * 0.8),
           color=colors, alpha=0.85, edgecolor="#1a1a2e", linewidth=0.5)

    # Threshold line
    ax.axhline(y=SUSPICIOUS_THRESHOLD, color="#FF1744", linestyle="--",
               alpha=0.5, linewidth=1, label=f"Suspicious Threshold ({SUSPICIOUS_THRESHOLD})")

    # Styling
    ax.set_xlabel("Time (seconds)", color="#FAFAFA", fontsize=11, fontweight="bold")
    ax.set_ylabel("AI-Generation Risk", color="#FAFAFA", fontsize=11, fontweight="bold")
    ax.set_title("Video Frame Risk Timeline", color="#FAFAFA", fontsize=14,
                 fontweight="bold", pad=12)
    ax.set_ylim(0, 1.05)
    ax.tick_params(colors="#AAAAAA")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#333333")
    ax.spines["left"].set_color("#333333")
    ax.legend(facecolor="#1a1a2e", edgecolor="#333333", labelcolor="#FAFAFA",
              fontsize=9)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#0E1117", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
