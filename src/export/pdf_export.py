"""
PDF export using reportlab.
"""

from typing import TYPE_CHECKING

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

if TYPE_CHECKING:
    from ..models.voyage import Voyage


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
        info_table = Table(info_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Main data table
        headers = ["Tank", "Grade", "Receiver", "Ullage", "%Fill", 
                   "TOV", "VCF", "GSV", "MT(Air)"]
        
        data = [headers]
        for tank_id, reading in voyage.tank_readings.items():
            row = [
                tank_id,
                reading.grade[:12] if reading.grade else "",
                reading.receiver[:12] if reading.receiver else "",
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
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            
            # Totals row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
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
        elements.append(officers_table)
        
        # Build PDF
        doc.build(elements)
        return True
        
    except Exception as e:
        print(f"Error exporting to PDF: {e}")
        return False
