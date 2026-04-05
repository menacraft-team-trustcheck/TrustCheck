"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE C: Source Credibility & Domain Forensics
══════════════════════════════════════════════════════════════════════════════

Evaluates the source against a multi-signal framework:
  1. Domain risk signals: suspicious TLDs, typosquatting patterns
  2. Emotional amplification & urgency manipulation in writing style
  3. Vague sourcing, anonymised authorship
  4. Source-type classification (editorial / stock / social / unknown)
  5. Source reputation using LLM knowledge

Returns a structured dict with confidence_score, verdict, and risk_signals.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
from typing import Dict, Any, List
from urllib.parse import urlparse
from llm_router import route_text, route_reasoning

# ── Known suspicious TLD patterns ────────────────────────────────────────────
SUSPICIOUS_TLDS = {
    ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click",
    ".loan", ".download", ".win", ".bid", ".stream", ".trade",
}

# ── Known credible editorial domains (partial) ───────────────────────────────
CREDIBLE_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "lemonde.fr", "aljazeera.com", "dw.com",
    "npr.org", "washingtonpost.com", "bloomberg.com", "ft.com",
}

# ── Stock/neutral platforms ───────────────────────────────────────────────────
STOCK_DOMAINS = {
    "pexels.com", "unsplash.com", "shutterstock.com", "getty images.com",
    "istockphoto.com", "flickr.com", "pixabay.com",
}

