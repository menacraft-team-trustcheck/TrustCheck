"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PIPELINE B.3: Geolocation Verification
══════════════════════════════════════════════════════════════════════════════

Extracts EXIF GPS metadata from uploaded images using piexif, then
reverse-geocodes via OpenStreetMap Nominatim API to produce a human-readable
location.  Compares the detected location against user-stated location.

Pipeline:
  1. Extract EXIF data (GPS, DateTime, Camera info) from image bytes
  2. Convert GPS coordinates from DMS (degrees/minutes/seconds) to decimal
  3. Reverse geocode via Nominatim → address & country
  4. Compare geocoded location vs. claimed location
  5. Return match assessment
══════════════════════════════════════════════════════════════════════════════
"""

import io
import re
from typing import Dict, Any, Optional, Tuple

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

import requests
from PIL import Image
from llm_router import route_text

# ─────────────────────────────────────────────────────────────
# NOMINATIM CONFIGURATION
# ─────────────────────────────────────────────────────────────

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_USER_AGENT = "MenaCraftTrustCheck/2.0 (hackathon-project)"


# ─────────────────────────────────────────────────────────────
# EXIF EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_exif(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract complete EXIF forensic profile from image bytes.
    Returns ALL available metadata — camera, timing, settings, GPS, software.
    """
    result = {
        "gps_lat":          None,
        "gps_lon":          None,
        "datetime_original": None,
        "datetime_digitized": None,
        "camera_make":      None,
        "camera_model":     None,
        "software":         None,
        "iso":              None,
        "f_number":         None,
        "exposure_time":    None,
        "focal_length":     None,
        "flash":            None,
        "orientation":      None,
        "image_width":      None,
        "image_height":     None,
        "has_gps":          False,
        "raw_gps":          None,
        "gps_altitude":     None,
        "gps_date":         None,
    }

    # Also try PIL for basic info
    try:
        img = Image.open(io.BytesIO(image_bytes))
        result["image_width"]  = img.width
        result["image_height"] = img.height
    except Exception:
        pass

    if not PIEXIF_AVAILABLE:
        result["error"] = "piexif library not installed — run: pip install piexif"
        return result

    try:
        exif_dict = piexif.load(image_bytes)
    except Exception as e:
        result["error"] = f"No EXIF block found: {e}"
        return result

    # ── IFD 0 — Image / Camera info ─────────────────────────────
    ifd0 = exif_dict.get("0th", {})
    if piexif.ImageIFD.Make        in ifd0: result["camera_make"]  = _decode_exif_value(ifd0[piexif.ImageIFD.Make])
    if piexif.ImageIFD.Model       in ifd0: result["camera_model"] = _decode_exif_value(ifd0[piexif.ImageIFD.Model])
    if piexif.ImageIFD.Software    in ifd0: result["software"]     = _decode_exif_value(ifd0[piexif.ImageIFD.Software])
    if piexif.ImageIFD.Orientation in ifd0: result["orientation"]  = ifd0[piexif.ImageIFD.Orientation]
    if piexif.ImageIFD.ImageWidth  in ifd0: result["image_width"]  = ifd0[piexif.ImageIFD.ImageWidth]
    if piexif.ImageIFD.ImageLength in ifd0: result["image_height"] = ifd0[piexif.ImageIFD.ImageLength]

    # ── Exif IFD — Capture settings ───────────────────────────────
    exif_ifd = exif_dict.get("Exif", {})
    if piexif.ExifIFD.DateTimeOriginal  in exif_ifd:
        result["datetime_original"]  = _decode_exif_value(exif_ifd[piexif.ExifIFD.DateTimeOriginal])
    if piexif.ExifIFD.DateTimeDigitized in exif_ifd:
        result["datetime_digitized"] = _decode_exif_value(exif_ifd[piexif.ExifIFD.DateTimeDigitized])
    if piexif.ExifIFD.ISOSpeedRatings   in exif_ifd:
        iso = exif_ifd[piexif.ExifIFD.ISOSpeedRatings]
        result["iso"] = iso if isinstance(iso, int) else (iso[0] if isinstance(iso, (list, tuple)) else str(iso))
    if piexif.ExifIFD.FNumber in exif_ifd:
        fn = exif_ifd[piexif.ExifIFD.FNumber]
        if isinstance(fn, tuple) and len(fn) == 2 and fn[1] != 0:
            result["f_number"] = round(fn[0] / fn[1], 1)
    if piexif.ExifIFD.ExposureTime in exif_ifd:
        et = exif_ifd[piexif.ExifIFD.ExposureTime]
        if isinstance(et, tuple) and len(et) == 2 and et[1] != 0:
            result["exposure_time"] = f"{et[0]}/{et[1]}s"
    if piexif.ExifIFD.FocalLength in exif_ifd:
        fl = exif_ifd[piexif.ExifIFD.FocalLength]
        if isinstance(fl, tuple) and len(fl) == 2 and fl[1] != 0:
            result["focal_length"] = round(fl[0] / fl[1], 1)
    if piexif.ExifIFD.Flash in exif_ifd:
        flash_val = exif_ifd[piexif.ExifIFD.Flash]
        result["flash"] = "fired" if flash_val & 0x1 else "did not fire"

    # ── GPS IFD ───────────────────────────────────────────────────
    gps_ifd = exif_dict.get("GPS", {})
    if gps_ifd:
        lat = _extract_gps_coord(gps_ifd, piexif.GPSIFD.GPSLatitude,  piexif.GPSIFD.GPSLatitudeRef)
        lon = _extract_gps_coord(gps_ifd, piexif.GPSIFD.GPSLongitude, piexif.GPSIFD.GPSLongitudeRef)
        if lat is not None and lon is not None:
            result["gps_lat"]  = lat
            result["gps_lon"]  = lon
            result["has_gps"]  = True
            result["raw_gps"]  = {"latitude": lat, "longitude": lon}
        if piexif.GPSIFD.GPSAltitude in gps_ifd:
            alt = gps_ifd[piexif.GPSIFD.GPSAltitude]
            if isinstance(alt, tuple) and alt[1] != 0:
                result["gps_altitude"] = round(alt[0] / alt[1], 1)
        if piexif.GPSIFD.GPSDateStamp in gps_ifd:
            result["gps_date"] = _decode_exif_value(gps_ifd[piexif.GPSIFD.GPSDateStamp])

    return result


