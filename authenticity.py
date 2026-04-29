"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE A: Content Authenticity
══════════════════════════════════════════════════════════════════════════════

Determines whether an image is AI-generated or has been digitally manipulated
using TWO independent detection methods fused together:

  Method 1 — Vision LLM Forensic Analysis (OpenRouter)
    • Sends image to a multimodal LLM with a detailed forensic prompt
    • Checks for anatomical errors, lighting inconsistencies, AI smoothing etc.
    • Weight: 60% of final confidence

  Method 2 — Latent Manifold Reconstruction Error (Math / VAE)
    • Passes image through Stable Diffusion VAE (encode → decode)
    • Measures MSE/PSNR reconstruction error
    • AI-generated images reconstruct perfectly (low MSE)
    • Real photos do not fit the AI manifold (high MSE)
    • Weight: 40% of final confidence
    • Model: stabilityai/sd-vae-ft-mse (FREE, ~335 MB, no token needed)

Returns a structured result dict with:
  - verdict: "likely_authentic" | "likely_ai_generated" | "inconclusive"
  - confidence: float 0-1
  - details: human-readable explanation
  - vae_analysis: sub-dict with MSE/PSNR scores from the math method
══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import re
import logging
from typing import Dict, Any
from llm_router import route_vision, route_text, encode_image_to_base64

logger = logging.getLogger("trustcheck.authenticity")

# Lazy-import the VAE detector so the app starts even if torch/diffusers are
# not yet installed (graceful degradation).
def _try_vae_analysis(image_bytes: bytes) -> Dict[str, Any] | None:
    """
    Run the combined math-based AI detector (HF Classifier + VAE Manifold).
    Returns None if unavailable (torch/diffusers not installed).
    """
    try:
        from latent_manifold_detector import analyze_math_combined
        return analyze_math_combined(image_bytes)
    except ImportError:
        logger.warning("[Authenticity] Math detector unavailable — torch/diffusers not installed.")
        return None
    except Exception as e:
        logger.warning(f"[Authenticity] Math detector failed: {e}")
        return None


def compute_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of the uploaded file for integrity verification."""
    return hashlib.sha256(file_bytes).hexdigest()


FORENSIC_PROMPT = """You are a Lead Digital Forensics Investigator at a top OSINT agency.
Your objective is to identify AI generation (Diffusion models, GANs) or digital manipulation.