# ── Emotional amplification word patterns ────────────────────────────────────
EMOTIONAL_PATTERNS = re.compile(
    r"\b(BREAKING|SHOCKING|MUST.?READ|YOU WON'?T BELIEVE|URGENT|"
    r"SHARE NOW|WAKE UP|EXPOSED|BOMBSHELL|EXCLUSIVE|UNBELIEVABLE|"
    r"BANNED|CENSORED|THEY DON'?T WANT YOU TO KNOW)\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────
# LOCAL SIGNAL EXTRACTION (zero API cost)
# ─────────────────────────────────────────────────────────────

def _extract_domain_signals(source_url: str, source_name: str) -> Dict[str, Any]:
    """Extract domain-level risk signals without calling any API."""
    signals: List[str] = []
    source_type = "unknown"
    domain = ""
    base_score = 0.5

    if source_url.strip():
        try:
            parsed = urlparse(source_url if "://" in source_url else "https://" + source_url)
            domain = parsed.netloc.lower().removeprefix("www.")
        except Exception:
            domain = source_url.lower()

        # TLD risk
        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                signals.append(f"Suspicious TLD detected: {tld}")
                base_score -= 0.25

        # Known credible sources
        if any(cd in domain for cd in CREDIBLE_DOMAINS):
            source_type = "editorial"
            base_score = 0.85
        elif any(sd in domain for sd in STOCK_DOMAINS):
            source_type = "stock_photo"
            signals.append("Stock photo platform — image provides no news context")
            base_score = 0.45
        elif "twitter.com" in domain or "x.com" in domain:
            source_type = "social_media"
            signals.append("Social media post — unverified user-generated content")
            base_score = 0.35
        elif "facebook.com" in domain or "instagram.com" in domain:
            source_type = "social_media"
            signals.append("Social media — high misinformation risk platform")
            base_score = 0.30
        elif "t.me" in domain or "telegram" in domain:
            source_type = "messaging_app"
            signals.append("Messaging app — unverified, no editorial oversight")
            base_score = 0.20

        # Typosquatting check (compare against known credible domains)
        for cd in CREDIBLE_DOMAINS:
            cd_base = cd.split(".")[0]
            if cd_base in domain and cd not in domain and len(domain) > 3:
                signals.append(f"Possible typosquatting: '{domain}' resembles '{cd}'")
                base_score -= 0.20

    # Source name signals
    if source_name.strip():
        if source_name.startswith("@"):
            signals.append("Anonymous social handle — no institutional accountability")
            base_score -= 0.10

    return {
        "domain": domain,
        "source_type": source_type,
        "local_signals": signals,
        "base_score": round(max(0.0, min(1.0, base_score)), 3),
    }


def _check_text_manipulation(claim_text: str) -> List[str]:
    """Check claim text for emotional amplification and manipulation patterns."""
    signals = []
    if not claim_text.strip():
        return signals

    # Emotional amplification
    matches = EMOTIONAL_PATTERNS.findall(claim_text)
    if matches:
        unique = list(set(m.upper() for m in matches))
        signals.append(f"Emotional amplification language: {', '.join(unique[:3])}")

    # Urgency manipulation
    if re.search(r"\b(share|spread|tell everyone|repost)\b", claim_text, re.IGNORECASE):
        signals.append("Urgency manipulation: explicit share request")

    # Vague sourcing
    if re.search(r"\b(sources say|officials claim|reportedly|unconfirmed|allegedly)\b", claim_text, re.IGNORECASE):
        signals.append("Vague sourcing: anonymous or unattributed claims")

    # Extraordinary claims
    if re.search(r"\b(proof|evidence that|confirms|smoking gun|100%)\b", claim_text, re.IGNORECASE):
        signals.append("Extraordinary claim phrasing without cited evidence")

    return signals


# ─────────────────────────────────────────────────────────────
# CREDIBILITY SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────

CREDIBILITY_SYSTEM_PROMPT = """You are a Media Forensics & Source Credibility expert.

Using only your knowledge of the source, evaluate:
1. Is this source known for editorial standards, fact-checking, corrections?
2. Does it have a track record of misinformation, political bias, or state affiliation?
3. Is the source type appropriate for the claim (e.g., a stock photo site is NOT a news source)?
4. Does the claim text show signs of emotional manipulation, urgency, or vague attribution?

**Output EXACTLY this JSON (no preamble):**
{
    "credibility_score": <float 0.0-1.0>,
    "verdict": "highly_credible" | "credible" | "questionable" | "low_credibility" | "unknown",
    "bias_direction": "none" | "left" | "right" | "commercial" | "state" | "unknown",
    "bias_severity": "none" | "mild" | "moderate" | "severe",
    "risk_indicators": ["specific red flags found"],
    "language_quality": "professional" | "casual" | "sensational" | "manipulative",
    "analysis": "2-3 sentence hard assessment naming the decisive trust-breaking factor.",
    "recommendations": ["concrete investigator action items"]
}"""


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def analyze_credibility(
    source_name: str = "",
    claim_text: str = "",
    source_url:  str = "",
) -> Dict[str, Any]:
    """
    Full 2-layer credibility analysis:
      Layer 1: Local domain/text signal extraction (zero API cost)
      Layer 2: LLM reputational assessment
    """
    # Layer 1 — local signals
    domain_data  = _extract_domain_signals(source_url, source_name)
    text_signals = _check_text_manipulation(claim_text)
    all_local_signals = domain_data["local_signals"] + text_signals
    local_score  = domain_data["base_score"]

    if not any([source_name.strip(), claim_text.strip(), source_url.strip()]):
        return {
            "credibility_score": 0.0, "verdict": "unknown",
            "analysis": "No source information provided.",
            "risk_indicators": [], "bias_direction": "unknown",
            "bias_severity": "none", "language_quality": "unknown",
            "recommendations": ["Provide source info for analysis."],
            "source_type": "unknown", "domain": "",
        }

    # Layer 2 — LLM assessment
    info_parts = []
    if source_name.strip(): info_parts.append(f"SOURCE NAME: {source_name}")
    if domain_data["domain"]: info_parts.append(f"DOMAIN: {domain_data['domain']}")
    if domain_data["source_type"] != "unknown":
        info_parts.append(f"SOURCE TYPE: {domain_data['source_type']}")
    if claim_text.strip():
        info_parts.append(f"CLAIM TEXT:\n\"\"\"\n{claim_text[:1500]}\n\"\"\"")
    if all_local_signals:
        info_parts.append(f"PRE-DETECTED SIGNALS: {'; '.join(all_local_signals)}")

    prompt = "Evaluate media source credibility:\n\n" + "\n".join(info_parts) + "\n\nRespond in JSON."

    try:
        raw = route_text(prompt, system_prompt=CREDIBILITY_SYSTEM_PROMPT, temperature=0.15)
    except Exception:
        raw = route_reasoning(prompt, system_prompt=CREDIBILITY_SYSTEM_PROMPT)

    parsed = _parse_credibility_response(raw)

    # Blend local score with LLM score (60/40 split — local signals are deterministic)
    if parsed["credibility_score"] > 0:
        blended = round(local_score * 0.4 + parsed["credibility_score"] * 0.6, 3)
        parsed["credibility_score"] = blended

    # Merge local risk signals into the LLM-found indicators
    all_risks = list(set(all_local_signals + parsed.get("risk_indicators", [])))
    parsed["risk_indicators"] = all_risks
    parsed["source_type"] = domain_data["source_type"]
    parsed["domain"] = domain_data["domain"]

    return parsed


def _parse_credibility_response(raw: str) -> Dict[str, Any]:
    default = {
        "credibility_score": 0.5, "verdict": "unknown", "analysis": "",
        "risk_indicators": [], "bias_direction": "unknown",
        "bias_severity": "none", "language_quality": "unknown",
        "recommendations": [],
    }
    if raw.startswith("[ERROR]"):
        default["analysis"] = raw
        return default

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Extract first JSON object if there's preamble text
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        p = json.loads(cleaned)
        return {
            "credibility_score": float(p.get("credibility_score", 0.5)),
            "verdict":           p.get("verdict", "unknown"),
            "analysis":          p.get("analysis", ""),
            "risk_indicators":   p.get("risk_indicators", []),
            "bias_direction":    p.get("bias_direction", "unknown"),
            "bias_severity":     p.get("bias_severity", "none"),
            "language_quality":  p.get("language_quality", "unknown"),
            "recommendations":   p.get("recommendations", []),
        }
    except (json.JSONDecodeError, ValueError):
        default["analysis"] = raw[:500]
        return default


def get_credibility_verdict_display(verdict: str) -> tuple:
    return {
        "highly_credible": ("🏆", "#00C853", "Highly Credible"),
        "credible":        ("✅", "#4CAF50", "Credible"),
        "questionable":    ("⚠️", "#FF9100", "Questionable"),
        "low_credibility": ("🚩", "#FF1744", "Low Credibility"),
        "unknown":         ("❓", "#9E9E9E", "Unknown"),
    }.get(verdict, ("❓", "#9E9E9E", "Unknown"))
