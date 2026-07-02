"""
Visual stowage plan PDF, ported from the desktop export/visual_stowage.py.

Layout (landscape A4): title, cargo summary table (top left), voyage info and
final drafts (top right), then the ship strip — SLOP tanks leftmost (stern),
tank pairs in descending number order, Port row on top, Starboard row below,
each cell showing ULL / MT / CBM / % with the parcel colour band touching the
centre line.
"""

import io
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from .fonts import ensure_fonts, normalize_hex

FONT, FONT_BOLD = ensure_fonts()

PORT_BODY = colors.HexColor("#60A5FA")
STBD_BODY = colors.HexColor("#86EFAC")
SLOP_COLOR = "#9CA3AF"


def _contrast(hex_color: str) -> colors.Color:
    h = normalize_hex(hex_color).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return colors.black if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.5 else colors.white


def _group_tanks(rows: list) -> tuple[dict, dict]:
    """Group calc rows into {number: {side: row}} plus {side: row} for slops."""
    groups: dict = {}
    slops: dict = {}
    for r in rows:
        tid = r["tank_id"]
        upper = tid.upper()
        if "SLOP" in upper:
            slops["P" if "P" in upper.replace("SLOP", "") else "S"] = r
            continue
        digits = re.sub(r"\D", "", tid)
        if not digits:
            continue
        num = int(digits)
        side = "S" if upper.endswith("S") else ("P" if upper.endswith("P") else "C")
        groups.setdefault(num, {})[side] = r
    return groups, slops


def _fmt(value, spec: str) -> str:
    return format(value, spec) if isinstance(value, (int, float)) else ""


def _draw_cell(c: canvas.Canvas, x, y, w, h, row: dict, parcel: dict | None, side: str):
    tid = row["tank_id"]
    band_color, band_text = colors.white, colors.black
    pname = ""
    if parcel:
        pname = parcel.get("name") or ""
        hexc = normalize_hex(parcel.get("color") or "#FFFFFF")
        band_color = colors.HexColor(hexc)
        band_text = _contrast(hexc)
    elif row.get("parcel_id") == "0":
        pname = "SLOP"
        band_color, band_text = colors.HexColor(SLOP_COLOR), colors.black
    receiver = (parcel.get("receiver") or "")[:20] if parcel else ""

    header_h = footer_h = receiver_h = 0.5 * cm
    data_h = h - header_h - footer_h - receiver_h
    c.setStrokeColor(colors.black)

    def box(bx, by, bw, bh, fill):
        c.setFillColor(fill)
        c.rect(bx, by, bw, bh, fill=1, stroke=1)

    def data_body(by):
        box(x, by, w, data_h, PORT_BODY if side in ("P", "C") else STBD_BODY)
        c.setFillColor(colors.white if side in ("P", "C") else colors.black)
        c.setFont(FONT_BOLD, 8)
        ty = by + data_h - 0.4 * cm
        step = 0.4 * cm
        for label, val in (
            ("ULL", _fmt(row.get("ullage"), ".0f")),
            ("MT", _fmt(row.get("mt_air"), ".0f")),
            ("CBM", _fmt(row.get("gov"), ".0f")),
            ("%", _fmt(row.get("fill_percent"), ".1f")),
        ):
            c.drawString(x + 2, ty, label)
            c.drawRightString(x + w - 2, ty, val)
            ty -= step

    if side in ("P", "C"):
        # top: tank id / receiver / data / coloured grade band at centre line
        box(x, y + h - header_h, w, header_h, colors.white)
        c.setFillColor(colors.black)
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(x + w / 2, y + h - header_h + 0.15 * cm, tid)

        box(x, y + h - header_h - receiver_h, w, receiver_h, colors.white)
        c.setFillColor(colors.black)
        c.setFont(FONT, 6)
        c.drawCentredString(x + w / 2, y + h - header_h - receiver_h + 0.15 * cm, receiver)

        data_body(y + footer_h)

        box(x, y, w, footer_h, band_color)
        c.setFillColor(band_text)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(x + w / 2, y + 0.15 * cm, pname)
    else:
        # mirrored: coloured grade band at centre line / receiver / data / tank id
        box(x, y + h - header_h, w, header_h, band_color)
        c.setFillColor(band_text)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(x + w / 2, y + h - header_h + 0.15 * cm, pname)

        box(x, y + h - header_h - receiver_h, w, receiver_h, colors.white)
        c.setFillColor(colors.black)
        c.setFont(FONT, 6)
        c.drawCentredString(x + w / 2, y + h - header_h - receiver_h + 0.15 * cm, receiver)

        data_body(y + footer_h)

        box(x, y, w, footer_h, colors.white)
        c.setFillColor(colors.black)
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(x + w / 2, y + 0.15 * cm, tid)


