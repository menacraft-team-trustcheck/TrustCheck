"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — PDF Certificate Generator
══════════════════════════════════════════════════════════════════════════════

Uses fpdf2 to generate a professional, downloadable PDF verification report.
Includes SHA-256 hash, QR code, and full results from all 3 analysis axes.
══════════════════════════════════════════════════════════════════════════════
"""

import io
import os
import hashlib
import datetime
from typing import Dict, Any, Optional

from fpdf import FPDF, Align
import qrcode
from PIL import Image
import tempfile


class TrustCheckCertificate(FPDF):
    """Custom FPDF subclass with branded header/footer."""

    def header(self):
        self.set_fill_color(14, 17, 23)
        self.rect(0, 0, 210, 25, "F")
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 200, 83)
        self.cell(0, 12, "MENACRAFT TRUSTCHECK", ln=False, align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(170, 170, 170)
        self.cell(0, 12, "Digital Content Verification Certificate", ln=True, align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
                  align="C")


def _generate_qr(data: str) -> str:
    """Generate a QR code image and return the temp file path."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00C853", back_color="#0E1117")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    return tmp.name


def _add_section(pdf: FPDF, title: str, color: tuple = (0, 200, 83)):
    """Add a styled section header."""
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_draw_color(*color)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 180, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font("Helvetica", "", 10)


def _add_kv(pdf: FPDF, key: str, value: str):
    """Add a key-value row."""
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(55, 7, f"{key}:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 7, str(value))


def generate_certificate(
    file_hash: str,
    filename: str,
    authenticity_result: Optional[Dict] = None,
    context_result: Optional[Dict] = None,
    fact_check_result: Optional[Dict] = None,
    geo_result: Optional[Dict] = None,
    credibility_result: Optional[Dict] = None,
    heatmap_result: Optional[Dict] = None,
) -> bytes:
    """
    Generate a full PDF verification certificate.

    Returns: PDF file as bytes
    """
    pdf = TrustCheckCertificate()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── File Identity ────────────────────────────────────────
    _add_section(pdf, "FILE IDENTITY")
    _add_kv(pdf, "Filename", filename)
    _add_kv(pdf, "SHA-256 Hash", file_hash)
    _add_kv(pdf, "Analysis Date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    pdf.ln(4)

    # ── QR Code ──────────────────────────────────────────────
    qr_data = f"trustcheck://verify/{file_hash[:16]}"
    qr_path = _generate_qr(qr_data)
    try:
        pdf.image(qr_path, x=160, y=35, w=35)
    except Exception:
        pass
    finally:
        try:
            os.unlink(qr_path)
        except OSError:
            pass

    # ── Axis A: Content Authenticity ─────────────────────────
    if authenticity_result:
        _add_section(pdf, "AXIS A: CONTENT AUTHENTICITY")
        _add_kv(pdf, "Verdict", authenticity_result.get("verdict", "N/A").replace("_", " ").title())
        _add_kv(pdf, "Confidence", f"{authenticity_result.get('confidence', 0):.1%}")
        _add_kv(pdf, "Model", authenticity_result.get("model_used", "N/A"))
        details = authenticity_result.get("details", "")
        if details:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, details)
        pdf.ln(4)

    # ── Axis B: Contextual Consistency ───────────────────────
    if context_result:
        _add_section(pdf, "AXIS B.1: CONTEXTUAL CONSISTENCY", (255, 145, 0))
        _add_kv(pdf, "Verdict", context_result.get("verdict", "N/A").title())
        _add_kv(pdf, "Match Score", f"{context_result.get('match_score', 0):.1%}")
        analysis = context_result.get("analysis", "")
        if analysis:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, analysis)
        pdf.ln(4)

    if fact_check_result:
        _add_section(pdf, "AXIS B.2: FACT CHECK", (255, 145, 0))
        _add_kv(pdf, "Verdict", fact_check_result.get("verdict", "N/A").replace("_", " ").title())
        _add_kv(pdf, "Score", f"{fact_check_result.get('score', 0):.1%}")
        _add_kv(pdf, "Source", fact_check_result.get("source", "N/A"))
        details = fact_check_result.get("details", "")
        if details:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, details[:500])
        pdf.ln(4)

    if geo_result:
        _add_section(pdf, "AXIS B.3: GEOLOCATION", (255, 145, 0))
        _add_kv(pdf, "GPS Data", "Found" if geo_result.get("has_gps") else "Not Found")
        loc = geo_result.get("geocoded_location", {})
        if loc:
            _add_kv(pdf, "Location", loc.get("display_name", "N/A"))
        _add_kv(pdf, "Verdict", geo_result.get("verdict", "N/A").replace("_", " ").title())
        pdf.ln(4)

    # ── Axis ELA: Image Forensics Heatmap ─────────────────────
    if heatmap_result:
        _add_section(pdf, "FORENSIC ERROR LEVEL ANALYSIS (ELA)", (156, 39, 176))
        _add_kv(pdf, "Method", heatmap_result.get("method", "ELA").upper())
        _add_kv(pdf, "Avg Error Level", f"{heatmap_result.get('ela_mean', 0):.2f}")
        _add_kv(pdf, "Max Error Level", f"{heatmap_result.get('ela_max', 0):.2f}")
        
        hotspots = heatmap_result.get("hotspots", [])
        _add_kv(pdf, "Hotspots Detected", str(len(hotspots)))
        
        assessment = heatmap_result.get("overall_assessment", "")
        if assessment:
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(0, 6, f"Assessment: {assessment}")
        pdf.ln(4)

    # ── Axis C: Source Credibility ───────────────────────────
    if credibility_result:
        _add_section(pdf, "AXIS C: SOURCE CREDIBILITY", (33, 150, 243))
        _add_kv(pdf, "Verdict", credibility_result.get("verdict", "N/A").replace("_", " ").title())
        _add_kv(pdf, "Score", f"{credibility_result.get('credibility_score', 0):.1%}")
        _add_kv(pdf, "Bias", f"{credibility_result.get('bias_direction', 'N/A')} ({credibility_result.get('bias_severity', 'N/A')})")
        analysis = credibility_result.get("analysis", "")
        if analysis:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, analysis[:500])

        risks = credibility_result.get("risk_indicators", [])
        if risks:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, "Risk Indicators:", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for r in risks[:5]:
                pdf.cell(0, 5, f"  - {r}", ln=True)
        pdf.ln(4)

    # ── Disclaimer ───────────────────────────────────────────
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5,
        "DISCLAIMER: This report is generated by AI-assisted analysis tools and should be used "
        "as one input among many in verification workflows. Results are probabilistic, not definitive. "
        "MenaCraft TrustCheck is a hackathon project and makes no guarantees of accuracy."
    )

    # Return PDF bytes
    return pdf.output()
