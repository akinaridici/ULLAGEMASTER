"""Register DejaVu fonts (full Turkish glyph coverage) for PDF generation."""

import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")

FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

_registered = False


def ensure_fonts() -> tuple[str, str]:
    """Register fonts once; fall back to Helvetica if the files are missing."""
    global _registered, FONT, FONT_BOLD
    if _registered:
        return FONT, FONT_BOLD
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))
    except Exception:
        FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"
    _registered = True
    return FONT, FONT_BOLD


def normalize_hex(color: str, fallback: str = "#FFFFFF") -> str:
    """Expand #abc to #aabbcc and validate; ReportLab misparses shorthand hex."""
    c = (color or "").strip()
    if not c.startswith("#"):
        return fallback
    h = c[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return fallback
    try:
        int(h, 16)
    except ValueError:
        return fallback
    return f"#{h}"