def _decode_exif_value(value) -> str:
    """Safely decode EXIF byte strings to UTF-8."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip("\x00").strip()
    return str(value)


def _extract_gps_coord(gps_ifd: dict, coord_tag: int, ref_tag: int) -> Optional[float]:
    """
    Extract and convert GPS coordinates from EXIF DMS format to decimal degrees.
    DMS = ((deg_num, deg_den), (min_num, min_den), (sec_num, sec_den))
    """
    if coord_tag not in gps_ifd:
        return None

    dms = gps_ifd[coord_tag]
    try:
        degrees = dms[0][0] / dms[0][1]
        minutes = dms[1][0] / dms[1][1]
        seconds = dms[2][0] / dms[2][1]
    except (IndexError, ZeroDivisionError, TypeError):
        return None

    decimal = degrees + minutes / 60.0 + seconds / 3600.0

    # Apply direction reference (S/W = negative)
    ref = gps_ifd.get(ref_tag, b"N")
    if isinstance(ref, bytes):
        ref = ref.decode("utf-8", errors="replace")
    if ref.upper() in ("S", "W"):
        decimal = -decimal

    return round(decimal, 6)


# ─────────────────────────────────────────────────────────────
# REVERSE GEOCODING (OPENSTREETMAP NOMINATIM)
# ─────────────────────────────────────────────────────────────

def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    """
    Reverse geocode GPS coordinates using OpenStreetMap Nominatim API.

    Returns: dict with display_name, country, city, state, etc.
    """
    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1,
                "zoom": 14,
            },
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        address = data.get("address", {})
        return {
            "display_name": data.get("display_name", "Unknown"),
            "country": address.get("country", ""),
            "country_code": address.get("country_code", ""),
            "state": address.get("state", ""),
            "city": address.get("city", address.get("town", address.get("village", ""))),
            "road": address.get("road", ""),
            "lat": lat,
            "lon": lon,
        }
    except Exception as e:
        return {
            "display_name": f"Coordinates: {lat}, {lon}",
            "country": "",
            "error": str(e),
            "lat": lat,
            "lon": lon,
        }


# ─────────────────────────────────────────────────────────────
# LOCATION COMPARISON
# ─────────────────────────────────────────────────────────────

def compare_locations(
    geocoded: Dict[str, Any],
    claimed_location: str,
) -> Dict[str, Any]:
    """
    Compare the EXIF-derived geocoded location against the user's stated
    location using LLM reasoning.

    Returns:
        dict with: match, confidence, explanation
    """
    if not claimed_location.strip():
        return {
            "match": "no_claim",
            "confidence": 0.0,
            "explanation": "No location claim provided for comparison.",
        }

    geocoded_str = geocoded.get("display_name", "Unknown")

    prompt = f"""Compare these two locations and determine if they refer to the same place:

