"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE A: Content Authenticity
══════════════════════════════════════════════════════════════════════════════

Determines whether an image is AI-generated or has been digitally manipulated
using OpenRouter Vision LLMs for detailed image forensic analysis.

Strategy:
  1. Send image to a vision LLM with a forensic analysis prompt
  2. Parse the structured JSON response for verdict + confidence

Returns a structured result dict with:
  - verdict: "likely_authentic" | "likely_ai_generated" | "inconclusive"
  - confidence: float 0-1
  - details: human-readable explanation
══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import re
import logging
from typing import Dict, Any
from llm_router import route_vision, route_text, encode_image_to_base64

logger = logging.getLogger("trustcheck.authenticity")


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
    Run AI-generated image detection via OpenRouter Vision LLM.

    Falls back to Groq/DeepSeek text-based heuristic if vision fails.

    Returns:
        dict with keys: verdict, confidence, details, model_used, sha256
    """
    sha256 = compute_file_hash(image_bytes)
    result = {
        "verdict": "inconclusive",
        "confidence": 0.0,
        "details": "",
        "model_used": "none",
        "sha256": sha256,
    }

    # ── Try Vision LLM for forensic analysis ─────────────────
    logger.info("Running authenticity check via Vision LLM...")
    image_b64 = encode_image_to_base64(image_bytes)
    vision_result = route_vision(FORENSIC_PROMPT, image_b64)

    if vision_result and not (isinstance(vision_result, str) and vision_result.startswith("[ERROR]")):
        parsed = _parse_vision_response(vision_result, sha256)
        if parsed:
            return parsed

    # ── Fallback: Text LLM general assessment ────────────────
    logger.info("Vision failed, falling back to text LLM...")
    fallback_prompt = (
        "You are a digital forensics expert. A user uploaded an image for analysis "
        "but we couldn't run vision-based detection. Based on general knowledge, "
        "what advice would you give for manually checking if an image is AI-generated? "
        "Reply with a brief 2-3 sentence practical guide."
    )
    fallback_result = route_text(fallback_prompt)

    result["details"] = (
        f"Vision-based detection was unavailable. "
        f"Manual verification recommended. {fallback_result}"
        if isinstance(fallback_result, str) and not fallback_result.startswith("[ERROR]")
        else "Automated detection unavailable. Please verify the image manually using reverse image search and metadata analysis."
    )
    result["model_used"] = "fallback_llm"
    return result


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
