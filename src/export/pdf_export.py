"""
PDF export using reportlab.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

if TYPE_CHECKING:
    from ..models.voyage import Voyage


def register_fonts():
    """
    Register Unicode-compatible fonts for ReportLab.
    
    ReportLab's default fonts do not support all UTF-8 characters (like Turkish 'ğ', 'ş').
    We attempt to register Arial from the Windows system fonts.
    """
    if not REPORTLAB_AVAILABLE:
        return

    # Try to find Arial in standard Windows location
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")

    try:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont('Arial', str(font_path)))
        if font_bold_path.exists():
            pdfmetrics.registerFont(TTFont('Arial-Bold', str(font_bold_path)))
    except Exception as e:
        # Fallback if fonts are missing (will use ReportLab defaults)
        print(f"Warning: Could not register Arial fonts: {e}")


def export_to_pdf(voyage: 'Voyage', filepath: str) -> bool:
    """
    Export voyage data to PDF file.
    
    Args:
        voyage: Voyage object with all tank readings
        filepath: Output file path (.pdf)
        
    Returns:
        True if successful
    """
    if not REPORTLAB_AVAILABLE:
        print("reportlab not installed. Run: pip install reportlab")
        return False
    
    # Register fonts before building the doc
    register_fonts()
    
    # Determine font names (fallback to Helvetica if Arial not registered)
    try:
        pdfmetrics.getFont('Arial')
        font_normal = 'Arial'
    except:
        font_normal = 'Helvetica'

    try:
        pdfmetrics.getFont('Arial-Bold')
        font_bold = 'Arial-Bold'
    except:
        font_bold = 'Helvetica-Bold'
    
    try:
        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=font_bold,
            fontSize=18,
            alignment=1  # Center
        )
        elements.append(Paragraph("ULLAGE REPORT", title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Voyage info table
        info_data = [
            ["Voyage No:", voyage.voyage_number, "Date:", voyage.date],
            ["Port:", voyage.port, "Terminal:", voyage.terminal],
            ["V.E.F.:", f"{voyage.vef:.5f}", "Trim:", f"{voyage.drafts.trim:+.2f} m"],
        ]
        # Create and style the info table
        info_table = Table(info_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_normal), # Default font for all
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), font_bold),    # Bold first column (labels)
            ('FONTNAME', (2, 0), (2, -1), font_bold),    # Bold third column (labels)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Main data table
        headers = ["Tank", "Grade", "Receiver", "Ullage", "%Fill", 
                   "TOV", "VCF", "GSV", "MT(Air)"]
        
        data = [headers]
        for tank_id, reading in voyage.tank_readings.items():
            # Lookup parcel for grade/receiver
            grade = ""
            receiver = ""
            if reading.parcel_id:
                if reading.parcel_id == "0":  # SLOP
                    grade = "SLOP"
                else:
                    for parcel in voyage.parcels:
                        if parcel.id == reading.parcel_id:
                            grade = parcel.name[:12] if parcel.name else ""
                            receiver = parcel.receiver[:12] if parcel.receiver else ""
                            break
            
            row = [
                tank_id,
                grade,
                receiver,
                f"{reading.ullage:.1f}" if reading.ullage else "-",
                f"{reading.fill_percent:.1f}" if reading.fill_percent else "-",
                f"{reading.tov:.3f}",
                f"{reading.vcf:.5f}",
                f"{reading.gsv:.3f}",
                f"{reading.mt_air:.3f}"
            ]
            data.append(row)
        
        # Totals row
        data.append(["TOTAL", "", "", "", "", "", "", 
                     f"{voyage.total_gsv:.3f}", f"{voyage.total_mt:.3f}"])
        
        # Create table
        col_widths = [2*cm, 3*cm, 3*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]
        main_table = Table(data, colWidths=col_widths)
        
        # Table styling
        style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), font_normal),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            
            # Totals row
            ('FONTNAME', (0, -1), (-1, -1), font_bold),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D9E1F2')),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Apply warning colors
        for i, (tank_id, reading) in enumerate(voyage.tank_readings.items(), 1):
            if reading.warning == "high_high":
                style.add('BACKGROUND', (4, i), (4, i), colors.red)
            elif reading.warning == "high":
                style.add('BACKGROUND', (4, i), (4, i), colors.yellow)
            elif reading.warning == "low":
                style.add('BACKGROUND', (4, i), (4, i), colors.orange)
        
        main_table.setStyle(style)
        elements.append(main_table)
        
        # Officers
        elements.append(Spacer(1, 1*cm))
        officers_data = [
            ["Chief Officer:", voyage.chief_officer, "Master:", voyage.master]
        ]
        officers_table = Table(officers_data, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        # Set font for officers table
        officers_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_normal),
            ('FONTNAME', (0, 0), (0, -1), font_bold),
            ('FONTNAME', (2, 0), (2, -1), font_bold),
        ]))
        elements.append(officers_table)
        
        # Build PDF
        doc.build(elements)
        return True
        
    except Exception as e:
        print(f"Error exporting to PDF: {e}")
        return False

