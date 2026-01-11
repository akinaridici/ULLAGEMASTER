"""
Protest Letter PDF Report Generator.
Generates formal Letter of Protest PDFs for Loading and Discharging operations.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ProtestPDFReport:
    """
    Generates Letter of Protest PDF for discrepancy between Ship and Shore figures.
    
    Supports both Loading and Discharging operations with different data row layouts.
    """
    
    def __init__(self, output_path: str, vessel_name: str, parcel_data: dict, 
                 operation_type: str, voyage_data: dict):
        """
        Initialize protest report generator.
        
        Args:
            output_path: Path for the output PDF file
            vessel_name: Name of the vessel (e.g., "KUZEY EKIM")
            parcel_data: Dictionary containing parcel info and calculated values
            operation_type: "loading" or "discharging"
            voyage_data: Dictionary with voyage info (number, date, port, terminal)
        """
        self.output_path = output_path
        self.vessel_name = vessel_name
        self.parcel_data = parcel_data
        self.operation_type = operation_type
        self.voyage_data = voyage_data
        
        # Register Arial Font for Turkish character support
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Italic', 'C:\\Windows\\Fonts\\ariali.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'C:\\Windows\\Fonts\\arialbi.ttf'))
            self.font_regular = 'Arial'
            self.font_bold = 'Arial-Bold'
            self.font_italic = 'Arial-Italic'
            self.font_bold_italic = 'Arial-BoldItalic'
        except:
            # Fallback if not on Windows or missing fonts
            self.font_regular = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'
            self.font_italic = 'Helvetica-Oblique'
            self.font_bold_italic = 'Helvetica-BoldOblique'
        
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()
        
    def _init_custom_styles(self):
        """Initialize custom paragraph styles."""
        self.style_title = ParagraphStyle(
            'Title', parent=self.styles['Normal'],
            fontSize=10, alignment=TA_CENTER, fontName=self.font_bold,
            leading=12
        )
        self.style_bold_center = ParagraphStyle(
            'BoldCenter', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_CENTER, fontName=self.font_bold
        )
        self.style_normal = ParagraphStyle(
            'NormalText', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_LEFT, fontName=self.font_regular,
            leading=11
        )
        self.style_small = ParagraphStyle(
            'Small', parent=self.styles['Normal'],
            fontSize=7, alignment=TA_LEFT, fontName=self.font_regular,
            leading=9
        )
        self.style_small_italic = ParagraphStyle(
            'SmallItalic', parent=self.styles['Normal'],
            fontSize=7, alignment=TA_LEFT, fontName=self.font_italic,
            textColor=colors.blue, leading=9
        )
        self.style_table_header = ParagraphStyle(
            'TableHeader', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_CENTER, fontName=self.font_bold
        )
        self.style_table_cell = ParagraphStyle(
            'TableCell', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_RIGHT, fontName=self.font_regular
        )
        self.style_table_label = ParagraphStyle(
            'TableLabel', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_LEFT, fontName=self.font_regular
        )
        
    def generate(self):
        """Generate the PDF report for a single parcel."""
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=10*mm, bottomMargin=10*mm
        )
        
        self._build_header()
        self._build_vessel_info()
        self._build_protest_text()
        self._build_cargo_table()
        self._build_description_section()
        self._build_data_table()
        self._build_footer_text()
        self._build_signature_section()
        self._build_port_info()
        
        doc.build(self.elements)
    
    @classmethod
    def generate_multi(cls, output_path: str, vessel_name: str, parcel_data_list: list,
                       operation_type: str, voyage_data: dict):
        """
        Generate a multi-page PDF with one page per parcel.
        
        Args:
            output_path: Path for the output PDF file
            vessel_name: Name of the vessel
            parcel_data_list: List of parcel_data dicts
            operation_type: "loading" or "discharging"
            voyage_data: Dictionary with voyage info
        """
        from reportlab.platypus import PageBreak
        
        if not parcel_data_list:
            return
        
        # Use first parcel to initialize, then collect all elements
        all_elements = []
        
        for idx, parcel_data in enumerate(parcel_data_list):
            # Create instance for each parcel (reuses styles and fonts)
            report = cls(output_path, vessel_name, parcel_data, operation_type, voyage_data)
            
            # Build all sections for this parcel
            report._build_header()
            report._build_vessel_info()
            report._build_protest_text()
            report._build_cargo_table()
            report._build_description_section()
            report._build_data_table()
            report._build_footer_text()
            report._build_signature_section()
            report._build_port_info()
            
            # Add this parcel's elements
            all_elements.extend(report.elements)
            
            # Add page break if not the last parcel
            if idx < len(parcel_data_list) - 1:
                all_elements.append(PageBreak())
        
        # Build the combined PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=10*mm, bottomMargin=10*mm
        )
        doc.build(all_elements)
        
    def _build_header(self):
        """Build the header with logo, title, and document info."""
        # Load config
        from utils.config_headers import load_header_config
        config = load_header_config().get("PROTEST_REPORT", {})
        
        # Title Data
        title_line_1 = config.get("title_line_1", "INTEGRATED MANAGEMENT SYSTEM MANUAL")
        title_line_2 = config.get("title_line_2", "Chapter 7.5")
        doc_title = config.get("doc_title", "LETTER OF PROTEST")
        
        title_text = f"{title_line_1}<br/>{title_line_2}"
        
        # Doc Info Labels
        doc_info = "Issue No.:<br/>Issue Date:<br/>Rev. No.:<br/>Rev. Date:<br/>Page:"
        
        # Doc Info Values
        issue_no = config.get("issue_no", "2")
        issue_date = config.get("issue_date", "1.11.2024")
        rev_no = config.get("rev_no", "0")
        rev_date = config.get("rev_date", "00/00/0000")
        
        doc_values = f"{issue_no}<br/>{issue_date}<br/>{rev_no}<br/>{rev_date}<br/>1 of 1"
        
        # Logo Logic (Image or Text)
        logo_config = load_header_config().get("LOGO_SETTINGS", {})
        logo_mode = logo_config.get("mode", "IMAGE")
        
        logo_obj = None
        
        if logo_mode == "IMAGE":
            # Get logo path
            import sys
            from pathlib import Path
            if getattr(sys, 'frozen', False):
                app_root = Path(sys.executable).parent
            else:
                app_root = Path(__file__).parent.parent.parent
            logo_path = str(app_root / 'data' / 'config' / 'company_logo' / 'LOGO.PNG')
            
            if os.path.exists(logo_path):
                try:
                    logo_obj = Image(logo_path)
                    
                    # Resize Logic:
                    # Target Width: 30mm (Protest uses 30mm)
                    # Max Height: 30mm
                    target_w = 30 * mm
                    max_h = 30 * mm
                    
                    aspect = logo_obj.imageHeight / float(logo_obj.imageWidth)
                    
                    # 1. Scale to target width
                    calc_h = target_w * aspect
                    
                    if calc_h > max_h:
                        # If height exceeds max, scale by height
                        logo_obj.drawHeight = max_h
                        logo_obj.drawWidth = max_h / aspect
                    else:
                        # Otherwise scale by width
                        logo_obj.drawWidth = target_w
                        logo_obj.drawHeight = calc_h
                except Exception as e:
                    print(f"Error loading logo image: {e}")
                    logo_obj = None
        
        if logo_obj is None:
            # Fallback to Text or Explicit Text Mode
            text_content = logo_config.get("text_content", "LOGO")
            formatted_text = text_content.replace('\n', '<br/>')
            logo_obj = Paragraph(formatted_text, self.style_bold_center)
        
        # Info table (right side)
        info_table_data = [
            [Paragraph(doc_info, self.style_small), Paragraph(doc_values, self.style_small)]
        ]
        info_table = Table(info_table_data, colWidths=[25*mm, 25*mm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        # Title table (center)
        title_table_data = [
            [Paragraph(title_text, self.style_title)],
            [Table([[Paragraph(doc_title, self.style_bold_center)]], colWidths=[100*mm])]
        ]
        title_table = Table(title_table_data, colWidths=[100*mm])
        title_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        # Main header table
        header_data = [[logo_obj, title_table, info_table]]
        header_table = Table(header_data, colWidths=[35*mm, 100*mm, 50*mm])
        header_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        
        self.elements.append(header_table)
        self.elements.append(Spacer(1, 3*mm))
        
    def _build_vessel_info(self):
        """Build vessel name and subject line."""
        vessel_text = f"<b>Vessel Name:</b> {self.vessel_name}"
        subject_text = "<b>Subject :</b> Difference between Ship and Shore"
        
        self.elements.append(Paragraph(vessel_text, self.style_normal))
        self.elements.append(Paragraph(subject_text, self.style_normal))
        self.elements.append(Spacer(1, 3*mm))
        
    def _build_protest_text(self):
        """Build the protest declaration text in English and Turkish."""
        english_text = (
            "<b>I, Master of the above named vessel, hereby give formal notice and lodge a Protest.</b><br/>"
            "I hold you responsible for any consequences arising from the events described below. I also reserve the right to amend this "
            "Letter Of Protest (LOP) at later date and to take action as may be deemed necessary."
        )
        
        turkish_text = (
            "<i><font color='blue'>İşbu Protesto Mektubuyla, yukarıda adı yazılı geminin Kaptanı resmi Protesto Mektubunu sunarım. Aşağıda belirtilen durumdan ötürü "
            "karşılaşılabilecek her türlü kayıptan tarafınızın sorumlu tutulacağını bildiririm. Ayrıca bu Protesto Mektubunun ileriki bir tarihte değiştirilmesi "
            "hakkını da saklı tuttuğumu ve gerekecek aksiyonları alacağımı bildiririm.</font></i>"
        )
        
        self.elements.append(Paragraph(english_text, self.style_normal))
        self.elements.append(Spacer(1, 2*mm))
        self.elements.append(Paragraph(turkish_text, self.style_small_italic))
        self.elements.append(Spacer(1, 3*mm))
        
    def _build_cargo_table(self):
        """Build the cargo info table with Grade, B/L Figure, and Date."""
        parcel_name = self.parcel_data.get('name', 'Unknown')
        receiver = self.parcel_data.get('receiver', '')
        bl_figure = self.parcel_data.get('bl_figure', 0)
        date = self.voyage_data.get('bl_date', datetime.now().strftime('%d.%m.%Y'))
        
        grade_display = f"{parcel_name}"
        if receiver:
            grade_display = f"{parcel_name}-{receiver}"
        
        headers = [
            Paragraph("<b>Grade, <font color='blue'>Yükün Cinsi</font></b>", self.style_table_header),
            Paragraph("<b>B/L Figure, <font color='blue'>Konsimento Miktarı</font></b>", self.style_table_header),
            Paragraph("<b>B/L Date, <font color='blue'>B/L Tarihi</font></b>", self.style_table_header)
        ]
        
        data = [
            headers,
            [
                Paragraph(grade_display, self.style_bold_center),
                Paragraph(f"{bl_figure:,.3f} mts", self.style_bold_center),
                Paragraph(date, self.style_bold_center)
            ]
        ]
        
        table = Table(data, colWidths=[60*mm, 65*mm, 50*mm])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.Color(0.9, 0.9, 0.9)),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 3*mm))
        
    def _build_description_section(self):
        """Build description section header."""
        desc_text = "<b>Description of the Protest,</b><br/><i><font color='blue'>Protesto Açıklaması,</font></i>"
        self.elements.append(Paragraph(desc_text, self.style_normal))
        self.elements.append(Spacer(1, 2*mm))
        
    def _build_data_table(self):
        """Build the main data table based on operation type."""
        parcel_name = self.parcel_data.get('name', 'Unknown')
        receiver = self.parcel_data.get('receiver', '')
        grade_display = f"{parcel_name}" if not receiver else f"{parcel_name}-{receiver}"
        
        # Header row
        if self.operation_type == 'loading':
            header_text = "Discrepancy on Completion of Loading"
        else:
            header_text = "Discrepancy on Completion of Discharging (Ship has received empty tank certificate)"
        
        header_rows = [
            [Paragraph(f"<b>{header_text}</b>", self.style_bold_center), ""],
            [Paragraph(f"<b>{grade_display}</b>", self.style_bold_center), ""],
            ["", Paragraph("<b>Gross Metric Tons (in air)</b>", self.style_table_cell)]
        ]
        
        # Data rows based on operation type
        if self.operation_type == 'loading':
            data_rows = self._get_loading_data_rows()
        else:
            data_rows = self._get_discharging_data_rows()
        
        all_rows = header_rows + data_rows
        
        table = Table(all_rows, colWidths=[100*mm, 75*mm])
        table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            # Span first two rows across both columns
            ('SPAN', (0,0), (1,0)),
            ('SPAN', (0,1), (1,1)),
            ('ALIGN', (0,0), (1,1), 'CENTER'),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 3*mm))
        
    def _get_loading_data_rows(self):
        """Get data rows for Loading operation (7 rows)."""
        d = self.parcel_data
        return [
            [Paragraph("B/L Figure", self.style_table_label), Paragraph(f"{d.get('bl_figure', 0):,.3f}", self.style_table_cell)],
            [Paragraph("Ship Figure W/O VEF", self.style_table_label), Paragraph(f"{d.get('ship_wo_vef', 0):,.3f}", self.style_table_cell)],
            [Paragraph("Quantity Difference W/O VEF", self.style_table_label), Paragraph(f"{d.get('diff_wo_vef', 0):,.3f}", self.style_table_cell)],
            [Paragraph("<b>Difference W/O VEF ‰</b>", self.style_table_label), Paragraph(f"<b>{d.get('diff_pct_wo_vef', 0):,.3f}</b>", self.style_table_cell)],
            [Paragraph("Ship Figure with VEF", self.style_table_label), Paragraph(f"{d.get('ship_with_vef', 0):,.3f}", self.style_table_cell)],
            [Paragraph("Quantity Difference with VEF", self.style_table_label), Paragraph(f"{d.get('diff_with_vef', 0):,.3f}", self.style_table_cell)],
            [Paragraph("<b>Difference with VEF ‰</b>", self.style_table_label), Paragraph(f"<b>{d.get('diff_pct_with_vef', 0):,.3f}</b>", self.style_table_cell)],
        ]
        
    def _get_discharging_data_rows(self):
        """Get data rows for Discharging operation (8 rows: #1, #3, #6, #4, #7, #8, #9, #10)."""
        d = self.parcel_data
        return [
            [Paragraph("B/L Figure", self.style_table_label), Paragraph(f"{d.get('bl_figure', 0):,.3f}", self.style_table_cell)],                          # #1
            [Paragraph("Ship Arrival Figure", self.style_table_label), Paragraph(f"{d.get('ship_arrival', 0):,.3f}", self.style_table_cell)],              # #3
            [Paragraph("<b>Arrival-BL diff W/O VEF ‰</b>", self.style_table_label), Paragraph(f"<b>{d.get('arrival_bl_wo_pct', 0):,.3f}</b>", self.style_table_cell)],  # #6
            [Paragraph("Ship Arrival with VEF", self.style_table_label), Paragraph(f"{d.get('ship_arrival_vef', 0):,.3f}", self.style_table_cell)],        # #4
            [Paragraph("<b>Arrival-BL diff VEF ‰</b>", self.style_table_label), Paragraph(f"<b>{d.get('arrival_bl_vef_pct', 0):,.3f}</b>", self.style_table_cell)],     # #7
            [Paragraph("OUTTURN FIGURE", self.style_table_label), Paragraph(f"{d.get('outturn', 0):,.3f}", self.style_table_cell)],                        # #8
            [Paragraph("OUTTURN-BL DIFF", self.style_table_label), Paragraph(f"{d.get('outturn_bl_diff', 0):,.3f}", self.style_table_cell)],               # #9
            [Paragraph("<b>OUTTURN-BL DIFF ‰</b>", self.style_table_label), Paragraph(f"<b>{d.get('outturn_bl_pct', 0):,.3f}</b>", self.style_table_cell)], # #10
        ]
        
    def _build_footer_text(self):
        """Build the footer protest statement text."""
        english_text = (
            "<b>And, I hereby lodge protest accordingly, and we, hold you responsible for delays and consequences.</b> On behalf of the "
            "............... I hereby reserve the right to take such further action as may be considered necessary to protect the interest of "
            "these parties. I reserve the right to refer to this Letter of Protest at a future date and place convenient to the..............."
        )
        
        turkish_text = (
            "<i><font color='blue'>İşbu Protesto Mektubuyla, yukarıda belirtilen durumdan/bulgudan ötürü karşılaşılabilecek her türlü kayıp karşı sorumlu tutulacağınız "
            "hususunu dikkatlerinize sunarım. Tüm bu tarafların haklarını korumak üzere gerekli görülecek herşeyi yapma hakkını saklı tuttuğumu ayrıca "
            "belirtirim.</font></i>"
        )
        
        self.elements.append(Paragraph(english_text, self.style_normal))
        self.elements.append(Spacer(1, 2*mm))
        self.elements.append(Paragraph(turkish_text, self.style_small_italic))
        self.elements.append(Spacer(1, 5*mm))
        
    def _build_signature_section(self):
        """Build the signature table."""
        data = [
            [
                Paragraph("<b>Terminal Representative,</b><br/><i><font color='blue'>Terminal Temsilcisi</font></i>", self.style_normal),
                "",  # Empty middle cell
                Paragraph(f"<b>M/T {self.vessel_name}</b><br/><i><font color='blue'>Master, Kaptan</font></i>", self.style_normal)
            ]
        ]
        
        table = Table(data, colWidths=[60*mm, 60*mm, 55*mm], rowHeights=[25*mm])
        table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('LINEBEFORE', (1,0), (1,-1), 1, colors.black),
            ('LINEBEFORE', (2,0), (2,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 5*mm))
        
    def _build_port_info(self):
        """Build the port info table at the bottom."""
        port = self.voyage_data.get('port', '')
        terminal = self.voyage_data.get('terminal', '')
        date = self.voyage_data.get('report_date', datetime.now().strftime('%d.%m.%Y'))
        
        headers = [
            Paragraph("<b>Port,<font color='blue'>Liman</font></b>", self.style_table_header),
            Paragraph("<b>Terminal</b>", self.style_table_header),
            Paragraph("<b>Report Date, <font color='blue'>Rapor Tarihi</font></b>", self.style_table_header)
        ]
        
        data = [
            headers,
            [
                Paragraph(port, self.style_bold_center),
                Paragraph(terminal, self.style_bold_center),
                Paragraph(date, self.style_bold_center)
            ]
        ]
        
        table = Table(data, colWidths=[60*mm, 65*mm, 50*mm])
        table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('LINEBEFORE', (1,0), (1,-1), 1, colors.black),
            ('LINEBEFORE', (2,0), (2,-1), 1, colors.black),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        
        self.elements.append(table)


# Test code
if __name__ == "__main__":
    test_parcel = {
        'name': 'DAP-5 KB-95',
        'receiver': '',
        'bl_figure': 982779,
        'ship_wo_vef': 982307,
        'diff_wo_vef': -472,
        'diff_pct_wo_vef': -0.480,
        'ship_with_vef': 982995,
        'diff_with_vef': 216,
        'diff_pct_with_vef': 0.220,
    }
    
    test_voyage = {
        'voyage_number': '2025-01',
        'date': '17.11.2025',
        'port': 'ANTALYA',
        'terminal': 'AKDENIZ AKARYAKIT'
    }
    
    report = ProtestPDFReport(
        "test_protest.pdf",
        "KUZEY EKIM",
        test_parcel,
        "loading",
        test_voyage
    )
    report.generate()
    print("Test PDF generated: test_protest.pdf")
