"""
Letter of Protest PDF (document code CBO 082), ported from the desktop
src/reporting/protest_pdf.py. English + Turkish legal text, loading (7 data
rows) or discharging (8 data rows) layouts, optional company logo, and
multi-page output (one page per parcel).
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .fonts import ensure_fonts

FONT, FONT_BOLD = ensure_fonts()

_styles = getSampleStyleSheet()
S_TITLE = ParagraphStyle("PTitle", parent=_styles["Normal"], fontSize=10, alignment=TA_CENTER, fontName=FONT_BOLD, leading=12)
S_BOLD_CENTER = ParagraphStyle("PBoldCenter", parent=_styles["Normal"], fontSize=9, alignment=TA_CENTER, fontName=FONT_BOLD)
S_NORMAL = ParagraphStyle("PNormal", parent=_styles["Normal"], fontSize=9, alignment=TA_LEFT, fontName=FONT, leading=11)
S_SMALL = ParagraphStyle("PSmall", parent=_styles["Normal"], fontSize=7, alignment=TA_LEFT, fontName=FONT, leading=9)
S_SMALL_ITALIC = ParagraphStyle("PSmallItalic", parent=_styles["Normal"], fontSize=7, alignment=TA_LEFT, fontName=FONT, textColor=colors.blue, leading=9)
S_TH = ParagraphStyle("PTh", parent=_styles["Normal"], fontSize=9, alignment=TA_CENTER, fontName=FONT_BOLD)
S_CELL = ParagraphStyle("PCell", parent=_styles["Normal"], fontSize=9, alignment=TA_RIGHT, fontName=FONT)
S_LABEL = ParagraphStyle("PLabel", parent=_styles["Normal"], fontSize=9, alignment=TA_LEFT, fontName=FONT)


def _header(elements: list, logo_bytes: bytes | None):
    if logo_bytes:
        logo = Image(io.BytesIO(logo_bytes))
        aspect = logo.imageHeight / float(logo.imageWidth)
        logo.drawWidth = 30 * mm
        logo.drawHeight = 30 * mm * aspect
        logo_obj = logo
    else:
        logo_obj = Paragraph("LOGO", S_BOLD_CENTER)

    info = Table(
        [[Paragraph("Issue No.:<br/>Issue Date:<br/>Rev. No.:<br/>Rev. Date:<br/>Page:", S_SMALL),
          Paragraph("2<br/>1.11.2024<br/>0<br/>00/00/0000<br/>1 of 1", S_SMALL)]],
        colWidths=[25 * mm, 25 * mm],
    )
    info.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    title = Table(
        [
            [Paragraph("INTEGRATED MANAGEMENT SYSTEM MANUAL<br/>Chapter 7.5", S_TITLE)],
            [Table([[Paragraph("CBO 082", S_BOLD_CENTER), Paragraph("LETTER OF PROTEST", S_BOLD_CENTER)]], colWidths=[30 * mm, 70 * mm])],
        ],
        colWidths=[100 * mm],
    )
    title.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    header = Table([[logo_obj, title, info]], colWidths=[35 * mm, 100 * mm, 50 * mm])
    header.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements += [header, Spacer(1, 3 * mm)]


def _protest_text(elements: list):
    elements.append(Paragraph(
        "<b>I, Master of the above named vessel, hereby give formal notice and lodge a Protest.</b><br/>"
        "I hold you responsible for any consequences arising from the events described below. I also reserve the right to amend this "
        "Letter Of Protest (LOP) at later date and to take action as may be deemed necessary.",
        S_NORMAL,
    ))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "<i>İşbu Protesto Mektubuyla, yukarıda adı yazılı geminin Kaptanı resmi Protesto Mektubunu sunarım. Aşağıda belirtilen durumdan ötürü "
        "karşılaşılabilecek her türlü kayıptan tarafınızın sorumlu tutulacağını bildiririm. Ayrıca bu Protesto Mektubunun ileriki bir tarihte değiştirilmesi "
        "hakkını da saklı tuttuğumu ve gerekecek aksiyonları alacağımı bildiririm.</i>",
        S_SMALL_ITALIC,
    ))
    elements.append(Spacer(1, 3 * mm))


def _footer_text(elements: list):
    elements.append(Paragraph(
        "<b>And, I hereby lodge protest accordingly, and we, hold you responsible for delays and consequences.</b> On behalf of the "
        "............... I hereby reserve the right to take such further action as may be considered necessary to protect the interest of "
        "these parties. I reserve the right to refer to this Letter of Protest at a future date and place convenient to the...............",
        S_NORMAL,
    ))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "<i>İşbu Protesto Mektubuyla, yukarıda belirtilen durumdan/bulgudan ötürü karşılaşılabilecek her türlü kayıp karşı sorumlu tutulacağınız "
        "hususunu dikkatlerinize sunarım. Tüm bu tarafların haklarını korumak üzere gerekli görülecek herşeyi yapma hakkını saklı tuttuğumu ayrıca "
        "belirtirim.</i>",
        S_SMALL_ITALIC,
    ))
    elements.append(Spacer(1, 5 * mm))


def _grade_display(p: dict) -> str:
    name = p.get("name") or "Unknown"
    receiver = p.get("receiver") or ""
    return f"{name}-{receiver}" if receiver else name


def _loading_rows(d: dict) -> list:
    return [
        ("B/L Figure", d["bl_figure"], False),
        ("Ship Figure W/O VEF", d["ship_wo_vef"], False),
        ("Quantity Difference W/O VEF", d["diff_wo_vef"], False),
        ("Difference W/O VEF ‰", d["diff_pct_wo_vef"], True),
        ("Ship Figure with VEF", d["ship_with_vef"], False),
        ("Quantity Difference with VEF", d["diff_with_vef"], False),
        ("Difference with VEF ‰", d["diff_pct_with_vef"], True),
    ]


def _discharging_rows(d: dict) -> list:
    return [
        ("B/L Figure", d["bl_figure"], False),
        ("Ship Arrival Figure", d["ship_arrival"], False),
        ("Arrival-BL diff W/O VEF ‰", d["arrival_bl_wo_pct"], True),
        ("Ship Arrival with VEF", d["ship_arrival_vef"], False),
        ("Arrival-BL diff VEF ‰", d["arrival_bl_vef_pct"], True),
        ("OUTTURN FIGURE", d["outturn"], False),
        ("OUTTURN-BL DIFF", d["outturn_bl_diff"], False),
        ("OUTTURN-BL DIFF ‰", d["outturn_bl_pct"], True),
    ]


def _build_page(elements: list, vessel_name: str, parcel: dict, operation: str, voyage: dict, logo: bytes | None):
    _header(elements, logo)

    elements.append(Paragraph(f"<b>Vessel Name:</b> {vessel_name}", S_NORMAL))
    elements.append(Paragraph("<b>Subject :</b> Difference between Ship and Shore", S_NORMAL))
    elements.append(Spacer(1, 3 * mm))

    _protest_text(elements)

    # Cargo table
    bl_date = voyage.get("date") or date.today().strftime("%d.%m.%Y")
    cargo = Table(
        [
            [Paragraph("<b>Grade, Yükün Cinsi</b>", S_TH),
             Paragraph("<b>B/L Figure, Konsimento Miktarı</b>", S_TH),
             Paragraph("<b>B/L Date, B/L Tarihi</b>", S_TH)],
            [Paragraph(_grade_display(parcel), S_BOLD_CENTER),
             Paragraph(f"{parcel['bl_figure']:,.3f} mts", S_BOLD_CENTER),
             Paragraph(str(bl_date), S_BOLD_CENTER)],
        ],
        colWidths=[60 * mm, 65 * mm, 50 * mm],
    )
    cargo.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements += [cargo, Spacer(1, 3 * mm)]

    elements.append(Paragraph("<b>Description of the Protest,</b><br/><i>Protesto Açıklaması,</i>", S_NORMAL))
    elements.append(Spacer(1, 2 * mm))

    # Data table
    if operation == "loading":
        header_text = "Discrepancy on Completion of Loading"
        rows = _loading_rows(parcel)
    else:
        header_text = "Discrepancy on Completion of Discharging (Ship has received empty tank certificate)"
        rows = _discharging_rows(parcel)

    data = [
        [Paragraph(f"<b>{header_text}</b>", S_BOLD_CENTER), ""],
        [Paragraph(f"<b>{_grade_display(parcel)}</b>", S_BOLD_CENTER), ""],
        ["", Paragraph("<b>Gross Metric Tons (in air)</b>", S_CELL)],
    ]
    for label, value, bold in rows:
        label_p = Paragraph(f"<b>{label}</b>" if bold else label, S_LABEL)
        value_p = Paragraph(f"<b>{value:,.3f}</b>" if bold else f"{value:,.3f}", S_CELL)
        data.append([label_p, value_p])

    table = Table(data, colWidths=[100 * mm, 75 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (0, 1), (1, 1)),
        ("ALIGN", (0, 0), (1, 1), "CENTER"),
    ]))
    elements += [table, Spacer(1, 3 * mm)]

    _footer_text(elements)

    # Signatures
    sig = Table(
        [[Paragraph("<b>Terminal Representative,</b><br/><i>Terminal Temsilcisi</i>", S_NORMAL),
          "",
          Paragraph(f"<b>M/T {vessel_name}</b><br/><i>Master, Kaptan</i>", S_NORMAL)]],
        colWidths=[60 * mm, 60 * mm, 55 * mm], rowHeights=[25 * mm],
    )
    sig.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBEFORE", (1, 0), (1, -1), 1, colors.black),
        ("LINEBEFORE", (2, 0), (2, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements += [sig, Spacer(1, 5 * mm)]

    # Port info
    port_info = Table(
        [
            [Paragraph("<b>Port, Liman</b>", S_TH), Paragraph("<b>Terminal</b>", S_TH),
             Paragraph("<b>Report Date, Rapor Tarihi</b>", S_TH)],
            [Paragraph(voyage.get("port", ""), S_BOLD_CENTER),
             Paragraph(voyage.get("terminal", ""), S_BOLD_CENTER),
             Paragraph(voyage.get("report_date") or date.today().strftime("%d.%m.%Y"), S_BOLD_CENTER)],
        ],
        colWidths=[60 * mm, 65 * mm, 50 * mm],
    )
    port_info.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBEFORE", (1, 0), (1, -1), 1, colors.black),
        ("LINEBEFORE", (2, 0), (2, -1), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(port_info)


def export_protest_pdf(
    vessel_name: str,
    parcels: list[dict],
    operation: str,
    voyage: dict,
    logo: bytes | None = None,
) -> bytes:
    """One page per parcel dict. operation: 'loading' | 'discharging'."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
    elements: list = []
    for i, parcel in enumerate(parcels):
        _build_page(elements, vessel_name, parcel, operation, voyage, logo)
        if i < len(parcels) - 1:
            elements.append(PageBreak())
    doc.build(elements)
    return buf.getvalue()