def export_stowage_pdf(ship_name: str, voyage: dict, calc: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    width, height = landscape(A4)
    c.setTitle("Stowage Plan")

    name = ship_name.strip()
    prefix = "" if name.upper().startswith(("M/T", "MT ", "M.T")) else "M/T "
    title = f"{prefix}{name} STOWAGE PLAN" if name else "STOWAGE PLAN"
    c.setFont(FONT_BOLD, 18)
    c.drawCentredString(width / 2, height - 1.5 * cm, title)

    c.setFont(FONT_BOLD, 10)
    c.drawRightString(width - 1 * cm, height - 2.5 * cm, f"VOYAGE: {voyage.get('voyage_number', '')}")
    c.drawRightString(width - 1 * cm, height - 3.0 * cm,
                      f"PORT/TERMINAL: {voyage.get('port', '')} / {voyage.get('terminal', '')}")

    rows = calc["rows"]
    parcels_by_id = {str(p["id"]): p for p in voyage.get("parcels", [])}

    # --- cargo summary (top left) ---
    row_h = 0.6 * cm
    col_widths = [4 * cm, 3 * cm, 2 * cm, 2.5 * cm, 2.5 * cm]
    c_x, c_y = 1 * cm, height - 2.5 * cm
    c.setFillColor(colors.HexColor(SLOP_COLOR))
    c.rect(c_x, c_y, sum(col_widths), row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_BOLD, 8)
    curr_x = c_x
    for i, text in enumerate(["TERMINAL", "GRADE", "DENSITY", "AVG.TEMP", "WEIGHT (MT)"]):
        c.drawString(curr_x + 2, c_y + 0.15 * cm, text)
        curr_x += col_widths[i]
    c_y -= row_h

    summary: dict = {}
    for r in rows:
        pid = r.get("parcel_id")
        if not pid:
            continue
        if pid not in summary:
            parcel = parcels_by_id.get(pid)
            summary[pid] = {
                "term": (parcel.get("receiver") or "")[:15] if parcel else "",
                "grade": ((parcel.get("name") or "") if parcel else ("SLOP" if pid == "0" else "?"))[:10],
                "dens": (parcel.get("density_vac") if parcel else r.get("density_vac")) or 0.0,
                "color": (parcel.get("color") if parcel else "#E5E7EB") or "#FFFFFF",
                "temp": r.get("temp_celsius"),
                "mt": 0.0,
            }
        summary[pid]["mt"] += r.get("mt_air") or 0.0

    for data in summary.values():
        bg = colors.HexColor(normalize_hex(data["color"]))
        c.setFillColor(bg)
        c.rect(c_x, c_y, sum(col_widths), row_h, fill=1, stroke=1)
        c.setFillColor(_contrast(data["color"]))
        c.setFont(FONT, 8)
        curr_x = c_x
        for i, text in enumerate([
            data["term"], data["grade"], f"{data['dens']:.4f}",
            _fmt(data["temp"], ".1f"),
        ]):
            c.drawString(curr_x + 2, c_y + 0.15 * cm, text)
            curr_x += col_widths[i]
        c.drawRightString(curr_x + col_widths[4] - 2, c_y + 0.15 * cm, f"{data['mt']:.0f}")
        c_y -= row_h

    # --- final drafts (top right) ---
    d_x, d_y, d_w = width - 5 * cm, height - 4 * cm, 4 * cm
    c.setFillColor(colors.lightgrey)
    c.rect(d_x, d_y, d_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_BOLD, 8)
    c.drawCentredString(d_x + d_w / 2, d_y + 0.15 * cm, "FINAL DRAFTS")
    for label, value in (("Draft FWD", voyage.get("draft_fwd", 0.0)), ("Draft AFT", voyage.get("draft_aft", 0.0))):
        d_y -= row_h
        c.setFillColor(colors.white)
        c.rect(d_x, d_y, d_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(d_x + 2, d_y + 0.15 * cm, label)
        c.drawRightString(d_x + d_w - 2, d_y + 0.15 * cm, f"{value:.2f}")

    # --- ship strip ---
    groups, slops = _group_tanks(rows)
    sorted_nums = sorted(groups.keys(), reverse=True)

    box_w, gap, cell_h = 2.4 * cm, 0.1 * cm, 5.0 * cm
    col_count = len(sorted_nums) + (1 if slops else 0)
    total_w = col_count * (box_w + gap)
    curr_x = width / 2 - total_w / 2
    center_y = 10 * cm

    def parcel_of(row):
        return parcels_by_id.get(row.get("parcel_id") or "")

    if slops:
        if "P" in slops:
            _draw_cell(c, curr_x, center_y, box_w, cell_h, slops["P"], parcel_of(slops["P"]), "P")
        if "S" in slops:
            _draw_cell(c, curr_x, center_y - cell_h, box_w, cell_h, slops["S"], parcel_of(slops["S"]), "S")
        curr_x += box_w + gap

    for num in sorted_nums:
        group = groups[num]
        if "P" in group:
            _draw_cell(c, curr_x, center_y, box_w, cell_h, group["P"], parcel_of(group["P"]), "P")
        if "C" in group:
            _draw_cell(c, curr_x, center_y, box_w, cell_h, group["C"], parcel_of(group["C"]), "C")
        if "S" in group:
            _draw_cell(c, curr_x, center_y - cell_h, box_w, cell_h, group["S"], parcel_of(group["S"]), "S")
        curr_x += box_w + gap

    # bow marker
    c.setFont(FONT_BOLD, 10)
    c.drawString(curr_x + 0.2 * cm, center_y - 0.2 * cm, "BOW ►")

    c.save()
    return buf.getvalue()
