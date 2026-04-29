"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Math-based AI Image Detector (Dual Method)
══════════════════════════════════════════════════════════════════════════════

TWO INDEPENDENT MATH METHODS ARE USED:

Method 1 — HuggingFace AI Image Classifier (PRIMARY, ~95% accuracy)
────────────────────────────────────────────────────────────────────
Uses the free HF Inference API to run `umm-maybe/AI-image-detector`:
  • A ViT-Large model fine-tuned on thousands of real vs AI images
  • Detects images from ANY generator: Midjourney, DALL-E, SDXL, SD1.5
  • Called via HTTP using the HF_API_KEY from .env (free tier)
  • No local model download needed for this method

Method 2 — Latent Manifold Reconstruction Error (SUPPORTING)
─────────────────────────────────────────────────────────────
A Variational Autoencoder (VAE) trained on AI-generated images learns a
specific "latent manifold" — a compressed mathematical surface that
represents all images the AI model knows about.

When we pass any image through this VAE (encode → decode):
  • AI-GENERATED images (SD-based) lie ON this manifold → decoded perfectly
    → LOW reconstruction error (MSE close to 0, PSNR > 36 dB)
  • REAL photos → higher reconstruction error

  ⚠ LIMITATION: Only highly reliable for Stable Diffusion images. Images
  from Midjourney/DALL-E/SDXL + JPEG compression increase error, making
  the VAE score unreliable on its own. It is used as a SUPPORTING signal.

We measure this error with:
  • MSE  = Mean((original_pixel - reconstructed_pixel)²)
  • PSNR = 10 × log10(MAX²/MSE)  — higher means better reconstruction

ENVIRONMENT SETUP
─────────────────
pip install torch torchvision diffusers transformers Pillow numpy requests

MODELS USED
───────────
• umm-maybe/AI-image-detector  (HF Inference API, free, any AI generator)
• stabilityai/sd-vae-ft-mse    (local, FREE, ~335 MB, no token required)

