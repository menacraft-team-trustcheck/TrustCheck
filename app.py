"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — FastAPI Backend (app.py)
══════════════════════════════════════════════════════════════════════════════

REST API backend that your Figma-based frontend calls.

Endpoints:
  GET  /status                      → Provider health + Supabase status
  GET  /history                     → Recent analyses from Supabase
  GET  /analysis/{file_hash}        → Retrieve stored analysis by hash
  POST /analyze/image               → Full image analysis (all 3 axes)
  POST /analyze/video               → Video frame-by-frame analysis
  POST /analyze/batch               → Batch image analysis
  POST /analyze/authenticity        → Axis A only
  POST /analyze/context             → Axis B.1 only
  POST /analyze/fact-check          → Axis B.2 only
  POST /analyze/geolocation         → Axis B.3 only
  POST /analyze/credibility         → Axis C only
  POST /analyze/heatmap             → Heatmap overlay only
  POST /report/certificate          → Generate PDF certificate

Run:  uvicorn app:app --reload --port 8000

NO ANTHROPIC / CLAUDE DEPENDENCIES.
══════════════════════════════════════════════════════════════════════════════
"""

import io
import os
import logging
import base64
import hashlib
import datetime
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env file for API keys
load_dotenv()

# ── Configure logging ────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("trustcheck.api")

# ── Module imports ───────────────────────────────────────────
from llm_router import check_provider_status, PROVIDERS, get_fallback_logs, route_reasoning
from authenticity import analyze_image_authenticity, compute_file_hash
from video_analyzer import analyze_video
from context import analyze_context
from fact_check import fact_check_claim
from geolocation import analyze_geolocation
from credibility import analyze_credibility
from heatmap import generate_heatmap
from voice_analyzer import analyze_voice
import voice_analyzer as voice_analyzer_module
from certificate import generate_certificate
from database import (
    is_connected as db_connected,
    save_analysis, get_analysis, get_recent_analyses,
    save_report, upload_file as db_upload_file,
)

# ═══════════════════════════════════════════════════════════════
# APP INIT
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="MenaCraft TrustCheck API",
    description="OSINT content verification across 3 axes: Authenticity, Context, Credibility",
    version="2.0.0",
)


# Create a shared ThreadPoolExecutor for blocking work (models, network calls)
@app.on_event("startup")
async def _startup():
    loop = asyncio.get_running_loop()
    # Create a modest-sized executor to avoid creating many threads per-request
    executor = ThreadPoolExecutor(max_workers=8)
    app.state.executor = executor

    # Pre-load heavy audio models in background to avoid cold-start on first request
    try:
        await loop.run_in_executor(app.state.executor, getattr, voice_analyzer_module, "preload_models")
        # Actually call the preload function if present
        preload = getattr(voice_analyzer_module, "preload_models", None)
        if callable(preload):
            await loop.run_in_executor(app.state.executor, preload)
            logger.info("Preloaded optional audio models (pyannote/resemblyzer)")
    except Exception as e:
        logger.debug(f"Preload models failed: {e}")


@app.on_event("shutdown")
def _shutdown():
    try:
        execr = getattr(app.state, "executor", None)
        if execr:
            execr.shutdown(wait=False)
    except Exception:
        pass

# Simple in-memory cache for expensive per-file results
_analysis_cache: dict = {}
_cache_ttl_seconds = 300

def _cache_get(key: str):
    item = _analysis_cache.get(key)
    if not item: return None
    ts, value = item
    if (datetime.datetime.now() - ts).total_seconds() > _cache_ttl_seconds:
        try: del _analysis_cache[key]
        except: pass
        return None
    return value

def _cache_set(key: str, value: dict):
    _analysis_cache[key] = (datetime.datetime.now(), value)

# CORS — allow your frontend (Figma export / local dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend static files ──────────────────────────────
# We now serve the built Next.js export from the 'out' directory
FRONTEND_SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
FRONTEND_BUILD_DIR = os.path.join(FRONTEND_SOURCE_DIR, "out")

# Use build dir if it exists (standard Next.js export), else fallback to source for legacy compatibility
serving_dir = FRONTEND_BUILD_DIR if os.path.isdir(FRONTEND_BUILD_DIR) else FRONTEND_SOURCE_DIR

if os.path.isdir(serving_dir):
    logger.info(f"Serving frontend assets from: {serving_dir}")
    app.mount("/ui", StaticFiles(directory=serving_dir, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root to the frontend UI."""
    return RedirectResponse(url="/ui/index.html")


