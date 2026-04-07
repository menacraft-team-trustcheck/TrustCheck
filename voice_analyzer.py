"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Voice/Audio Authenticity Analyzer (v4.0)
Enhanced with Pyannote + Resemblyzer for Superior Voice Detection
══════════════════════════════════════════════════════════════════════════════
"""

import io
import logging
import numpy as np
import tempfile
import os
from typing import Dict, Any, Tuple

logger = logging.getLogger("trustcheck.voice")

# ─────────────────────────────────────────────────────────────
# PYANNOTE & RESEMBLYZER INITIALIZATION
# ─────────────────────────────────────────────────────────────

PYANNOTE_AVAILABLE = False
RESEMBLYZER_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    from pyannote.audio.pipelines import VoiceActivityDetection
    PYANNOTE_AVAILABLE = True
    logger.info("✓ Pyannote-audio loaded successfully")
except ImportError:
    logger.warning("⚠ Pyannote-audio not installed. Install with: pip install pyannote.audio")

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMBLYZER_AVAILABLE = True
    logger.info("✓ Resemblyzer loaded successfully")
except ImportError:
    logger.warning("⚠ Resemblyzer not installed. Install with: pip install resemblyzer")

# ─────────────────────────────────────────────────────────────
# PYANNOTE VOICE ACTIVITY DETECTION
# ─────────────────────────────────────────────────────────────

_pyannote_vad_cache = None

def _get_pyannote_vad():
    """Lazy load Pyannote VAD pipeline."""
    global _pyannote_vad_cache
    if _pyannote_vad_cache is None and PYANNOTE_AVAILABLE:
        try:
            from pyannote.audio.pipelines import VoiceActivityDetection
            _pyannote_vad_cache = VoiceActivityDetection(task="voice-activity-detection")
            logger.info("✓ Pyannote VAD pipeline loaded")
        except Exception as e:
            logger.warning(f"Failed to load Pyannote VAD: {e}")
            return None
    return _pyannote_vad_cache

# ─────────────────────────────────────────────────────────────
# RESEMBLYZER VOICE ENCODING
# ─────────────────────────────────────────────────────────────

_encoder_cache = None

def _get_voice_encoder():
    """Lazy load Resemblyzer voice encoder."""
    global _encoder_cache
    if _encoder_cache is None and RESEMBLYZER_AVAILABLE:
        try:
            from resemblyzer import VoiceEncoder
            _encoder_cache = VoiceEncoder()
            logger.info("✓ Resemblyzer voice encoder loaded")
        except Exception as e:
            logger.warning(f"Failed to load Resemblyzer: {e}")
            return None
    return _encoder_cache

# ─────────────────────────────────────────────────────────────
# ADVANCED VOICE ACTIVITY DETECTION (Pyannote)
# ─────────────────────────────────────────────────────────────

def _detect_voice_segments(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """Detect voice activity segments using Pyannote."""
    result = {
        "has_voice": False,
        "voice_percentage": 0.0,
        "num_speech_segments": 0,
        "speech_gaps": 0,
        "unnatural_silence": False,
        "segments": []
    }
    
    if not PYANNOTE_AVAILABLE:
        return result
    
    try:
        from pyannote.audio.pipelines import VoiceActivityDetection
        vad = _get_pyannote_vad()
        if vad is None:
            return result
        
        # Create temp file for pyannote
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            import soundfile as sf
            sf.write(tmp.name, y, sr)
            temp_path = tmp.name
        
        try:
            # Run VAD pipeline
            vad_output = vad({"audio": temp_path, "sample_rate": sr})
            
            # Process segments
            speech_frames = 0
            for segment in vad_output:
                start, end = segment.start, segment.end
                duration = end - start
                result["segments"].append({"start": start, "end": end, "duration": duration})
                speech_frames += duration
                result["num_speech_segments"] += 1
            
            total_duration = len(y) / sr
            result["voice_percentage"] = round((speech_frames / total_duration * 100) if total_duration > 0 else 0, 2)
            result["has_voice"] = result["voice_percentage"] > 10.0
            
            # Detect unnatural silence patterns (AI signature)
            gaps_between_segments = []
            sorted_segments = sorted(result["segments"], key=lambda x: x["start"])
            for i in range(len(sorted_segments) - 1):
                gap = sorted_segments[i+1]["start"] - sorted_segments[i]["end"]
                if gap > 0.3:
                    gaps_between_segments.append(gap)
            
            result["speech_gaps"] = len(gaps_between_segments)
            if gaps_between_segments and np.mean(gaps_between_segments) < 0.1:
                result["unnatural_silence"] = True
                
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    except Exception as e:
        logger.debug(f"Pyannote VAD error: {e}")
    
    return result

# ─────────────────────────────────────────────────────────────
# SPEAKER EMBEDDING & DEEPFAKE DETECTION (Resemblyzer)
# ─────────────────────────────────────────────────────────────

def _analyze_speaker_embedding(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """Analyze speaker using Resemblyzer embeddings."""
    result = {
        "embedding_available": False,
        "voice_stability": 0.0,
        "embedding_variance": 0.0,
        "is_likely_deepfake": False,
        "deepfake_confidence": 0.0
    }
    
    if not RESEMBLYZER_AVAILABLE:
        return result
    
    try:
        from resemblyzer import preprocess_wav
        encoder = _get_voice_encoder()
        if encoder is None:
            return result
        
        # Preprocess audio for resemblyzer
        wav = preprocess_wav(y, source_sr=sr)
        
        # Split audio into chunks for embedding analysis
        chunk_size = sr * 2
        chunks = [wav[i:i+chunk_size] for i in range(0, len(wav), chunk_size) if len(wav[i:i+chunk_size]) > sr]
        
        if len(chunks) < 2:
            return result
        
        # Generate embeddings for each chunk
        embeddings = []
        for chunk in chunks:
            try:
                embed = encoder.embed_utterance(chunk)
                embeddings.append(embed)
            except:
                continue
        
        if len(embeddings) > 1:
            result["embedding_available"] = True
            
            # Calculate variance in embeddings (low = AI, high = natural)
            embed_array = np.array(embeddings)
            embedding_variance = np.mean(np.std(embed_array, axis=0))
            result["embedding_variance"] = round(float(embedding_variance), 4)
            
            # Calculate consistency across chunks
            embed_distances = []
            for i in range(len(embeddings) - 1):
                dist = float(np.linalg.norm(embeddings[i] - embeddings[i+1]))
                embed_distances.append(dist)
            
            voice_stability = round(float(np.mean(embed_distances)), 4) if embed_distances else 0.0
            result["voice_stability"] = voice_stability
            
            # Deepfake detection: extremely consistent embeddings = AI
            if embedding_variance < 0.08:
                result["is_likely_deepfake"] = True
                result["deepfake_confidence"] = min(0.95, (0.08 - embedding_variance) / 0.08)
    
    except Exception as e:
        logger.debug(f"Resemblyzer error: {e}")
    
    return result

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
# SCORING ENGINE WITH ADVANCED DETECTION
# ─────────────────────────────────────────────────────────────

def _compute_ai_score(features: Dict[str, Any], vad_results: Dict[str, Any] = None, 
                     embedding_results: Dict[str, Any] = None) -> Dict[str, Any]:
    """Expert-weighted scoring to detect high-fidelity Neural TTS."""
    evidence = []
    flags = []
    scores = []
    
    if vad_results is None:
        vad_results = {}
    if embedding_results is None:
        embedding_results = {}

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
    
    # F. PYANNOTE VAD SIGNALS (Advanced Voice Activity Detection)
    if vad_results:
        if not vad_results.get("has_voice"):
            flags.append("No voice activity detected")
            scores.append(0.65)
        elif vad_results.get("unnatural_silence"):
            flags.append("Unnatural silence patterns (AI signature)")
            scores.append(0.80)
        elif vad_results.get("voice_percentage", 0) > 90:
            evidence.append("Continuous natural speech")
            scores.append(0.05)
    
    # G. RESEMBLYZER DEEPFAKE DETECTION
    if embedding_results and embedding_results.get("embedding_available"):
        if embedding_results.get("is_likely_deepfake"):
            confidence = embedding_results.get("deepfake_confidence", 0)
            flags.append(f"Deepfake signature detected ({confidence:.0%})")
            scores.append(0.88)
        elif embedding_results.get("voice_stability", 0) > 0.15:
            evidence.append("Natural voice variation across utterances")
            scores.append(0.08)

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
        
        # Advanced detection with Pyannote & Resemblyzer
        vad_results = _detect_voice_segments(y, sr)
        embedding_results = _analyze_speaker_embedding(y, sr)
        
        scoring = _compute_ai_score(features, vad_results, embedding_results)
        
        # Enhanced interpretation
        interp = f"Voice analysis verdict: {scoring['verdict'].replace('_', ' ').title()} ({scoring['ai_score']:.0%}). "
        if scoring["flags"]: interp += f"Key forensic signals: {', '.join(scoring['flags'][:2])}."
        else: interp += "No suspicious acoustic signatures detected."

        return {
            **scoring,
            "details": interp,
            "features": features,
            "vad_analysis": vad_results,
            "embedding_analysis": embedding_results,
            "interpretation": interp,
            "model_used": "librosa_forensics_v3.0",
            "sample_rate": sr
        }
    except Exception as e:
        return {"verdict": "error", "details": str(e), "ai_score": 0.0, "flags": [], "evidence": [], "features": {}}


def preload_models() -> None:
    """Pre-load optional heavy audio models (Pyannote, Resemblyzer).

    Call this from the FastAPI startup event to avoid cold-start latency
    on the first audio request.
    """
    try:
        _get_pyannote_vad()
    except Exception:
        pass

    try:
        _get_voice_encoder()
    except Exception:
        pass