LOCATION FROM IMAGE METADATA (EXIF GPS): {geocoded_str}
  - Country: {geocoded.get('country', 'Unknown')}
  - City: {geocoded.get('city', 'Unknown')}
  - Coordinates: {geocoded.get('lat', 'N/A')}, {geocoded.get('lon', 'N/A')}

CLAIMED LOCATION: {claimed_location}

Respond in this exact JSON format:
{{
    "match": "<match|mismatch|partial|uncertain>",
    "confidence": <float 0.0-1.0>,
    "explanation": "Brief explanation of the comparison"
}}"""

    raw = route_text(prompt, temperature=0.1)

    # Parse response
    try:
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        import json
        parsed = json.loads(cleaned)
        return {
            "match": parsed.get("match", "uncertain"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "explanation": parsed.get("explanation", ""),
        }
    except Exception:
        return {
            "match": "uncertain",
            "confidence": 0.5,
            "explanation": raw[:300],
        }


# ─────────────────────────────────────────────────────────────
# UNIFIED GEOLOCATION ANALYSIS
# ─────────────────────────────────────────────────────────────

def _flag_software(software: str | None) -> list:
    """Flag software that typically indicates post-processing."""
    flags = []
    if not software:
        return flags
    s = software.lower()
    EDIT_SIGNATURES = [
        ("photoshop",  "Adobe Photoshop detected — manual editing likely"),
        ("lightroom",  "Adobe Lightroom detected — image processed"),
        ("gimp",       "GIMP (GNU Image Manipulation) detected"),
        ("affinity",   "Affinity Photo detected — post-processing confirmed"),
        ("snapseed",   "Snapseed (mobile editor) detected"),
        ("vsco",       "VSCO filter app detected"),
        ("facetune",   "Facetune detected — face retouching likely"),
        ("instagram",  "Instagram filter applied"),
        ("canva",      "Canva design tool — image may be composite"),
        ("whatsapp",   "WhatsApp re-compression detected (quality loss)"),
        ("telegram",   "Telegram re-compression detected"),
    ]
    for keyword, message in EDIT_SIGNATURES:
        if keyword in s:
            flags.append(message)
    return flags


def analyze_geolocation(
    image_bytes: bytes,
    claimed_location: str = "",
) -> Dict[str, Any]:
    """
    Full geolocation + EXIF forensics pipeline:
      1. Extract comprehensive EXIF metadata (camera, settings, software, GPS)
      2. Run software forensics (detect editing apps)
      3. Detect GPS-stripping (has camera model that supports GPS but no coords)
      4. Reverse geocode if GPS found
      5. Compare with claimed location
      6. Return full forensic profile
    """
    exif = extract_exif(image_bytes)

    # ── Software forensics ────────────────────────────────────────
    software_flags = _flag_software(exif.get("software"))

    # ── Build camera info block ───────────────────────────────────
    camera_info = {
        "make":          exif.get("camera_make"),
        "model":         exif.get("camera_model"),
        "software":      exif.get("software"),
        "datetime":      exif.get("datetime_original"),
        "datetime_digitized": exif.get("datetime_digitized"),
        "iso":           exif.get("iso"),
        "f_number":      exif.get("f_number"),
        "exposure_time": exif.get("exposure_time"),
        "focal_length":  exif.get("focal_length"),
        "flash":         exif.get("flash"),
        "orientation":   exif.get("orientation"),
        "resolution":    (
            f"{exif['image_width']}×{exif['image_height']}px"
            if exif.get("image_width") and exif.get("image_height") else None
        ),
    }

    result = {
        "has_gps":             exif.get("has_gps", False),
        "exif_data":           exif,
        "geocoded_location":   None,
        "location_comparison": None,
        "camera_info":         camera_info,
        "software_flags":      software_flags,
        "forensic_signals":    [],
        "verdict":             "no_gps_data",
    }

    # ── Forensic signal collection ────────────────────────────────
    signals = list(software_flags)  # start with software flags

    if exif.get("software"):
        signals.insert(0, f"Software tag present: '{exif['software']}' — possible post-processing")

    if not exif.get("camera_make") and not exif.get("camera_model"):
        signals.append("No camera make/model — EXIF may have been stripped or image is a screenshot")

    if exif.get("camera_make") and not exif.get("has_gps"):
        # Known GPS-capable phones/cameras that rarely omit GPS involuntarily
        gps_capable = ["samsung", "apple", "huawei", "xiaomi", "pixel", "oneplus", "iphone"]
        make_lower = exif["camera_make"].lower()
        if any(brand in make_lower for brand in gps_capable):
            signals.append(
                f"⚠️ GPS-stripping detected: {exif['camera_make']} devices embed GPS by default "
                f"— coordinates were deliberately removed (high forensic suspicion)"
            )

    result["forensic_signals"] = signals

    # ── Build human-readable details ──────────────────────────────
    meta_parts = []
    if camera_info["make"] or camera_info["model"]:
        meta_parts.append(f"Camera: {camera_info['make'] or ''} {camera_info['model'] or ''}")
    if camera_info["datetime"]:
        meta_parts.append(f"Captured: {camera_info['datetime']}")
    if camera_info["iso"]:
        meta_parts.append(f"ISO {camera_info['iso']}")
    if camera_info["f_number"]:
        meta_parts.append(f"f/{camera_info['f_number']}")
    if camera_info["exposure_time"]:
        meta_parts.append(f"Exposure {camera_info['exposure_time']}")
    if camera_info["focal_length"]:
        meta_parts.append(f"Focal {camera_info['focal_length']}mm")

    if not exif.get("has_gps"):
        if meta_parts:
            result["details"] = (
                f"No GPS coordinates found. Full EXIF profile extracted: {' | '.join(meta_parts)}. "
                + (f"Forensic flags: {'; '.join(signals)}" if signals else "No software editing flags.")
            )
        else:
            result["details"] = (
                "No GPS metadata found. No camera EXIF data present — "
                "image may be a screenshot, render, or have had all metadata stripped."
            )
        return result

    # ── Reverse geocode ───────────────────────────────────────────
    geocoded = reverse_geocode(exif["gps_lat"], exif["gps_lon"])
    result["geocoded_location"] = geocoded

    if claimed_location.strip():
        comparison = compare_locations(geocoded, claimed_location)
        result["location_comparison"] = comparison
        result["verdict"] = comparison["match"]
        result["details"] = comparison["explanation"]
    else:
        result["verdict"] = "gps_found"
        result["details"] = (
            f"GPS location detected: {geocoded.get('display_name', 'Unknown')}. "
            + (f" | {' | '.join(meta_parts)}" if meta_parts else "")
        )

    return result


def get_geo_verdict_display(verdict: str) -> tuple:
    """Return (emoji, color, label) for geolocation verdicts."""
    mapping = {
        "match":        ("✅", "#00C853", "Location Match"),
        "mismatch":     ("❌", "#FF1744", "Location Mismatch"),
        "partial":      ("⚠️", "#FF9100", "Partial Match"),
        "uncertain":    ("❓", "#9E9E9E", "Uncertain"),
        "no_gps_data":  ("📍", "#9E9E9E", "No GPS Data"),
        "gps_found":    ("📍", "#00C853", "GPS Found"),
        "no_claim":     ("📍", "#9E9E9E", "No Claim"),
    }
    return mapping.get(verdict, ("❓", "#9E9E9E", "Unknown"))