### FORENSIC CHECKLIST (Analyze carefully):
1. **Micro-Texture Analysis**: Look for "AI-smoothness" - regions with suspiciously uniform noise or lack of natural film grain.
2. **Frequency Artifacts**: Check for any checkerboard patterns or strange tiling (common in early GANs).
3. **Anatomical/Structural Coherence**:
   - Hands: finger count, joints, merged skin.
   - Eyes: mismatched pupil shapes, asymmetric reflections.
   - Ears: geometry inconsistencies.
   - Background: impossible connections (e.g., a chair leg that doesn't reach the floor).
4. **Lighting & Global Consistency**:
   - Does every shadow align with a coherent light source?
   - Is the Depth of Field (DoF) natural, or are there abrupt sharp-to-blur transitions that make no sense?
   - Reflections: Do they show the correct objects in the scene?
5. **Semantic Logic**: Are there "impossible" objects (e.g., a hand coming out of a wall)?

### RESPONSE PROTOCOL:
1. First, perform a brief internal thought process on each point.
2. Then, provide the final forensic verdict in JSON format.

Output MUST be EXACTLY this JSON:
{
  "verdict": "likely_authentic" | "likely_ai_generated" | "inconclusive",
  "confidence": 0.0 to 1.0,
  "details": "A technical explanation focusing on specific forensic anomalies found.",
  "indicators_found": ["list", "of", "specific", "technical", "indicators"]
}"""


def analyze_image_authenticity(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run AI-generated image detection using two independent methods:
      1. Vision LLM forensic analysis (OpenRouter) — 60% weight
      2. Latent Manifold VAE reconstruction error (Math) — 40% weight

    If the Vision LLM is unavailable, falls back to Groq/DeepSeek text heuristic.
    If the VAE is unavailable (torch not installed), gracefully skips it.
    The two verdicts are fused into a single weighted confidence score.
    """
    sha256 = compute_file_hash(image_bytes)
    try:
        # ══ METHOD 1: Vision LLM Forensic Analysis (60% weight) ══════════
        logger.info("[Authenticity] Running Vision LLM forensic analysis...")
        llm_result = None
        image_b64 = encode_image_to_base64(image_bytes)
        vision_raw = route_vision(FORENSIC_PROMPT, image_b64)

        if vision_raw and not (isinstance(vision_raw, str) and vision_raw.startswith("[ERROR]")):
            llm_result = _parse_vision_response(vision_raw, sha256)

        if llm_result is None:
            # Soft fallback: text LLM
            logger.info("[Authenticity] Vision LLM failed, using text fallback...")
            fallback_prompt = (
                "You are a digital forensics expert. A user uploaded an image for analysis "
                "but we couldn't run vision-based detection. Based on general knowledge, "
                "what advice would you give for manually checking if an image is AI-generated? "
                "Reply with a brief 2-3 sentence practical guide."
            )
            fb = route_text(fallback_prompt)
            llm_result = {
                "verdict": "inconclusive",
                "confidence": 0.0,
                "details": (
                    f"Vision detection unavailable. Manual verification recommended. {fb}"
                    if isinstance(fb, str) and not fb.startswith("[ERROR]")
                    else "Automated detection unavailable. Please verify the image manually."
                ),
                "model_used": "fallback_llm",
                "sha256": sha256,
            }

        # ══ METHOD 2: Latent Manifold VAE Reconstruction Error (40% weight) ══
        logger.info("[Authenticity] Running Latent Manifold VAE analysis...")
        vae_result = _try_vae_analysis(image_bytes)

        # ══ FUSION: Combine both methods ═════════════════════════════════
        final = _fuse_results(llm_result, vae_result, sha256)
        return final

    except Exception as e:
        logger.error(f"[Authenticity] Pipeline crashed: {e}")
        return {
            "verdict": "inconclusive",
            "confidence": 0.0,
            "details": f"Forensic engine internal error: {str(e)}",
            "model_used": "none",
            "sha256": sha256,
        }


def _verdict_to_risk(verdict: str, confidence: float) -> float:
    """
    Convert a verdict+confidence pair into a unified 0-1 risk score.
    (1.0 = certainly AI-generated, 0.0 = certainly authentic)
    """
    if verdict == "likely_ai_generated":
        return confidence
    elif verdict == "likely_authentic":
        return 1.0 - confidence
    else:  # inconclusive
        return 0.5


def _fuse_results(
    llm: Dict[str, Any],
    vae: Dict[str, Any] | None,
    sha256: str,
) -> Dict[str, Any]:
    """
    Fuse Vision LLM (60%) and VAE math (40%) results into a single verdict.

    Fusion strategy:
      • The 'math' block already contains a pre-fused result from
        analyze_math_combined() (HF Classifier 60% + VAE 40%).
      • We fuse THAT math result (35% weight) with the Vision LLM (65%),
        giving us a three-signal final verdict:
          Vision LLM     65%
          HF Classifier  ~21%  (35% × 60%)
          VAE Manifold   ~14%  (35% × 40%)
      • If math block is unavailable, Vision LLM carries 100%.
    """
    LLM_WEIGHT  = 0.65
    MATH_WEIGHT = 0.35

    llm_risk = _verdict_to_risk(llm.get("verdict", "inconclusive"), float(llm.get("confidence", 0.5)))

    # The math block is from analyze_math_combined() — read its fused verdict
    math_verdict    = (vae or {}).get("fused_verdict")   or (vae or {}).get("vae_verdict")
    math_confidence = (vae or {}).get("fused_confidence") or (vae or {}).get("vae_confidence") or 0.5

    if vae is not None and math_verdict and math_verdict != "inconclusive":
        math_risk  = _verdict_to_risk(math_verdict, float(math_confidence))
        fused_risk = LLM_WEIGHT * llm_risk + MATH_WEIGHT * math_risk
        method_note = f"vision_llm(65%) + math_detector(35%) [{vae.get('method', 'combined')}]"
    else:
        # Math unavailable or inconclusive → Vision LLM only
        fused_risk  = llm_risk
        method_note = llm.get("model_used", "vision_llm")

    # Map fused risk score → final verdict + confidence
    if fused_risk >= 0.55:
        final_verdict = "likely_ai_generated"
        final_confidence = round(fused_risk, 3)
    elif fused_risk <= 0.40:
        final_verdict = "likely_authentic"
        final_confidence = round(1.0 - fused_risk, 3)
    else:
        final_verdict = "inconclusive"
        final_confidence = round(0.5 - abs(fused_risk - 0.5), 3)

    # Build detail string
    llm_details = llm.get("details", "")
    math_details = (
        f" | Math: HF={vae.get('hf_ai_score')} MSE={vae.get('mse_score')} PSNR={vae.get('psnr_score')} dB → {math_verdict}"
        if vae else " | Math Detector: unavailable"
    )

    return {
        "verdict": final_verdict,
        "confidence": final_confidence,
        "details": llm_details + math_details,
        "model_used": method_note,
        "sha256": sha256,
        "indicators": llm.get("indicators", []),
        # Expose raw sub-results for transparency
        "math_analysis": vae if vae else {"status": "unavailable"},
        "llm_risk_score": round(llm_risk, 3),
        "math_risk_score": round(
            _verdict_to_risk(math_verdict, float(math_confidence)), 3
        ) if vae and math_verdict != "inconclusive" else None,
        "fused_risk_score": round(fused_risk, 3),
    }


def _parse_vision_response(response: str, sha256: str) -> Dict[str, Any] | None:
    """Parse the vision LLM JSON response into a structured result."""
    text = response if isinstance(response, str) else str(response)

    # Try to extract JSON from the response
    json_match = re.search(r'\{[^{}]*"verdict"[^{}]*\}', text, re.DOTALL)
    if not json_match:
        # Try more aggressively
        json_match = re.search(r'\{.*?\}', text, re.DOTALL)

    if json_match:
        try:
            data = json.loads(json_match.group())
            verdict = data.get("verdict", "inconclusive")
            # Normalize verdict
            if verdict not in ("likely_authentic", "likely_ai_generated", "inconclusive"):
                if "authentic" in verdict.lower() or "real" in verdict.lower():
                    verdict = "likely_authentic"
                elif "ai" in verdict.lower() or "generated" in verdict.lower() or "fake" in verdict.lower():
                    verdict = "likely_ai_generated"
                else:
                    verdict = "inconclusive"

            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            return {
                "verdict": verdict,
                "confidence": confidence,
                "details": data.get("details", "Analysis completed."),
                "model_used": "vision_llm",
                "sha256": sha256,
                "indicators": data.get("indicators_found", []),
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # If JSON parsing failed, try to interpret the text directly
    text_lower = text.lower()
    if any(kw in text_lower for kw in ("ai-generated", "ai generated", "artificially", "synthetic", "generated by")):
        return {
            "verdict": "likely_ai_generated",
            "confidence": 0.7,
            "details": text[:500],
            "model_used": "vision_llm",
            "sha256": sha256,
        }
    elif any(kw in text_lower for kw in ("authentic", "genuine", "real photograph", "not ai")):
        return {
            "verdict": "likely_authentic",
            "confidence": 0.7,
            "details": text[:500],
            "model_used": "vision_llm",
            "sha256": sha256,
        }

    return {
        "verdict": "inconclusive",
        "confidence": 0.5,
        "details": text[:500] if text else "Analysis returned no structured result.",
        "model_used": "vision_llm",
        "sha256": sha256,
    }


def get_verdict_emoji(verdict: str) -> str:
    """Map verdict strings to display emojis."""
    return {
        "likely_authentic": "✅",
        "likely_ai_generated": "🤖",
        "inconclusive": "⚠️",
    }.get(verdict, "❓")


def get_verdict_color(verdict: str) -> str:
    """Map verdict strings to hex colors for UI theming."""
    return {
        "likely_authentic": "#00C853",
        "likely_ai_generated": "#FF1744",
        "inconclusive": "#FF9100",
    }.get(verdict, "#9E9E9E")
