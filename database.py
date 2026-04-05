"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — Supabase Persistence Layer (database.py)
══════════════════════════════════════════════════════════════════════════════

Handles all Supabase operations:
  - Client initialization
  - Analysis results storage & retrieval
  - File upload to Supabase Storage
  - Report history

Tables expected in Supabase:
  analyses     → stores every analysis run + JSON results
  reports      → stores generated PDF certificate metadata

Storage buckets:
  uploads      → original uploaded files
  reports      → generated PDF certificates
  heatmaps     → heatmap overlay images
══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import logging
import datetime
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("trustcheck.database")

# ─────────────────────────────────────────────────────────────
# SUPABASE CLIENT INIT
# ─────────────────────────────────────────────────────────────

_supabase_client = None


def get_supabase():
    """
    Lazy-initialize and return the Supabase client.
    Returns None if credentials are not configured (graceful degradation).
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_KEY not set. "
            "Database persistence is disabled — results will be returned but not stored."
        )
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        logger.info("Supabase client connected successfully.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def is_connected() -> bool:
    """Check if Supabase is available."""
    return get_supabase() is not None


# ─────────────────────────────────────────────────────────────
# ANALYSIS RESULTS — CRUD
# ─────────────────────────────────────────────────────────────

def save_analysis(
    file_hash: str,
    filename: str,
    analysis_type: str,
    results: Dict[str, Any],
) -> Optional[Dict]:
    """
    Persist an analysis result to the `analyses` table.

    Args:
        file_hash: SHA-256 hash of the uploaded file
        filename: Original filename
        analysis_type: "image" | "video" | "batch"
        results: Full JSON results dict from the analysis pipeline

    Returns:
        The inserted row dict, or None if Supabase is unavailable.
    """
    sb = get_supabase()
    if not sb:
        return None

    # Strip non-serialisable bytes from results before storing
    clean_results = _strip_bytes(results)

    row = {
        "file_hash": file_hash,
        "filename": filename,
        "analysis_type": analysis_type,
        "results": json.dumps(clean_results),
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    try:
        response = sb.table("analyses").insert(row).execute()
        if response.data:
            logger.info(f"Analysis saved: {file_hash[:12]}... ({analysis_type})")
            return response.data[0]
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")

    return None


def get_analysis(file_hash: str) -> Optional[Dict]:
    """Retrieve the most recent analysis for a given file hash."""
    sb = get_supabase()
    if not sb:
        return None

    try:
        response = (
            sb.table("analyses")
            .select("*")
            .eq("file_hash", file_hash)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            row = response.data[0]
            row["results"] = json.loads(row["results"])
            return row
    except Exception as e:
        logger.error(f"Failed to retrieve analysis: {e}")

    return None


def get_recent_analyses(limit: int = 20) -> List[Dict]:
    """Retrieve recent analyses for dashboard display."""
    sb = get_supabase()
    if not sb:
        return []

    try:
        response = (
            sb.table("analyses")
            .select("id, file_hash, filename, analysis_type, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to retrieve recent analyses: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# SUPABASE STORAGE — FILE UPLOADS
# ─────────────────────────────────────────────────────────────

def upload_file(
    bucket: str,
    path: str,
    file_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> Optional[str]:
    """
    Upload a file to Supabase Storage.

    Args:
        bucket: Storage bucket name ("uploads", "reports", "heatmaps")
        path: File path within the bucket (e.g., "abc123/image.jpg")
        file_bytes: Raw file bytes
        content_type: MIME type

    Returns:
        Public URL of the uploaded file, or None.
    """
    sb = get_supabase()
    if not sb:
        return None

    try:
        sb.storage.from_(bucket).upload(
            path,
            file_bytes,
            file_options={"content-type": content_type},
        )
        public_url = sb.storage.from_(bucket).get_public_url(path)
        logger.info(f"File uploaded to {bucket}/{path}")
        return public_url
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        return None


def get_file_url(bucket: str, path: str) -> Optional[str]:
    """Get the public URL for a file in Supabase Storage."""
    sb = get_supabase()
    if not sb:
        return None

    try:
        return sb.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        logger.error(f"Failed to get file URL: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# REPORT STORAGE
# ─────────────────────────────────────────────────────────────

def save_report(
    file_hash: str,
    filename: str,
    pdf_bytes: bytes,
) -> Optional[Dict]:
    """
    Save a generated PDF report to Supabase Storage + record in DB.

    Returns dict with: id, file_hash, report_url
    """
    sb = get_supabase()
    if not sb:
        return None

    # Upload PDF to storage
    storage_path = f"{file_hash[:16]}/{filename}.pdf"
    report_url = upload_file("reports", storage_path, pdf_bytes, "application/pdf")

    # Record in DB
    row = {
        "file_hash": file_hash,
        "filename": filename,
        "report_url": report_url or "",
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    try:
        response = sb.table("reports").insert(row).execute()
        if response.data:
            logger.info(f"Report saved: {file_hash[:12]}...")
            return response.data[0]
    except Exception as e:
        logger.error(f"Failed to save report: {e}")

    return None


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _strip_bytes(obj):
    """
    Recursively strip bytes values from a dict/list so it's JSON-serialisable.
    Bytes are replaced with a placeholder string.
    """
    if isinstance(obj, dict):
        return {k: _strip_bytes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_bytes(item) for item in obj]
    elif isinstance(obj, bytes):
        return f"[binary {len(obj)} bytes]"
    else:
        return obj
