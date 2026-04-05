"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Voice/Audio Authenticity Analyzer (v3.0)
══════════════════════════════════════════════════════════════════════════════
"""

import io
import logging
import numpy as np
import tempfile
import os
from typing import Dict, Any

logger = logging.getLogger("trustcheck.voice")

# ─────────────────────────────────────────────────────────────
# AUDIO LOADING
# ─────────────────────────────────────────────────────────────

def _load_audio(audio_bytes: bytes, original_filename: str = "audio.tmp"):
    """Robust audio loading via temporary file to support multiple formats."""
    ext = os.path.splitext(original_filename)[1] or ".tmp"
    temp_path = None
    try:
        import librosa
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        y, sr = librosa.load(temp_path, sr=None, mono=True, duration=60)
        return y, sr, librosa
    except Exception as e:
        raise RuntimeError(f"Could not decode audio: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass

# ─────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_features(y: np.ndarray, sr: int, librosa) -> Dict[str, Any]:
    """Extract deep forensic signals from the audio waveform."""
    features = {}
    features["duration_sec"] = round(float(len(y) / sr), 2)

    # 1. Fundamental Frequency (F0) & Jitter
    try:
        f0, voiced_flag, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr)
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)] if f0 is not None else np.array([])
        if len(voiced_f0) > 10:
            features["pitch_cv"] = round(float(np.nanstd(voiced_f0) / (np.nanmean(voiced_f0) + 1e-6)), 4)
            f0_diffs = np.abs(np.diff(voiced_f0))
            features["jitter_local"] = round(float(np.mean(f0_diffs) / (np.mean(voiced_f0) + 1e-6)), 6)
        else:
            features["pitch_cv"] = features["jitter_local"] = None
    except:
        features["pitch_cv"] = features["jitter_local"] = None

    # 2. Energy Dynamics & Shimmer
    rms = librosa.feature.rms(y=y)[0]
    features["rms_cv"] = round(float(np.std(rms) / (np.mean(rms) + 1e-9)), 4)
    
    # 3. Silicon Silence (Neural Dithering check)
    abs_min_rms = float(np.min(rms)) if len(rms) > 0 else 1.0
    features["min_rms_db"] = round(float(20 * np.log10(abs_min_rms + 1e-12)), 2)

    # 4. Harmonicity & Noise
    try:
        autocorr = librosa.autocorrelate(y, max_size=int(sr/50))
        if len(autocorr) > 1:
            hnr_est = 10 * np.log10(np.max(autocorr[1:]) / (autocorr[0] - np.max(autocorr[1:]) + 1e-12))
            features["hnr_db"] = round(float(hnr_est), 2)
        else: features["hnr_db"] = None
    except: features["hnr_db"] = None

    # 5. Spectral Entropy & Flatness
    stft = np.abs(librosa.stft(y))
    features["spectral_flatness"] = round(float(librosa.feature.spectral_flatness(y=y).mean()), 6)
    try:
        entropy = librosa.feature.spectral_entropy(S=stft, sr=sr).mean()
        features["spectral_entropy"] = round(float(entropy), 6)
    except: features["spectral_entropy"] = None

    # 6. MFCC Variability
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    features["mfcc_variability"] = round(float(np.std(mfcc, axis=1).mean()), 4)

    # 7. Noise Stationarity
    try:
        silence_thresh = float(np.mean(rms)) * 0.1
        silent_mask = rms < silence_thresh
        if np.sum(silent_mask) > 10:
            quiet_rms = rms[silent_mask]
            features["noise_stationarity"] = round(float(np.std(quiet_rms) / (np.mean(quiet_rms) + 1e-9)), 4)
        else: features["noise_stationarity"] = None
    except: features["noise_stationarity"] = None

    return features

# ─────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────

def _compute_ai_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """Expert-weighted scoring to detect high-fidelity Neural TTS."""
    evidence = []
    flags = []
    scores = []

    # A. Pitch Perfection
    pcv = features.get("pitch_cv")
    if pcv is not None:
        if pcv < 0.055:
            flags.append(f"Robotic Pitch Stability (CV={pcv:.3f})")
            scores.append(0.98)
        elif pcv < 0.09:
            flags.append("Low pitch variance (Neural TTS signature)")
            scores.append(0.75)
        else:
            evidence.append("Natural prosodic variance")
            scores.append(0.10)

    # B. Silicon Silence (The Smoking Gun)
    min_db = features.get("min_rms_db", 0)
    if min_db < -80:
        flags.append(f"Detected 'Silicon Silence' ({min_db:.1f} dB)")
        scores.append(1.0)
        scores.append(1.0) # Double-force

    # C. Noise Stationarity
    nstat = features.get("noise_stationarity")
    if nstat is not None and nstat < 0.045:
        flags.append("Detected Stationary Digital Noisefloor")
        scores.append(0.93)

    # D. Harmonics (HNR)
    hnr = features.get("hnr_db")
    if hnr is not None and hnr > 23:
        flags.append(f"Unnaturally Clean Harmonic Signal ({hnr:.1f} dB)")
        scores.append(0.85)

    # E. Energy Stability
    rcv = features.get("rms_cv", 0)
    if rcv < 0.38:
        flags.append(f"Flat Energy Envelope (CV={rcv:.3f})")
        scores.append(0.90)

    # --- Synthesis ---
    base_score = float(np.mean(scores)) if scores else 0.5
    
    # Aggressive Scaler for 'Perfect' Signals
    perf_count = len(flags)
    if perf_count >= 3 or min_db < -85:
        ai_score = max(base_score, 0.985)
    else:
        ai_score = base_score

    ai_score = round(min(0.999, max(0.001, ai_score)), 4)
    
    if ai_score >= 0.70: verdict = "likely_ai_generated"
    elif ai_score >= 0.40: verdict = "inconclusive"
    else: verdict = "likely_authentic"

    return {
        "ai_score": ai_score,
        "verdict": verdict,
        "confidence": round(ai_score if ai_score > 0.5 else 1-ai_score, 2),
        "flags": flags,
        "evidence": evidence
    }

# ─────────────────────────────────────────────────────────────
# MAIN PUBLIC API
# ─────────────────────────────────────────────────────────────

def analyze_voice(audio_bytes: bytes, original_filename: str = "audio.tmp") -> Dict[str, Any]:
    """Analyzes voice for AI generation and manipulation."""
    try:
        y, sr, librosa = _load_audio(audio_bytes, original_filename)
        features = _extract_features(y, sr, librosa)
        scoring = _compute_ai_score(features)
        
        # Simple local interpretation
        interp = f"Voice analysis verdict: {scoring['verdict'].replace('_', ' ').title()} ({scoring['ai_score']:.0%}). "
        if scoring["flags"]: interp += f"Key forensic signals: {', '.join(scoring['flags'][:2])}."
        else: interp += "No suspicious acoustic signatures detected."

        return {
            **scoring,
            "details": interp,
            "features": features,
            "interpretation": interp,
            "model_used": "librosa_forensics_v3.0",
            "sample_rate": sr
        }
    except Exception as e:
        return {"verdict": "error", "details": str(e), "ai_score": 0.0, "flags": [], "evidence": [], "features": {}}