# ═══════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════

@app.get("/status")
def get_status():
    """Provider health check — shows which API keys and Supabase are configured."""
    status = check_provider_status()
    providers = {}
    for pid, cfg in PROVIDERS.items():
        providers[pid] = {
            "name": cfg["name"],
            "emoji": cfg["emoji"],
            "connected": status.get(pid, False),
        }
    return {
        "status": "operational",
        "providers": providers,
        "supabase_connected": db_connected(),
        "recent_logs": get_fallback_logs()[-10:],
    }


@app.get("/history")
def get_history(limit: int = 20):
    """Retrieve recent analysis history from Supabase."""
    return {"analyses": get_recent_analyses(limit)}


@app.get("/analysis/{file_hash}")
def get_stored_analysis(file_hash: str):
    """Retrieve a previously stored analysis by file hash."""
    result = get_analysis(file_hash)
    if not result:
        raise HTTPException(404, "No analysis found for this file hash.")
    return result


# ═══════════════════════════════════════════════════════════════
# WEIGHTED SCORING + CONTRADICTION DETECTION ENGINE
# ═══════════════════════════════════════════════════════════════

# Axis weights — visual forensics carry most weight, source is a tie-breaker
AXIS_WEIGHTS = {
    "visual":   0.60,   # Axis A (AI detection) + ELA heatmap
    "context":  0.25,   # Axis B.1 (semantic) + B.2 (plausibility)
    "source":   0.15,   # Axis C (domain/reputation)
}


def _score_to_risk(score: float) -> str:
    """Map weighted risk score (0=safe, 1=danger) to risk level label."""
    if score >= 0.75:  return "CRITICAL"
    if score >= 0.55:  return "HIGH"
    if score >= 0.30:  return "MEDIUM"
    return "LOW"


def _detect_visual_conflict(auth: dict, heatmap: dict) -> bool:
    """
    Returns True when Axis A and ELA disagree — the classic 'staged fake' pattern.
    A clip appears pixel-clean (ELA low) yet the AI vision model flags it as synthetic.
    """
    ai_flagged = auth.get("verdict") == "likely_ai_generated"
    ela_clean  = heatmap.get("ela_mean", 0) < 0.06
    ela_hot    = len(heatmap.get("hotspots", [])) > 0

    return (ai_flagged and ela_clean) or (not ai_flagged and ela_hot)


def _compute_weighted_score(
    auth: dict,
    heatmap: dict,
    context: dict | None,
    fact_check: dict | None,
    credibility: dict | None,
    visual_conflict: bool,
) -> float:
    """
    Compute a unified 0-1 risk score from all axes.
    Higher = more suspicious / likely manipulated.
    """
    # ── Visual score (Axis A + ELA) ──────────────────────────────
    auth_conf    = float(auth.get("confidence", 0.5))
    auth_risk    = auth_conf if auth.get("verdict") == "likely_ai_generated" else (1 - auth_conf) * 0.3
    ela_mean     = float(heatmap.get("ela_mean", 0.05))
    ela_risk     = min(1.0, ela_mean * 8)   # scale: 0.12 ELA → 1.0 risk
    visual_score = (auth_risk * 0.55 + ela_risk * 0.45)

    # ── Context score (B.1 + B.2) ────────────────────────────────
    ctx_score = 0.5   # neutral if no claim provided
    if context:
        ctx_map  = {"consistent": 0.1, "uncertain": 0.45, "inconsistent": 0.85}
        ctx_score = ctx_map.get(context.get("verdict", "uncertain"), 0.45)
    if fact_check:
        fc_map   = {"likely_true": 0.1, "unverifiable": 0.5, "likely_false": 0.9, "mixed": 0.6}
        fc_risk  = fc_map.get(fact_check.get("verdict", "unverifiable"), 0.5)
        ctx_score = (ctx_score + fc_risk) / 2 if context else fc_risk

    # ── Source score (Axis C) ────────────────────────────────────
    src_score = 0.5   # neutral default
    if credibility:
        cred_raw  = float(credibility.get("credibility_score", 0.5))
        src_score = 1.0 - cred_raw   # high credibility → low risk

    # ── Weighted combination ──────────────────────────────────────
    weighted = (
        visual_score * AXIS_WEIGHTS["visual"]  +
        ctx_score    * AXIS_WEIGHTS["context"] +
        src_score    * AXIS_WEIGHTS["source"]
    )

    # When visual axes conflict (staged-fake pattern), cap score at HIGH
    if visual_conflict:
        weighted = max(weighted, 0.60)

    return round(min(1.0, weighted), 4)


