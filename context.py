"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE B.1: Contextual Consistency (Vision)
══════════════════════════════════════════════════════════════════════════════

Uses the OpenRouter vision models (llama-3.2-11b-vision / qwen2.5-vl-7b)
to compare what is VISIBLE in an image against a user-provided textual claim.

The model is prompted to act as an OSINT investigator and assess whether the
image content is consistent with or contradicts the stated claim.

Returns a structured assessment with:
  - match_score: 0.0 (total mismatch) → 1.0 (perfect consistency)
  - verdict: "consistent" | "inconsistent" | "uncertain"
  - analysis: detailed explanation of visual vs. textual comparison
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
from typing import Dict, Any
from llm_router import route_vision, encode_image_to_base64, route_text

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT — OSINT Visual Context Analyst
# ─────────────────────────────────────────────────────────────

CONTEXT_SYSTEM_PROMPT = """You are an expert OSINT (Open Source Intelligence) investigator specialising in visual verification. Your task is to analyse an image and determine whether its visual content is CONSISTENT with a given textual claim.

ANALYZE THE FOLLOWING ASPECTS:
1. **Scene & Setting**: Does the environment, location markers (signs, landmarks, vegetation) match the claim?
2. **People & Actions**: Do the individuals, their clothing, actions, and expressions align with the narrative?
3. **Objects & Artifacts**: Are the objects, vehicles, equipment consistent with the claimed event/time/place?
4. **Temporal Cues**: Do lighting, shadows, weather, or visible dates/timestamps match the claimed timeframe?
5. **Text & Symbols**: Any visible text, logos, or symbols — do they support or contradict the claim?
6. **Anachronisms**: Anything that seems out of place for the claimed context?

RESPOND IN EXACTLY THIS JSON FORMAT (no markdown, no extra text):
{
    "match_score": <float 0.0-1.0>,
    "verdict": "<consistent|inconsistent|uncertain>",
    "visual_elements_found": ["list", "of", "key", "visual", "elements"],
    "supporting_evidence": "What in the image SUPPORTS the claim",
    "contradicting_evidence": "What in the image CONTRADICTS the claim (or 'None found')",
    "analysis": "Detailed 2-3 sentence overall assessment"
}"""


def analyze_context(
    image_bytes: bytes,
    claim_text: str,
) -> Dict[str, Any]:
    """
    Compare image content against a user-provided claim using vision LLM.

    Args:
        image_bytes: Raw bytes of the image to analyze
        claim_text: The textual claim/caption to verify against the image

    Returns:
        dict with: match_score, verdict, analysis, supporting_evidence,
                   contradicting_evidence, visual_elements_found
    """
    if not claim_text.strip():
        return {
            "match_score": 0.0,
            "verdict": "uncertain",
            "analysis": "No claim text provided for comparison.",
            "visual_elements_found": [],
            "supporting_evidence": "N/A",
            "contradicting_evidence": "N/A",
        }

    # Encode image for the vision API
    image_b64 = encode_image_to_base64(image_bytes)

    # Build the user prompt
    user_prompt = f"""CLAIM TO VERIFY: "{claim_text}"

Carefully examine the uploaded image and determine whether its visual content is consistent with the claim above. Look for any supporting or contradicting evidence. Respond in the required JSON format."""

    # Route to vision model (OpenRouter)
    raw_response = route_vision(
        prompt=user_prompt,
        image_b64=image_b64,
        system_prompt=CONTEXT_SYSTEM_PROMPT,
        temperature=0.2,
    )

    # Parse the JSON response
    return _parse_context_response(raw_response)


def _parse_context_response(raw_response: str) -> Dict[str, Any]:
    """
    Parse the vision model's JSON response, handling common formatting
    issues (markdown code blocks, trailing text, etc.).
    """
    default_result = {
        "match_score": 0.5,
        "verdict": "uncertain",
        "analysis": "",
        "visual_elements_found": [],
        "supporting_evidence": "Unable to parse",
        "contradicting_evidence": "Unable to parse",
    }

    if raw_response.startswith("[ERROR]"):
        default_result["analysis"] = raw_response
        return default_result

    # Strip markdown code fences if present
    cleaned = raw_response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return {
            "match_score": float(parsed.get("match_score", 0.5)),
            "verdict": parsed.get("verdict", "uncertain"),
            "analysis": parsed.get("analysis", ""),
            "visual_elements_found": parsed.get("visual_elements_found", []),
            "supporting_evidence": parsed.get("supporting_evidence", ""),
            "contradicting_evidence": parsed.get("contradicting_evidence", "None found"),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        # If JSON parsing fails, use LLM text as-is
        default_result["analysis"] = raw_response[:500]

        # Try to extract a score heuristically
        score_match = re.search(r"(\d+\.?\d*)\s*/\s*10", raw_response)
        if score_match:
            default_result["match_score"] = float(score_match.group(1)) / 10

        # Try to detect verdict keywords
        lower = raw_response.lower()
        if "inconsistent" in lower or "contradict" in lower or "mismatch" in lower:
            default_result["verdict"] = "inconsistent"
        elif "consistent" in lower or "matches" in lower or "supports" in lower:
            default_result["verdict"] = "consistent"

        return default_result


def get_context_verdict_display(verdict: str) -> tuple:
    """Return (emoji, color, label) for a context verdict."""
    mapping = {
        "consistent":   ("✅", "#00C853", "Consistent"),
        "inconsistent": ("❌", "#FF1744", "Inconsistent"),
        "uncertain":    ("⚠️", "#FF9100", "Uncertain"),
    }
    return mapping.get(verdict, ("❓", "#9E9E9E", "Unknown"))