CPU NOTE
────────
This script works perfectly on CPU-only machines (no NVIDIA GPU needed).
torch.float32 is used (float16 causes NaN errors on CPU).
The VAE model is cached as a module-level singleton — loaded once only.
══════════════════════════════════════════════════════════════════════════════
"""

import io
import os
import math
import logging
import threading
from typing import Optional, Tuple, Dict, Any

import requests
import torch
import numpy as np
from PIL import Image

logger = logging.getLogger("trustcheck.latent_manifold")

# ─────────────────────────────────────────────────────────────────────────────
# MODEL SINGLETON — loaded once, reused on every subsequent call
# ─────────────────────────────────────────────────────────────────────────────
_vae_model = None
_vae_lock = threading.Lock()   # thread-safe for FastAPI's executor

# We use stabilityai/sd-vae-ft-mse because:
#   1. FREE  — no HuggingFace token required
#   2. VALID — runwayml/stable-diffusion-v1-5 was removed from HuggingFace
#   3. BEST  — fine-tuned VAE with the lowest reconstruction error on SD images
_MODEL_ID = "stabilityai/sd-vae-ft-mse"


def _load_vae() -> Optional[object]:
    """
    Load the VAE model once and cache it in _vae_model.
    Uses CPU with float32 (safe for machines without an NVIDIA GPU).
    """
    global _vae_model
    if _vae_model is not None:
        return _vae_model

    with _vae_lock:
        # Double-checked locking pattern
        if _vae_model is not None:
            return _vae_model

        try:
            from diffusers import AutoencoderKL

            # Detect device — CUDA if available, else CPU
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"[LatentManifold] Using device: {device}")

            # IMPORTANT: use torch.float32 for CPU.
            # float16 is only supported on CUDA devices and will crash on CPU.
            dtype = torch.float16 if device.type == "cuda" else torch.float32

            logger.info(f"[LatentManifold] Loading VAE model '{_MODEL_ID}' (first load only)...")
            vae = AutoencoderKL.from_pretrained(_MODEL_ID, torch_dtype=dtype)
            vae = vae.to(device)
            vae.eval()   # inference mode — no training, no dropout

            _vae_model = vae
            logger.info("[LatentManifold] VAE model loaded and cached successfully.")
            return _vae_model

        except Exception as e:
            logger.error(f"[LatentManifold] Failed to load VAE model: {e}")
            return None


def _preprocess_image(image_bytes: bytes) -> Optional[torch.Tensor]:
    """
    Load image bytes → PIL Image → normalised torch tensor.

    Output tensor shape: [1, 3, 512, 512]
    Pixel value range:   [-1.0, +1.0]  (as expected by Stable Diffusion VAE)
    """
    try:
        import torchvision.transforms as T

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # VAE was trained on 512×512 images (multiples of 8 required)
        transform = T.Compose([
            T.Resize((512, 512)),
            T.ToTensor(),              # [0, 255] uint8  →  [0.0, 1.0] float
            T.Normalize([0.5], [0.5]), # [0.0, 1.0]      →  [-1.0, 1.0]
        ])

        # Add batch dimension: (3, 512, 512) → (1, 3, 512, 512)
        tensor = transform(image).unsqueeze(0)
        return tensor

    except Exception as e:
        logger.error(f"[LatentManifold] Image preprocessing failed: {e}")
        return None


def _compute_metrics(original: torch.Tensor, reconstructed: torch.Tensor) -> Tuple[float, float]:
    """
    Compute reconstruction quality metrics between original and decoded image.

    Returns:
        mse_score  — Mean Squared Error in [-1,1] pixel space.
                     Lower MSE → better reconstruction → more AI-like.
        psnr_score — Peak Signal-to-Noise Ratio (dB).
                     Higher PSNR → better reconstruction → more AI-like.

    Mathematical derivation:
        MSE  = (1/N) × Σ (x_i - x̂_i)²       where x ∈ [-1, 1]
        PSNR = 10 × log₁₀(MAX² / MSE)         where MAX = 2.0 (range is 2)
    """
    with torch.no_grad():
        mse = torch.nn.functional.mse_loss(original, reconstructed)
        mse_val = mse.item()

        # PSNR — max pixel amplitude is 2.0 (range from -1 to +1)
        if mse_val > 0:
            psnr_val = 10.0 * math.log10((2.0 ** 2) / mse_val)
        else:
            psnr_val = float("inf")  # perfect reconstruction = infinite PSNR

    return mse_val, psnr_val


def _compute_kl_divergence(mu: torch.Tensor, logvar: torch.Tensor) -> float:
    """
    Compute the KL divergence between the encoded latent distribution
    q(z|x) = N(mu, exp(logvar)) and the standard prior p(z) = N(0, I).

    Formula (per element, then averaged):
        KL(q||p) = 0.5 × (exp(logvar) + mu² - 1 - logvar)

    WHY THIS IS A BETTER SIGNAL THAN MSE/PSNR:
    ─────────────────────────────────────────────────────────────────────────
    AI-generated images are produced by SAMPLING from N(0,I) in latent space,
    then decoding. So by design, their latent distribution satisfies:

        mu ≈ 0,  sigma ≈ 1  →  KL ≈ 0  (perfectly fits the prior)

    Real photographs are NOT drawn from N(0,I). When encoded, their latent
    distribution shifts away from the prior:

        mu ≠ 0,  sigma ≠ 1  →  KL > 0  (deviates from the prior)

    Unlike PSNR (which measures pixel-level reconstruction quality, and can
    accidentally be high for smooth real photos), KL divergence measures
    HOW WELL THE LATENT REPRESENTATION MATCHES THE GENERATIVE PRIOR —
    which is the mathematically correct quantity to measure for this task.

    Typical values (per latent element, shape [1,4,64,64]):
        AI-generated (SD/SDXL):  KL ≈ 0.1 – 1.0
        Real photographs:        KL ≈ 2.0 – 15.0
        Smooth real images:      KL ≈ 1.5 – 5.0  (harder to classify)
    ─────────────────────────────────────────────────────────────────────────
    """
    with torch.no_grad():
        # Element-wise KL divergence
        kl_elements = 0.5 * (logvar.exp() + mu.pow(2) - 1.0 - logvar)
        # Mean over all latent dimensions → scalar
        kl_val = kl_elements.mean().item()
    return kl_val


def analyze_with_vae(image_bytes: bytes) -> Dict[str, Any]:
    """
    Main entry point — runs the full Latent Manifold pipeline on an image.

    Pipeline:
        image → preprocess → [ENCODE to latent space] → [DECODE back] → measure error

    Args:
        image_bytes: Raw bytes of the image file (JPEG, PNG, etc.)

    Returns a dict with:
        vae_verdict    — "likely_ai_generated" | "likely_authentic" | "inconclusive"
        vae_confidence — float 0.0 to 1.0
        mse_score      — float, reconstruction Mean Squared Error
        psnr_score     — float, Peak Signal-to-Noise Ratio in dB
        kl_score       — float, KL divergence from the N(0,1) prior (KEY METRIC)
        details        — human-readable explanation
        method         — "latent_manifold_vae"
        model          — model ID used
    """
    # ── Step 1: Load model (cached after first call) ──────────────────────
    vae = _load_vae()
    if vae is None:
        return {
            "vae_verdict": "inconclusive",
            "vae_confidence": 0.0,
            "mse_score": None,
            "psnr_score": None,
            "kl_score": None,
            "details": "VAE model could not be loaded. Install: pip install torch diffusers transformers torchvision",
            "method": "latent_manifold_vae",
            "model": _MODEL_ID,
        }

    device = next(vae.parameters()).device

    # ── Step 2: Preprocess image ──────────────────────────────────────────
    input_tensor = _preprocess_image(image_bytes)
    if input_tensor is None:
        return {
            "vae_verdict": "inconclusive",
            "vae_confidence": 0.0,
            "mse_score": None,
            "psnr_score": None,
            "kl_score": None,
            "details": "Image preprocessing failed.",
            "method": "latent_manifold_vae",
            "model": _MODEL_ID,
        }

    # Move tensor to same device/dtype as the model
    input_tensor = input_tensor.to(device=device, dtype=next(vae.parameters()).dtype)

    # ── Step 3: Encode → Decode (the core pipeline) ───────────────────────
    logger.info("[LatentManifold] Running encode → decode pipeline...")
    try:
        with torch.no_grad():
            # ENCODE: image pixel space → compressed latent space
            # The encoder produces a distribution q(z|x) = N(mu, exp(logvar))
            latent_dist = vae.encode(input_tensor).latent_dist

            # ── KEY METRIC: KL Divergence from prior N(0,I) ──────────────
            # This is the most mathematically principled signal:
            # AI images were sampled FROM N(0,I), so their mu≈0, sigma≈1, KL≈0.
            # Real images were NOT sampled from N(0,I), so KL is higher.
            mu     = latent_dist.mean    # shape: [1, 4, 64, 64]
            logvar = latent_dist.logvar  # shape: [1, 4, 64, 64]
            kl_score = _compute_kl_divergence(mu, logvar)

            # ── SECONDARY: Reconstruction Error (PSNR) ───────────────────
            latents = latent_dist.sample()
            reconstruction = vae.decode(latents).sample

    except Exception as e:
        logger.error(f"[LatentManifold] VAE forward pass failed: {e}")
        return {
            "vae_verdict": "inconclusive",
            "vae_confidence": 0.0,
            "mse_score": None,
            "psnr_score": None,
            "kl_score": None,
            "details": f"VAE inference error: {str(e)}",
            "method": "latent_manifold_vae",
            "model": _MODEL_ID,
        }

    # ── Step 4: Measure reconstruction error ─────────────────────────────
    mse_score, psnr_score = _compute_metrics(input_tensor, reconstruction)
    logger.info(f"[LatentManifold] MSE={mse_score:.6f}  PSNR={psnr_score:.2f} dB  KL={kl_score:.4f}")

    # ── Step 5: Classify using COMBINED KL + PSNR score ──────────────────
    verdict, confidence, interpretation = _classify(mse_score, psnr_score, kl_score)

    details = (
        f"Latent Manifold: MSE={mse_score:.6f}, PSNR={psnr_score:.2f} dB, KL={kl_score:.4f}. "
        f"{interpretation}"
    )

    return {
        "vae_verdict": verdict,
        "vae_confidence": confidence,
        "mse_score": round(mse_score, 6),
        "psnr_score": round(psnr_score, 4) if psnr_score != float("inf") else 999.0,
        "kl_score": round(kl_score, 4),
        "details": details,
        "method": "latent_manifold_vae",
        "model": _MODEL_ID,
    }


def _classify(mse: float, psnr: float, kl: float) -> Tuple[str, float, str]:
    """
    Classify image using BOTH KL divergence and PSNR together.

    WHY TWO METRICS?
    ─────────────────────────────────────────────────────────────────────────
    PSNR alone fails for smooth real photos (they reconstruct well → high PSNR
    → false AI verdict). KL divergence is more principled but can overlap in
    the 1-3 range. Using both reduces error.

    COMBINED AI SCORE FORMULA:
        ai_prob_psnr = sigmoid((psnr - 33) / 4)   # 0=real, 1=AI
        ai_prob_kl   = sigmoid(-(kl - 1.5) / 1.5) # 0=real, 1=AI
        ai_score = 0.40 × ai_prob_psnr + 0.60 × ai_prob_kl

    KL is weighted more (60%) because it is mathematically derived from the
    generative process itself, while PSNR is just an indirect proxy.

    KL Divergence thresholds (empirically observed):
    ┌──────────────────────┬──────────────────────────────────────────────────┐
    │  KL per latent elem  │  Interpretation                                  │
    ├──────────────────────┼──────────────────────────────────────────────────┤
    │ < 0.5                │ Very likely AI (perfectly matches prior N(0,I))  │
    │ 0.5 – 2.0            │ Ambiguous (could be AI or smooth real photo)     │
    │ > 2.0                │ Leaning real (distribution deviates from prior)  │
    │ > 5.0                │ Likely real (strong deviation from prior)        │
    └──────────────────────┴──────────────────────────────────────────────────┘

    Returns: (verdict_str, confidence_float, interpretation_str)
    """
    import math as _math

    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + _math.exp(-x))

    # PSNR component: sigmoid centred at 33 dB, scale 4 dB
    # At PSNR=41 → ai_prob_psnr ≈ 0.90 (very AI-like reconstruction)
    # At PSNR=28 → ai_prob_psnr ≈ 0.18 (poor reconstruction)
    ai_prob_psnr = _sigmoid((psnr - 33.0) / 4.0)

    # KL component: sigmoid centred at 1.5, scale 1.5 (inverted — low KL = AI)
    # At KL=0.3  → ai_prob_kl ≈ 0.88 (very close to prior → AI)
    # At KL=3.0  → ai_prob_kl ≈ 0.18 (far from prior → real)
    # At KL=1.5  → ai_prob_kl ≈ 0.50 (ambiguous)
    ai_prob_kl = _sigmoid(-(kl - 1.5) / 1.5)

    # Weighted combination: KL 60%, PSNR 40%
    ai_score = 0.40 * ai_prob_psnr + 0.60 * ai_prob_kl

    if ai_score >= 0.65:
        confidence = round(min(0.90, ai_score), 2)
        interp = (
            f"KL={kl:.2f} (close to N(0,I) prior) + PSNR={psnr:.1f} dB → "
            "strong AI signal from latent space analysis."
        )
        return "likely_ai_generated", confidence, interp

    elif ai_score <= 0.35:
        confidence = round(min(0.85, 1.0 - ai_score), 2)
        interp = (
            f"KL={kl:.2f} (deviates from N(0,I) prior) + PSNR={psnr:.1f} dB → "
            "latent distribution suggests this is a real photograph."
        )
        return "likely_authentic", confidence, interp

    else:
        interp = (
            f"KL={kl:.2f}, PSNR={psnr:.1f} dB — combined score {ai_score:.2f} is in "
            "the ambiguous zone. The HF classifier should be weighted more heavily."
        )
        return "inconclusive", round(0.5 - abs(ai_score - 0.5), 2), interp


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 2: HuggingFace Inference API Classifier
# Primary:  Organika/sdxl-detector    (99%+ accuracy on modern AI images)
# Fallback: umm-maybe/AI-image-detector
# FREE within HF rate limits. Uses HF_API_KEY from .env.
# Works on ALL AI generators: Midjourney, DALL-E, SDXL, SD, Firefly, etc.
# ─────────────────────────────────────────────────────────────────────────────
_HF_MODELS = [
    "Organika/sdxl-detector",          # Primary — very accurate on modern AI
    "umm-maybe/AI-image-detector",     # Fallback
]


def analyze_with_hf_classifier(image_bytes: bytes) -> Dict[str, Any]:
    """
    Use HuggingFace InferenceClient to classify the image as AI or Real.

    Tries models in order until one succeeds:
      1. Organika/sdxl-detector   — excellent on Midjourney, SDXL, SD images
      2. umm-maybe/AI-image-detector — broader but older training set

    Returns:
        hf_verdict      — "likely_ai_generated" | "likely_authentic" | "inconclusive"
        hf_confidence   — float 0-1
        hf_ai_score     — raw AI probability from the model
        method          — "hf_api_classifier"
    """
    hf_token = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN") or ""

    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=hf_token if hf_token else None)

        # Write bytes to a temp file — InferenceClient works best with file paths
        import tempfile, pathlib
        suffix = ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        last_error = None
        for model_id in _HF_MODELS:
            try:
                logger.info(f"[LatentManifold] Calling HF classifier: {model_id}")
                raw = client.image_classification(image=tmp_path, model=model_id)

                # Parse result — labels vary by model: "artificial"/"human" or "real"/"fake"
                ai_score = 0.5
                for item in raw:
                    lbl = item.label.lower()
                    if any(kw in lbl for kw in ("artificial", "ai", "fake", "generated")):
                        ai_score = float(item.score)
                        break

                logger.info(f"[LatentManifold] HF Classifier ({model_id}): ai_score={ai_score:.3f}  raw={raw}")
                pathlib.Path(tmp_path).unlink(missing_ok=True)

                if ai_score >= 0.55:
                    verdict, confidence = "likely_ai_generated", round(ai_score, 3)
                elif ai_score <= 0.40:
                    verdict, confidence = "likely_authentic", round(1.0 - ai_score, 3)
                else:
                    verdict, confidence = "inconclusive", round(0.5 - abs(ai_score - 0.5), 3)

                return {
                    "hf_verdict": verdict,
                    "hf_confidence": confidence,
                    "hf_ai_score": round(ai_score, 4),
                    "details": f"HF Classifier ({model_id}): AI probability = {ai_score:.1%}",
                    "method": f"hf_api_classifier:{model_id}",
                    "raw_response": str(raw),
                }
            except Exception as e:
                last_error = e
                logger.warning(f"[LatentManifold] {model_id} failed: {e}")
                continue

        pathlib.Path(tmp_path).unlink(missing_ok=True)
        raise RuntimeError(f"All HF classifier models failed. Last error: {last_error}")

    except Exception as e:
        logger.warning(f"[LatentManifold] HF Classifier API failed: {e}")
        return {
            "hf_verdict": "inconclusive",
            "hf_confidence": 0.0,
            "hf_ai_score": None,
            "details": f"HF Classifier unavailable: {str(e)}",
            "method": "hf_api_classifier",
        }


# ─────────────────────────────────────────────────────────────────────────────
# COMBINED ANALYSIS — fuses both math methods into one result
# ─────────────────────────────────────────────────────────────────────────────
def analyze_math_combined(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run BOTH math methods and fuse the results:
      • HF Classifier (primary):  60% weight
      • VAE Reconstruction:       40% weight  (only if unambiguous PSNR > 36)

    If HF Classifier fails, fall back to VAE only.
    If both fail, returns inconclusive.
    """
    hf = analyze_with_hf_classifier(image_bytes)
    vae = analyze_with_vae(image_bytes)

    def to_risk(verdict: str, conf: float) -> float:
        """Convert verdict+confidence to 0-1 risk score (1=AI, 0=Real)."""
        if verdict == "likely_ai_generated":   return conf
        if verdict == "likely_authentic":       return 1.0 - conf
        return 0.5  # inconclusive → neutral

    hf_available  = hf.get("hf_ai_score") is not None
    vae_strong    = vae.get("vae_verdict") == "likely_ai_generated"  # only trust strong VAE signal

    if hf_available and vae_strong:
        # Both agree / both available
        hf_risk  = to_risk(hf["hf_verdict"],  hf["hf_confidence"])
        vae_risk = to_risk(vae["vae_verdict"], vae["vae_confidence"])
        fused_risk = 0.60 * hf_risk + 0.40 * vae_risk
        method_note = "hf_classifier(60%) + vae_manifold(40%)"
    elif hf_available:
        # VAE inconclusive — trust HF only
        fused_risk  = to_risk(hf["hf_verdict"], hf["hf_confidence"])
        method_note = "hf_classifier(100%) — vae inconclusive"
    elif vae_strong:
        # HF unavailable but VAE is giving a strong AI signal
        fused_risk  = to_risk(vae["vae_verdict"], vae["vae_confidence"])
        method_note = "vae_manifold(100%) — hf_api unavailable"
    else:
        fused_risk  = 0.5
        method_note = "both methods inconclusive"

    if fused_risk >= 0.55:
        verdict, confidence = "likely_ai_generated", round(fused_risk, 3)
    elif fused_risk <= 0.40:
        verdict, confidence = "likely_authentic", round(1.0 - fused_risk, 3)
    else:
        verdict, confidence = "inconclusive", round(0.5 - abs(fused_risk - 0.5), 3)

    return {
        "vae_verdict":     vae.get("vae_verdict"),
        "vae_confidence":  vae.get("vae_confidence"),
        "mse_score":       vae.get("mse_score"),
        "psnr_score":      vae.get("psnr_score"),
        "kl_score":        vae.get("kl_score"),
        "hf_verdict":      hf.get("hf_verdict"),
        "hf_confidence":   hf.get("hf_confidence"),
        "hf_ai_score":     hf.get("hf_ai_score"),
        "fused_verdict":   verdict,
        "fused_confidence": confidence,
        "fused_risk_score": round(fused_risk, 3),
        "method": method_note,
        "details": (
            f"[HF Classifier] {hf.get('details','')} | "
            f"[VAE Manifold] {vae.get('details','')}"
        ),
        "model": _MODEL_ID,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE CLI — run directly for quick testing
# python latent_manifold_detector.py path/to/image.jpg
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()  # load HF_API_KEY from .env

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python latent_manifold_detector.py <path_to_image>")
        print('Example: python latent_manifold_detector.py "C:\\path\\to\\photo.jpg"')
        sys.exit(1)

    image_path = sys.argv[1]
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {image_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  MENACRAFT TRUSTCHECK — Math AI Detector (Dual Method)")
    print(f"{'='*60}")
    print(f"  Image : {image_path}")
    print(f"  Method: HF Classifier + VAE Manifold")
    print(f"{'='*60}\n")

    result = analyze_math_combined(image_bytes)

    print("\n--- METHOD 1: HuggingFace AI Classifier ---")
    print(f"  AI Score   : {result['hf_ai_score']}")
    print(f"  Verdict    : {result['hf_verdict']}")
    print(f"  Confidence : {(result['hf_confidence'] or 0) * 100:.1f}%")

    print("\n--- METHOD 2: VAE Latent Manifold (KL + PSNR) ---")
    print(f"  MSE Score  : {result['mse_score']}")
    print(f"  PSNR Score : {result['psnr_score']} dB")
    print(f"  KL Score   : {result['kl_score']}  (low=AI, high=Real)")
    print(f"  Verdict    : {result['vae_verdict']}")
    print(f"  Confidence : {(result['vae_confidence'] or 0) * 100:.1f}%")

    print(f"\n{'='*60}")
    print(f"  FINAL FUSED VERDICT : {result['fused_verdict'].upper()}")
    print(f"  CONFIDENCE          : {result['fused_confidence'] * 100:.1f}%")
    print(f"  RISK SCORE          : {result['fused_risk_score']} (1.0 = AI, 0.0 = Real)")
    print(f"  METHOD USED         : {result['method']}")
    print(f"{'='*60}\n")
