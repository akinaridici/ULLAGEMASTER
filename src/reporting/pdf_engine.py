import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import mm

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class UllagePDFReport:
    """
    Generates the Ullage Report PDF matching the specific visual style.
    """
    def __init__(self, output_path, vessel_data, voyage_data, tank_data, overview_data=None):
        self.output_path = output_path
        self.vessel_data = vessel_data
        self.voyage_data = voyage_data
        self.tank_data = tank_data
        self.overview_data = overview_data or {}
        
        # Register Arial Font for Turkish Support
        # Using standard Windows font path
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
            self.font_regular = 'Arial'
            self.font_bold = 'Arial-Bold'
        except:
            # Fallback if not on Windows or missing
            self.font_regular = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'
        
        # A4 Landscape: 297mm width, 210mm height
        # Margins: 10mm L/R -> 277mm usable width
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=5*mm,
            bottomMargin=5*mm
        )
        
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.style_center = ParagraphStyle(
            'Center', parent=self.styles['Normal'], alignment=1, fontSize=8, leading=9, fontName=self.font_regular
        )
        self.style_bold_center = ParagraphStyle(
            'BoldCenter', parent=self.styles['Normal'], alignment=1, fontSize=8, leading=9, fontName=self.font_bold
        )
        self.style_title = ParagraphStyle(
            'Title', parent=self.styles['Heading1'], alignment=1, fontSize=12, leading=14, fontName=self.font_bold
        )
        self.style_left = ParagraphStyle(
             'Left', parent=self.styles['Normal'], alignment=0, fontSize=8, leading=10, fontName=self.font_regular, leftIndent=2*mm
        )

    def generate(self):
        self._build_header()
        self._build_voyage_info()
        self._build_main_table()
        self._build_summary_table()
        self._build_footer()
        
        self.doc.build(self.elements)
        print(f"PDF generated: {self.output_path}")

    def _build_header(self):
        # Load config
        from utils.config_headers import load_header_config
        config = load_header_config().get("ULLAGE_REPORT", {})
        
        # Build Title
        title_lines = [
            config.get("title_line_1", "INTEGRATED MANAGEMENT SYSTEM MANUAL"),
            config.get("title_line_2", "Chapter 7.5"),
            config.get("title_line_3", "ULLAGE REPORT & TEMPERATURE LOG")
        ]
        title_text = "<br/>".join(title_lines)
        
        # Build Doc Info
        issue_no = config.get("issue_no", "02")
        issue_date = config.get("issue_date", "01/11/2024")
        rev_no = config.get("rev_no", "0")
        page_fmt = config.get("page_format", "Page: 1")
        
        doc_info = f"Issue No: {issue_no}<br/>Issue Date: {issue_date}<br/>Rev No: {rev_no}<br/>{page_fmt}"
        
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
                    # Target Width: 35mm
                    # Max Height: 35mm
                    target_w = 35 * mm
                    max_h = 35 * mm
                    
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
            text_content = logo_config.get("text_content", "Battal\nMarine")
            # Replace \n with <br/> for ReportLab
            formatted_text = text_content.replace('\n', '<br/>')
            logo_obj = Paragraph(formatted_text, self.style_bold_center)

        data = [[
            logo_obj, 
            Table([
                [Paragraph(title_text, self.style_title)],
            ], colWidths=[180*mm]),
            Paragraph(doc_info, ParagraphStyle('Small', parent=self.style_center, alignment=0, fontSize=7))
        ]]
        
        # Total width: 275mm
        t = Table(data, colWidths=[40*mm, 190*mm, 45*mm])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 1*mm))

    def _build_voyage_info(self):
        rpt_type = self.voyage_data.get('report_type', '')
        title_row = [Paragraph(f"ULLAGE REPORT - {rpt_type}", self.style_bold_center)]
        t_title = Table([title_row], colWidths=[275*mm])
        t_title.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black), 
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke)
        ]))
        self.elements.append(t_title)

        # 10 Columns to accommodate Draft Aft
        # [Lbl, Val, Lbl, Val, Lbl, Val, Lbl, Val, Lbl, Val]
        # 20+55 + 20+30 + 20+40 + 20+25 + 20+25 = 275mm
        cw = [20*mm, 55*mm, 20*mm, 30*mm, 20*mm, 40*mm, 20*mm, 25*mm, 20*mm, 25*mm]
        
        v = self.vessel_data
        y = self.voyage_data
        
        row1 = [
            "Vessel", Paragraph(v.get('name',''), self.style_bold_center),
            "Voyage", Paragraph(y.get('voyage',''), self.style_bold_center),
            "Receiver", Paragraph(y.get('receiver',''), self.style_bold_center),
            "Date", Paragraph(y.get('date',''), self.style_bold_center),
            "", "" # Last 2 cols merged into Date Value
        ]
        
        row2 = [
            "From", Paragraph(y.get('port',''), self.style_center),
            "Port", Paragraph(y.get('port_to',''), self.style_center),
            "Cargo", Paragraph(y.get('cargo',''), self.style_center),
            "Draft Aft", y.get('draft_aft', ''),
            "Draft Fwd", y.get('draft_fwd', '')
        ]
        
        t_info = Table([row1, row2], colWidths=cw)
        t_info.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,-1), self.font_bold),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('SPAN', (7,0), (9,0)), # Merge Date Value across last 3 cols
        ]))
        self.elements.append(t_info)
        self.elements.append(Spacer(1, 1*mm))

    def _build_main_table(self):
        # 13 Columns. Total Width Target: 275mm.
        # Adjusted: Reduced FW by 10mm (5 each), gave to Tanks(+6), TOV(+2), GOV(+2)
        
        w_tanks = 33*mm
        w_ullage = 19*mm
        w_tov = 26*mm
        w_fw = 14*mm
        w_gov = 26*mm
        w_temp = 16*mm
        w_vcf = 16*mm
        w_gsv = 24*mm
        w_dens = 20*mm
        w_wvac = 24*mm
        w_wair = 24*mm
        
        col_widths = [
            w_tanks,         # 0: Tanks
            w_ullage, w_ullage, # 1,2: Ullage
            w_tov,           # 3: TOV
            w_fw, w_fw,      # 4,5: FW
            w_gov,           # 6: GOV
            w_temp,          # 7: Temp
            w_vcf,           # 8: VCF
            w_gsv,           # 9: GSV
            w_dens,          # 10: Density
            w_wvac,          # 11: Vac
            w_wair           # 12: Air
        ]
        
        headers = [
            ['Tanks', 'Ullage (mm)', '', 'TOV', 'Free water', '', 'GOV', 'Temperature', 'VCF', 'GSV', 'Density', 'Weight Vacuum', 'Weight Air'],
            ['', 'Actual', 'Corrected', '', 'Actual', 'Corrected', '', '', '', '', 'Vacuum', '', '']
        ]
        
        data = []
        
        # Accumulators
        total_tov = 0.0
        total_gov = 0.0
        total_gsv = 0.0
        total_vac = 0.0
        total_air = 0.0

        for t in self.tank_data:
            # Parse values for totals
            try: total_tov += float(t.get('tov', 0))
            except: pass
            try: total_gov += float(t.get('gov', 0))
            except: pass
            try: total_gsv += float(t.get('gsv', 0))
            except: pass
            try: total_vac += float(t.get('w_vac', 0))
            except: pass
            try: total_air += float(t.get('w_air', 0))
            except: pass
            
            row = [
                t.get('name', ''),
                t.get('ullage_actual', ''), t.get('ullage_corr', ''),
                t.get('tov', ''),
                t.get('fw_actual', '0.00'), t.get('fw_corr', '0.00'),
                t.get('gov', ''),
                t.get('temp', ''),
                t.get('vcf', ''),
                t.get('gsv', ''),
                t.get('density', ''),
                t.get('w_vac', ''),
                t.get('w_air', '')
            ]
            data.append(row)
            
        # Totals Row
        totals_row = [
            '', '', '', # Tanks, Ullage
            f"{total_tov:.3f}", # TOV
            '', '', # FW
            f"{total_gov:.3f}", # GOV
            '', '', # Temp Ref
            f"{total_gsv:.3f}", # GSV
            '', # Density
            f"{total_vac:.3f}", # Vac
            f"{total_air:.3f}"  # Air
        ]
        data.append(totals_row)
        
        combined_data = headers + data
        
        t = Table(combined_data, colWidths=col_widths, repeatRows=2)
        
        style = [
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,-1), self.font_regular),
            ('FONTSIZE', (0,0), (-1,-1), 6), # Reduced to 6pt to fit content
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            
            # Header
            ('FONTNAME', (0,0), (-1,1), self.font_bold),
            ('BACKGROUND', (0,0), (-1,1), colors.whitesmoke),
            ('FONTSIZE', (0,0), (-1,1), 7), # Headers slightly larger
            
            # Spans
            ('SPAN', (0,0), (0,1)), # Tanks
            ('SPAN', (1,0), (2,0)), # Ullage Span
            ('SPAN', (3,0), (3,1)), # TOV
            ('SPAN', (4,0), (5,0)), # FW Span
            ('SPAN', (6,0), (6,1)), # GOV
            ('SPAN', (7,0), (7,1)), # Temp
            ('SPAN', (8,0), (8,1)), # VCF
            ('SPAN', (9,0), (9,1)), # GSV
            ('SPAN', (10,0), (10,1)), # Density
            ('SPAN', (11,0), (11,1)), # Weight Vac
            ('SPAN', (12,0), (12,1)), # Weight Air
            
            # Reduce row height
            ('TOPPADDING', (0,0), (-1,-1), 0.5), # minimal padding
            ('BOTTOMPADDING', (0,0), (-1,-1), 0.5),
        ]
        
        # Totals Row formatting
        last_idx = -1
        style.append(('FONTNAME', (0, last_idx), (-1, last_idx), self.font_bold))
        style.append(('BACKGROUND', (0, last_idx), (-1, last_idx), colors.whitesmoke))
        
        t.setStyle(TableStyle(style))
        self.elements.append(t)
        self.elements.append(Spacer(1, 1*mm))

    def _build_summary_table(self):
        headers = ["MMC No", "Product", "Density Vacuum\n15 Deg C", "TOV", "Free Water", "GOV", "AVERAGE\nVCF", "GSV", "Metric Tonnes\nVacuum", "Metric Tonnes\nAir"]
        
        row = [
            self.overview_data.get('mmc_no', 'TFC-90782107'),
            self.overview_data.get('product', '0'),
            self.overview_data.get('density', '0.7340'),
            self.overview_data.get('tov', '21258.162'),
            "0.00",
            self.overview_data.get('gov', '21261.869'),
            self.overview_data.get('average_vcf', '0.9888'),
            self.overview_data.get('gsv', '21008.826'),
            self.overview_data.get('mt_vac', '15934.787'),
            self.overview_data.get('mt_air', '15911.677')
        ]
        
        data = [headers, row]
        col_w = 275/10 * mm
        t = Table(data, colWidths=[col_w]*10)
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,0), self.font_bold),
            ('FONTNAME', (0,1), (-1,-1), self.font_regular),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        self.elements.append(t)
        
        # Remarks
        self.elements.append(Spacer(1, 1*mm))
        rem = self.overview_data.get('remarks', 'Sea State: MODERATE')
        p_rem = Paragraph(f"<b>Remarks:</b><br/>{rem}", self.style_left)
        t_rem = Table([[p_rem]], colWidths=[275*mm])
        t_rem.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
        self.elements.append(t_rem)

    def _build_footer(self):
        self.elements.append(Spacer(1, 2*mm))
        data = [
             ["Signature, Master/Chief Officer", "Name in block letters", "Signature, Surveyor", "Name in block letters"],
             ["", "Harun Kurtuluş", "", ""] 
        ]
        # Total 275mm
        t = Table(data, colWidths=[70*mm, 67*mm, 70*mm, 68*mm])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,-1), self.font_regular),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,0), 'TOP'),
            ('MINHEIGHT', (0,1), (-1,1), 10*mm),
        ]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 1*mm))
        self.elements.append(Paragraph("Conttrolled Copy", ParagraphStyle('Tiny', fontSize=6)))

if __name__ == "__main__":
    dummy_vessel = {'name': 'M/T KUZEY EKIM'}
    dummy_voyage = {'voyage': '01-26', 'date': '28/12/2025', 'receiver': 'TUPRAS', 'port_to': 'ALIAGA'}
    dummy_tanks = [
        {'name': f'COT {i}P', 'ullage_actual': '1050', 'ullage_corr': '1050', 'tov': '778.414', 'gov': '778.620', 'gsv': '765.999', 'density':'0.7340', 'w_vac':'562.243', 'w_air':'561.400'} 
        for i in range(1, 8)
    ]
    dummy_overview = {
        'mmc_no': 'TFC-90782107', 'product': 'Gasoline', 'density': '0.7340',
        'tov': '21258.162', 'gov': '21261.869', 'average_vcf': '0.9888',
        'gsv': '21008.826', 'mt_vac': '15934.787', 'mt_air': '15911.677'
    }
    report = UllagePDFReport("test_ullage_report.pdf", dummy_vessel, dummy_voyage, dummy_tanks, dummy_overview)
    report.generate()