def synthesize_results(
    auth: dict,
    context: dict | None,
    fact_check: dict | None,
    credibility: dict | None,
    heatmap: dict,
) -> dict:
    """
    Master forensic synthesis:
    1. Compute weighted risk score across all axes
    2. Detect visual conflict (staged-fake signal)
    3. Call LLaMA 3.3 70B to produce 2-sentence plain-language verdict
    4. Return structured evidence chain
    """
    visual_conflict = _detect_visual_conflict(auth, heatmap)
    risk_score      = _compute_weighted_score(
        auth, heatmap, context, fact_check, credibility, visual_conflict
    )
    risk_level      = _score_to_risk(risk_score)

    # Decisive factor (for the synthesis prompt)
    decisive = "unknown"
    if auth.get("verdict") == "likely_ai_generated":      decisive = "AI generation fingerprints in pixel analysis"
    elif heatmap.get("ela_mean", 0) > 0.10:              decisive = "ELA artifacts indicating local editing"
    elif context and context.get("verdict") == "inconsistent": decisive = "semantic mismatch between image and claim"
    elif credibility and credibility.get("credibility_score", 1) < 0.35: decisive = "low-credibility source with risk signals"
    elif visual_conflict:                                  decisive = "conflict between AI detector and ELA (staged-fake pattern)"

    prompt = f"""You are the Chief Forensic Analyst at an OSINT verification agency.
You have received a complete multi-axis verification report. Your task: write exactly 2 sentences naming the single most decisive forensic factor and your final confidence in the conclusion.

REPORT SUMMARY:
- Risk Score: {risk_score:.0%}  →  {risk_level}
- Axis A (AI Detection): {auth.get('verdict', 'N/A')} (confidence {auth.get('confidence', 0):.0%})
- ELA Heatmap: mean={heatmap.get('ela_mean', 0):.1%}, hotspots={len(heatmap.get('hotspots', []))}
- Visual Conflict Detected: {visual_conflict}
- Axis B.1 (Context): {context.get('verdict', 'N/A') if context else 'not assessed'}
- Axis B.2 (Fact Check): {fact_check.get('verdict', 'N/A') if fact_check else 'not assessed'}
- Axis C (Source): {credibility.get('verdict', 'N/A') if credibility else 'not assessed'}
- Decisive Factor: {decisive}

2-sentence synthesis (technical, direct, name the decisive factor):"""

    try:
        narrative = route_reasoning(prompt)
    except Exception:
        narrative = f"Risk level {risk_level} ({risk_score:.0%}). Decisive signal: {decisive}."

    return {
        "risk_level":       risk_level,
        "risk_score":       risk_score,
        "visual_conflict":  visual_conflict,
        "decisive_factor":  decisive,
        "narrative":        narrative,
        "axis_weights":     AXIS_WEIGHTS,
    }



# ═══════════════════════════════════════════════════════════════
# AXIS A: CONTENT AUTHENTICITY
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/authenticity")
async def endpoint_authenticity(image: UploadFile = File(...)):
    """Detect AI-generated or manipulated images via HuggingFace models."""
    image_bytes = await image.read()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_image_authenticity, image_bytes)
    result["filename"] = image.filename
    return result


# ═══════════════════════════════════════════════════════════════
# AXIS B.1: CONTEXTUAL CONSISTENCY
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/context")
async def endpoint_context(
    image: UploadFile = File(...),
    claim: str = Form(""),
):
    """Compare image visual content against a textual claim via Vision LLM."""
    if not claim.strip():
        raise HTTPException(400, "A 'claim' text is required for context analysis.")
    image_bytes = await image.read()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_context, image_bytes, claim)
    result["filename"] = image.filename
    return result


# ═══════════════════════════════════════════════════════════════
# AXIS B.2: FACT CHECK
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/fact-check")
async def endpoint_fact_check(claim: str = Form(...)):
    """Google Fact Check API + LLM reasoning fallback."""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), fact_check_claim, claim)
    return result


# ═══════════════════════════════════════════════════════════════
# AXIS B.3: GEOLOCATION
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/geolocation")
async def endpoint_geolocation(
    image: UploadFile = File(...),
    claimed_location: str = Form(""),
):
    """Extract EXIF GPS + reverse geocode + compare with claimed location."""
    image_bytes = await image.read()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_geolocation, image_bytes, claimed_location)
    return result


