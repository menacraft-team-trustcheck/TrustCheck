"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE B.2: Fact Check
══════════════════════════════════════════════════════════════════════════════

Two-phase fact-checking pipeline:
  1. Query Google Fact Check Tools API for existing fact-check articles
  2. If no results (or API unavailable), fall back to LLM-based reasoning
     via the route_reasoning() function (DeepSeek → Groq fallback)

The Google Fact Check API is free and does not require an API key for
basic usage (rate-limited to ~100 requests/day).
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
import os
import requests
from typing import Dict, Any, List, Optional
from llm_router import route_reasoning, get_api_key

# ─────────────────────────────────────────────────────────────
# GOOGLE FACT CHECK TOOLS API
# ─────────────────────────────────────────────────────────────

GOOGLE_FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def _get_google_api_key() -> Optional[str]:
    """Get Google API key from environment variables."""
    return os.environ.get("GOOGLE_API_KEY", None)


def search_fact_checks(claim: str, language: str = "en") -> List[Dict[str, Any]]:
    """
    Search the Google Fact Check Tools API for existing fact-check reviews
    of the given claim.

    Args:
        claim: The claim text to search for
        language: ISO language code (default: "en")

    Returns:
        List of fact-check results, each with:
          - claim_text, claimant, claim_date
          - review_publisher, review_url, review_title, review_rating
    """
    api_key = _get_google_api_key()

    params = {
        "query": claim,
        "languageCode": language,
    }
    if api_key:
        params["key"] = api_key

    try:
        response = requests.get(GOOGLE_FACTCHECK_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return []

    # Parse the API response
    results = []
    for item in data.get("claims", []):
        claim_review = item.get("claimReview", [{}])[0] if item.get("claimReview") else {}
        publisher = claim_review.get("publisher", {})

        results.append({
            "claim_text": item.get("text", ""),
            "claimant": item.get("claimant", "Unknown"),
            "claim_date": item.get("claimDate", ""),
            "review_publisher": publisher.get("name", "Unknown"),
            "review_url": claim_review.get("url", ""),
            "review_title": claim_review.get("title", ""),
            "review_rating": claim_review.get("textualRating", ""),
            "review_language": claim_review.get("languageCode", language),
        })

    return results


# ─────────────────────────────────────────────────────────────
# LLM-BASED FACT CHECK REASONING (FALLBACK)
# ─────────────────────────────────────────────────────────────

FACTCHECK_SYSTEM_PROMPT = """You are a world-class fact-checker and OSINT analyst. Your task is to evaluate the plausibility of a given claim based on your training knowledge.

IMPORTANT RULES:
1. Be HONEST about your confidence level. If you are unsure, say so.
2. Do NOT fabricate sources or URLs.
3. Consider the claim from multiple angles: political, scientific, historical, geographic.
4. Note any red flags: extraordinary claims, emotional language, missing context.

RESPOND IN EXACTLY THIS JSON FORMAT:
{
    "plausibility_score": <float 0.0-1.0>,
    "verdict": "<likely_true|likely_false|unverifiable|mixed>",
    "reasoning": "Detailed 3-5 sentence explanation",
    "red_flags": ["list", "of", "concerns"],
    "recommended_sources": ["types of sources to check (not URLs)"]
}"""


def llm_fact_check(claim: str) -> Dict[str, Any]:
    """
    Use LLM reasoning (DeepSeek/Groq) to evaluate a claim when the
    Google Fact Check API returns no results.
    """
    prompt = f"""CLAIM TO EVALUATE:
"{claim}"

Analyze this claim for plausibility. Consider what is known about the subject, identify any red flags, and provide your assessment. Respond in the required JSON format."""

    raw = route_reasoning(prompt, system_prompt=FACTCHECK_SYSTEM_PROMPT)
    return _parse_factcheck_response(raw)


def _parse_factcheck_response(raw: str) -> Dict[str, Any]:
    """Parse LLM fact-check response JSON."""
    default = {
        "plausibility_score": 0.5,
        "verdict": "unverifiable",
        "reasoning": "",
        "red_flags": [],
        "recommended_sources": [],
        "source": "llm_reasoning",
    }

    if raw.startswith("[ERROR]"):
        default["reasoning"] = raw
        return default

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return {
            "plausibility_score": float(parsed.get("plausibility_score", 0.5)),
            "verdict": parsed.get("verdict", "unverifiable"),
            "reasoning": parsed.get("reasoning", ""),
            "red_flags": parsed.get("red_flags", []),
            "recommended_sources": parsed.get("recommended_sources", []),
            "source": "llm_reasoning",
        }
    except (json.JSONDecodeError, ValueError):
        default["reasoning"] = raw[:500]
        return default


# ─────────────────────────────────────────────────────────────
# UNIFIED FACT CHECK FUNCTION
# ─────────────────────────────────────────────────────────────

def fact_check_claim(claim: str) -> Dict[str, Any]:
    """
    Two-phase fact-checking:
      Phase 1 — Google Fact Check Tools API (authoritative sources)
      Phase 2 — LLM reasoning fallback (if no API results)

    Returns:
        dict with: verdict, score, details, google_results, llm_analysis
    """
    # Phase 1: Google Fact Check API
    google_results = search_fact_checks(claim)

    if google_results:
        # We have fact-check articles — synthesize them
        top = google_results[0]
        rating = top.get("review_rating", "").lower()

        # Map common ratings to scores
        if any(kw in rating for kw in ("false", "pants on fire", "incorrect", "fake")):
            score = 0.15
            verdict = "likely_false"
        elif any(kw in rating for kw in ("true", "correct", "accurate")):
            score = 0.85
            verdict = "likely_true"
        elif any(kw in rating for kw in ("mixed", "partly", "half")):
            score = 0.50
            verdict = "mixed"
        else:
            score = 0.50
            verdict = "mixed"

        return {
            "verdict": verdict,
            "score": score,
            "details": f"Found {len(google_results)} existing fact-check(s). "
                       f"Top result from {top['review_publisher']}: \"{top['review_rating']}\".",
            "google_results": google_results,
            "llm_analysis": None,
            "source": "google_factcheck_api",
        }

    # Phase 2: LLM reasoning fallback
    llm_result = llm_fact_check(claim)

    return {
        "verdict": llm_result["verdict"],
        "score": llm_result["plausibility_score"],
        "details": f"No existing fact-checks found. LLM analysis: {llm_result['reasoning']}",
        "google_results": [],
        "llm_analysis": llm_result,
        "source": "llm_reasoning",
    }


def get_factcheck_verdict_display(verdict: str) -> tuple:
    """Return (emoji, color, label) for fact-check verdicts."""
    mapping = {
        "likely_true":   ("✅", "#00C853", "Likely True"),
        "likely_false":  ("❌", "#FF1744", "Likely False"),
        "mixed":         ("⚖️", "#FF9100", "Mixed/Partly True"),
        "unverifiable":  ("❓", "#9E9E9E", "Unverifiable"),
    }
    return mapping.get(verdict, ("❓", "#9E9E9E", "Unknown"))