# ═══════════════════════════════════════════════════════════════
# AXIS C: SOURCE CREDIBILITY
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/credibility")
async def endpoint_credibility(
    source_name: str = Form(""),
    claim_text: str = Form(""),
    source_url: str = Form(""),
):
    """Assess source/author credibility via Groq/DeepSeek text analysis."""
    if not any([source_name.strip(), claim_text.strip(), source_url.strip()]):
        raise HTTPException(400, "At least one of source_name, claim_text, or source_url is required.")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_credibility, source_name, claim_text, source_url)
    return result


# ═══════════════════════════════════════════════════════════════
# HEATMAP (EXPLAINABILITY)
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/heatmap")
async def endpoint_heatmap(image: UploadFile = File(...)):
    """Generate a manipulation-likelihood heatmap overlay image."""
    image_bytes = await image.read()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), generate_heatmap, image_bytes)

    # Return heatmap as base64-encoded PNG plus metadata
    heatmap_b64 = ""
    if result.get("heatmap_image_bytes"):
        heatmap_b64 = base64.b64encode(result["heatmap_image_bytes"]).decode("utf-8")

    return {
        "heatmap_image_base64": heatmap_b64,
        "grid_scores": result.get("grid_scores"),
        "overall_assessment": result.get("overall_assessment"),
        "hotspots": result.get("hotspots"),
    }


# ═══════════════════════════════════════════════════════════════
# FULL IMAGE ANALYSIS (ALL AXES)
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/image")
async def endpoint_full_image(
    image: UploadFile = File(...),
    claim: str = Form(""),
    source_name: str = Form(""),
    source_url: str = Form(""),
    claimed_location: str = Form(""),
    fast: bool = Form(False),
):
    """Async multi-axis pipeline — runs heavy work in a shared executor to avoid blocking the event loop."""
    try:
        image_bytes = await image.read()
        file_hash = compute_file_hash(image_bytes)

        results = {"filename": image.filename, "sha256": file_hash}

        # Define closures for each axis (these run in executor)
        def run_authenticity():
            fh = compute_file_hash(image_bytes)
            cached = _cache_get(f"auth::{fh}")
            if cached is not None:
                return ("authenticity", cached)
            res = analyze_image_authenticity(image_bytes)
            try: _cache_set(f"auth::{fh}", res)
            except: pass
            return ("authenticity", res)

        def run_heatmap():
            fh = compute_file_hash(image_bytes)
            cached = _cache_get(f"heatmap::{fh}")
            if cached is not None:
                return ("_heatmap_raw", cached)
            res = generate_heatmap(image_bytes)
            try: _cache_set(f"heatmap::{fh}", res)
            except: pass
            return ("_heatmap_raw", res)

        def run_geolocation():
            return ("geolocation", analyze_geolocation(image_bytes, claimed_location))

        def run_context():
            if claim.strip():
                return ("context", analyze_context(image_bytes, claim))
            return ("context", {})

        def run_fact_check():
            if claim.strip():
                return ("fact_check", fact_check_claim(claim))
            return ("fact_check", {})

        def run_credibility():
            if source_name.strip() or claim.strip():
                return ("credibility", analyze_credibility(source_name, claim, source_url))
            return ("credibility", {})

        if fast:
            tasks = [run_authenticity, run_heatmap]
        else:
            tasks = [run_authenticity, run_heatmap, run_geolocation, run_context, run_fact_check, run_credibility]

        logger.info(f"Launching {len(tasks)} parallel analysis axes...")
        import time
        loop = asyncio.get_running_loop()
        coros = []
        
        # We wrap the executor call to capture elapsed time
        async def wrap_task(task_func):
            t0 = time.time()
            res = await loop.run_in_executor(getattr(app.state, "executor", None), task_func)
            t1 = time.time()
            return task_func.__name__, res, round(t1 - t0, 2)

        for t in tasks:
            coros.append(asyncio.wait_for(wrap_task(t), timeout=60))

        completed = await asyncio.gather(*coros, return_exceptions=True)

        task_timings = {}
        for idx, outcome in enumerate(completed):
            task_fn = tasks[idx]
            task_name = getattr(task_fn, "__name__", f"task_{idx}").replace("run_", "")
            if isinstance(outcome, Exception):
                logger.warning(f"Task {task_name} failed or timed out: {outcome}")
                results.setdefault("task_errors", {})[task_name] = str(outcome)
                continue
            
            # Validate result shape (expecting a 3-tuple from our wrapper)
            if not isinstance(outcome, (list, tuple)) or len(outcome) != 3:
                logger.error(f"Unexpected task result shape from {task_name}: {repr(outcome)}")
                results.setdefault("task_errors", {})[task_name] = f"unexpected_result: {repr(outcome)}"
                continue
            
            _, res_tuple, elapsed = outcome
            if isinstance(res_tuple, tuple) and len(res_tuple) == 2:
                key, value = res_tuple
                results[key] = value
                task_timings[key] = elapsed
            else:
                results.setdefault("task_errors", {})[task_name] = "invalid_inner_tuple"
                
        results["taskTimings"] = task_timings

        # Unpack heatmap
        hm = results.pop("_heatmap_raw", {})
        heatmap_b64 = hm.get("heatmap_image_base64", "")
        if not heatmap_b64 and hm.get("heatmap_image_bytes"):
            heatmap_b64 = base64.b64encode(hm["heatmap_image_bytes"]).decode("utf-8")

        results["heatmap"] = {
            "heatmap_image_base64": heatmap_b64,
            "grid_scores": hm.get("grid_scores"),
            "overall_assessment": hm.get("overall_assessment"),
            "hotspots": hm.get("hotspots", []),
            "ela_mean": hm.get("ela_mean", 0.0),
            "ela_max": hm.get("ela_max", 0.0),
            "method": hm.get("method", "ela_local"),
        }

        # Synthesis
        results["synthesis"] = synthesize_results(
            results.get("authenticity", {}),
            results.get("context", {}),
            results.get("fact_check", {}),
            results.get("credibility", {}),
            hm,
        )

        results["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Persist in background
        try:
            asyncio.ensure_future(loop.run_in_executor(getattr(app.state, "executor", None), save_analysis, file_hash, image.filename or "unknown", "image", results))
        except Exception:
            pass

        # Flatten for frontend compatibility (matches expected AnalysisResult mapping)
        top_level = results.get("synthesis", {})
        results["verdict"] = top_level.get("verdict", "inconclusive")
        results["ai_score"] = top_level.get("risk_score", 0.5)
        results["reasoning"] = top_level.get("narrative", "Forensic synthesis complete. No specific narrative provided.")
        results["interpretation"] = results["reasoning"] # Keep alias for backward compatibility

        return results
    except Exception as e:
        logger.exception("Catastrophic image analysis failure")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════════════════════
# VOICE / AUDIO ANALYSIS
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/voice")
async def endpoint_voice(audio: UploadFile = File(...)):
    """Acoustic forensic analysis to detect AI-generated voice/speech."""
    try:
        audio_bytes = await audio.read()
        file_hash = compute_file_hash(audio_bytes)

        logger.info(f"Running Voice Analysis for {audio.filename}...")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_voice, audio_bytes, audio.filename or "audio.tmp")
        result["filename"] = audio.filename
        result["sha256"] = file_hash

        # Persist in background
        try:
            asyncio.ensure_future(loop.run_in_executor(getattr(app.state, "executor", None), save_analysis, file_hash, audio.filename or "unknown", "audio", result))
        except Exception as e:
            logger.error(f"Persistence failed: {e}")

        return result
    except Exception as e:
        logger.exception("Voice analysis failure")
        return JSONResponse(status_code=500, content={"error": f"Voice Analysis Failure: {str(e)}"})



# ═══════════════════════════════════════════════════════════════
# VIDEO ANALYSIS
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/video")
async def endpoint_video(
    video: UploadFile = File(...),
    interval_sec: float = Form(2.0),
):
    """Frame-by-frame video analysis with risk timeline."""
    video_bytes = await video.read()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_video, video_bytes, interval_sec)

    # Convert timeline image to base64
    timeline_b64 = ""
    if result.get("timeline_image_bytes"):
        timeline_b64 = base64.b64encode(result["timeline_image_bytes"]).decode("utf-8")

    # Convert suspicious frame images to base64
    suspicious = []
    for sf in result.get("suspicious_frames", []):
        sf_copy = {k: v for k, v in sf.items() if k != "image_bytes"}
        if sf.get("image_bytes"):
            sf_copy["image_base64"] = base64.b64encode(sf["image_bytes"]).decode("utf-8")
        suspicious.append(sf_copy)

    video_result = {
        "filename": video.filename,
        "sha256": result.get("sha256"),
        "overall_verdict": result.get("overall_verdict"),
        "average_ai_score": result.get("average_ai_score"),
        "details": result.get("details"),
        "total_frames": result.get("total_frames"),
        "frame_scores": result.get("frame_scores"),
        "timeline_image_base64": timeline_b64,
        "suspicious_frames": suspicious,
    }

    # Persist in background
    try:
        asyncio.ensure_future(loop.run_in_executor(getattr(app.state, "executor", None), save_analysis, result.get("sha256", ""), video.filename or "unknown", "video", video_result))
    except Exception:
        pass

    return video_result


# ═══════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════

@app.post("/analyze/batch")
async def endpoint_batch(
    images: List[UploadFile] = File(...),
    claim: str = Form(""),
):
    """Batch-analyze multiple images."""
    results = []
    loop = asyncio.get_running_loop()
    tasks = []
    for img in images:
        img_bytes = await img.read()
        # schedule authenticity and context in executor
        auth_coro = loop.run_in_executor(getattr(app.state, "executor", None), analyze_image_authenticity, img_bytes)
        ctx_coro = None
        if claim.strip():
            ctx_coro = loop.run_in_executor(getattr(app.state, "executor", None), analyze_context, img_bytes, claim)
        tasks.append((img, img_bytes, auth_coro, ctx_coro))

    # await and collect
    for img, img_bytes, auth_coro, ctx_coro in tasks:
        auth = await auth_coro
        ctx = await ctx_coro if ctx_coro is not None else None
        results.append({
            "filename": img.filename,
            "sha256": compute_file_hash(img_bytes),
            "authenticity": auth,
            "context": ctx,
        })
    # ── Persist batch to Supabase ─────────────────────────────
    for r in results:
        save_analysis(r["sha256"], r["filename"], "batch", r)

    return {"results": results, "total": len(results)}


# ═══════════════════════════════════════════════════════════════
# PDF CERTIFICATE
# ═══════════════════════════════════════════════════════════════

@app.post("/report/certificate")
async def endpoint_certificate(
    image: UploadFile = File(...),
    claim: str = Form(""),
    source_name: str = Form(""),
    source_url: str = Form(""),
    claimed_location: str = Form(""),
):
    """
    Run full analysis and return a downloadable PDF certificate.
    Content-Type: application/pdf
    """
    try:
        image_bytes = await image.read()
        file_hash = compute_file_hash(image_bytes)

        # Run all pipelines safely
        logger.info(f"Generating certificate for {image.filename}...")
        
        loop = asyncio.get_running_loop()
        # Run heavy tasks in executor and gather
        auth = None; ctx = None; fc = None; geo = None; cred = None; hm = None
        try:
            auth = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_image_authenticity, image_bytes)
        except Exception:
            auth = {"verdict": "inconclusive", "confidence": 0.5, "details": "Error in Axis A"}

        try:
            ctx = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_context, image_bytes, claim) if claim.strip() else None
        except Exception:
            ctx = None

        try:
            fc = await loop.run_in_executor(getattr(app.state, "executor", None), fact_check_claim, claim) if claim.strip() else None
        except Exception:
            fc = None

        try:
            geo = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_geolocation, image_bytes, claimed_location)
        except Exception:
            geo = {"verdict": "inconclusive", "has_gps": False}

        try:
            cred = await loop.run_in_executor(getattr(app.state, "executor", None), analyze_credibility, source_name, claim, source_url) if (source_name.strip() or claim.strip()) else None
        except Exception:
            cred = None

        try:
            hm = await loop.run_in_executor(getattr(app.state, "executor", None), generate_heatmap, image_bytes)
        except Exception:
            hm = {}

        # Generate the PDF in executor (it's CPU-bound / blocking)
        pdf_bytes = await loop.run_in_executor(getattr(app.state, "executor", None), generate_certificate,
            file_hash, image.filename or "uploaded_image", auth, ctx, fc, geo, cred, hm)

        # ── Persist report to Supabase ────────────────────────────
        try:
            asyncio.ensure_future(loop.run_in_executor(getattr(app.state, "executor", None), save_report, file_hash, image.filename or "uploaded_image", pdf_bytes))
        except Exception as e:
            logger.error(f"Supabase report storage failed: {e}")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="TrustCheck_Report_{file_hash[:8]}.pdf"'
            },
        )
    except Exception as e:
        logger.exception("Catastrophic failure in certificate generation")
        return Response(content=f"Forensic Engine Failure: {str(e)}", status_code=500)


# ═══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
