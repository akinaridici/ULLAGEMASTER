"""
Visual Stowage Plan Export Module.
Generates a graphical representation of the ship's cargo plan.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm, mm
    from reportlab.pdfgen import canvas
    from reportlab.graphics.shapes import Drawing, Rect, String, Group, Line
    from reportlab.graphics import renderPDF
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
    
    # Constants for layout (only defined when reportlab is available)
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
    MARGIN_X = 1 * cm
    MARGIN_Y = 1 * cm
    DRAW_AREA_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)
    DRAW_AREA_HEIGHT = PAGE_HEIGHT - (2 * MARGIN_Y)
except ImportError:
    REPORTLAB_AVAILABLE = False

if TYPE_CHECKING:
    from ..models.voyage import Voyage
    from ..models.tank import TankReading
    from ..models.parcel import Parcel


def _get_contrast_color(hex_color: str) -> colors.Color:
    """
    Determine best text color (black or white) for a given background color.
    """
    try:
        # Check if color string is valid hex (e.g., "#FF0000")
        if not hex_color or not hex_color.startswith('#'):
            return colors.black
            
        # Parse hex
        h = hex_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        # Calculate luminance (standard formula)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Return black for light backgrounds, white for dark
        return colors.black if luminance > 0.5 else colors.white
    except:
        return colors.black


def _draw_tank_cell(c: canvas.Canvas, x: float, y: float, w: float, h: float, 
                   reading: 'TankReading', parcel: Optional['Parcel'], 
                   tank_name: str) -> None:
    """
    Draw a single tank cell with data.
    """
    # Background color
    bg_color = colors.white
    text_color = colors.black
    
    if parcel and parcel.color:
        try:
            bg_color = colors.HexColor(parcel.color)
            text_color = _get_contrast_color(parcel.color)
        except:
            pass
    elif reading.parcel_id == "0":  # SLOP
        bg_color = colors.HexColor("#9CA3AF")
        text_color = colors.black
    
    # Draw box
    c.setFillColor(bg_color)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(x, y, w, h, fill=1, stroke=1)
    
    # Draw Header (Tank Name + Parcel Name)
    header_h = h * 0.25
    c.setFillColor(colors.white) # Header background often distinct, or same? 
    # Let's keep specific header styling simple for now, or use the bg_color
    # To match example: Top part has tank name, Middle has Parcel, Bottom has data
    
    # Let's split into sections
    # Section 1: Top Name (e.g., "1P")
    # Section 2: Parcel Name
    # Section 3: Data Grid
    
    # Draw Text
    c.setFillColor(text_color)
    
    # Font setup
    font_bold = "Arial-Bold"
    font_normal = "Arial"
    
    # Row 1: Tank Name (Top Right or Center)
    c.setFont(font_bold, 10)
    c.drawCentredString(x + w/2, y + h - 12, tank_name)
    
    # Row 2: Parcel Name
    parcel_name = parcel.name if parcel else ("SLOP" if reading.parcel_id == "0" else "")
    c.setFont(font_bold, 9)
    # Wrap text if too long
    if c.stringWidth(parcel_name, font_bold, 9) > w - 4:
        c.setFont(font_bold, 7)
    c.drawCentredString(x + w/2, y + h - 25, parcel_name)
    
    # Divider line
    c.setStrokeColor(text_color)
    c.line(x, y + h - 30, x + w, y + h - 30)
    
    # Data Rows
    # Labels: ULL, MT, CBM, %
    # Values: ...
    data_start_y = y + h - 42
    line_height = 10
    
    c.setFont(font_normal, 8)
    
    # Helper to draw row
    def draw_row(label, value, y_pos):
        c.drawString(x + 5, y_pos, label)
        c.drawRightString(x + w - 5, y_pos, value)
    
    ullage_str = f"{reading.ullage:.0f}" if reading.ullage is not None else "-"
    draw_row("ULL", ullage_str, data_start_y)
    
    mt_str = f"{reading.mt_air:.0f}"
    draw_row("MT", mt_str, data_start_y - line_height)
    
    gov_str = f"{reading.gov:.0f}" # CBM usually refers to GOV or TOV? usually GOV/GSV at 15C
    draw_row("CBM", gov_str, data_start_y - line_height * 2)
    
    fill_str = f"{reading.fill_percent:.1f}" if reading.fill_percent is not None else "-"
    draw_row("%", fill_str, data_start_y - line_height * 3)


def generate_stowage_plan(voyage: 'Voyage', filepath: str, ship_name: str = "") -> bool:
    """
    Generate the visual stowage plan PDF.
    """
    if not REPORTLAB_AVAILABLE:
        print("ReportLab not available.")
        return False
        
    try:
        c = canvas.Canvas(filepath, pagesize=landscape(A4))
        title = f"{ship_name} - STOWAGE PLAN" if ship_name else "STOWAGE PLAN"
        c.setTitle(title)
        
        # Ensure fonts are registered (re-use logic from pdf_export if possible, or re-register)
        # We assume pdf_export.register_fonts() has been run or we run it here
        # Ideally we should import it, but to avoid circular imports or complex deps, let's just try to use Arial
        # If Arial isn't registered, ReportLab will error or fallback if we configured it. 
        # Safer to re-register here locally to be self-contained
        try:
            font_path = Path("C:/Windows/Fonts/arial.ttf")
            font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
            if font_path.exists():
                pdfmetrics.registerFont(TTFont('Arial', str(font_path)))
            if font_bold_path.exists():
                pdfmetrics.registerFont(TTFont('Arial-Bold', str(font_bold_path)))
            font_normal = 'Arial'
            font_bold = 'Arial-Bold'
        except:
            font_normal = 'Helvetica'
            font_bold = 'Helvetica-Bold'

        # --- HEADER ---
        c.setFont(font_bold, 16)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 30, title)
        
        c.setFont(font_bold, 10)
        c.drawString(MARGIN_X, PAGE_HEIGHT - 60, f"VOYAGE: {voyage.voyage_number}")
        c.drawString(MARGIN_X, PAGE_HEIGHT - 75, f"PORT: {voyage.port}")
        
        # --- SHIP LAYOUT GENERATION ---
        # Sort tanks: We want to organize by simple ID pairs usually.
        # Logic: Find unique numbers in tank IDs (e.g. "1P" -> 1). Sort descending (Bow on Right typically means 1 is Right?).
        # Actually user example shows 1P on the RIGHT. So 1..N order goes Right to Left? Or Left to Right?
        # Let's assume standard plan: Bow is usually Right in these diagrams.
        # So we place Tank 1 on Right, Tank N on Left.
        
        # Group tanks
        tank_groups = {} # {1: {'P': reading, 'S': reading, 'C': reading}}
        
        for tank_id, reading in voyage.tank_readings.items():
            # Extract number and side
            # Heuristic: Filter digits
            digits = ''.join(filter(str.isdigit, tank_id))
            if not digits:
                continue # Skip specialized tanks without numbers if logic fails
            
            num = int(digits)
            if num not in tank_groups:
                tank_groups[num] = {}
            
            # Side
            side = 'C'
            if 'P' in tank_id.upper(): side = 'P'
            elif 'S' in tank_id.upper(): side = 'S'
            
            tank_groups[num][side] = (tank_id, reading)
            
        sorted_nums = sorted(tank_groups.keys(), reverse=True) # Draw larger numbers (Aft) on Left? 
        # Actually, if we draw 1 on Right, and N on Left.
        # Let's define layout variables.
        
        # Grid settings
        start_x = MARGIN_X + 50 # Start from Left
        start_y = 10 * cm
        box_w = 2.5 * cm
        box_h = 4.0 * cm
        gap = 0.2 * cm
        
        # We need to calculate total width to center it
        total_groups = len(sorted_nums)
        total_width = total_groups * (box_w + gap)
        
        # Adjust start_x to center on page
        start_x = (PAGE_WIDTH - total_width) / 2
        
        # Draw tanks
        # We iterate sorted_nums. If we want 1 on Right (Bow), and we interpret sorted_nums as [N, ..., 1] 
        # then drawing from Left to Right means we draw N first (Aft), then ... then 1 (Fwd).
        # This results in Aft(Left) -> Fwd(Right). Perfect.
        
        current_x = start_x
        
        for num in sorted_nums:
            group = tank_groups[num]
            
            # Port (Top)
            if 'P' in group:
                tank_id, reading = group['P']
                parcel = None
                if reading.parcel_id and reading.parcel_id != "0":  # Not SLOP
                    # Find parcel
                    for p in voyage.parcels:
                        if p.id == reading.parcel_id:
                            parcel = p
                            break
                            
                _draw_tank_cell(c, current_x, start_y + box_h/2, box_w, box_h, 
                               reading, parcel, tank_id)
            
            # Starboard (Bottom)
            if 'S' in group:
                tank_id, reading = group['S']
                parcel = None
                if reading.parcel_id and reading.parcel_id != "0":  # Not SLOP
                    for p in voyage.parcels:
                        if p.id == reading.parcel_id:
                            parcel = p
                            break
                            
                # Draw below Port 
                # Note: Coordinate system 0,0 is bottom-left. 
                # So Port Y > Starboard Y
                _draw_tank_cell(c, current_x, start_y - box_h/2, box_w, box_h, 
                               reading, parcel, tank_id)
                
            # Center (Middle - overlap or specialized?)
            if 'C' in group:
                tank_id, reading = group['C']
                parcel = None
                if reading.parcel_id and reading.parcel_id != "0":  # Not SLOP
                    for p in voyage.parcels:
                        if p.id == reading.parcel_id:
                            parcel = p
                            break
                # Center tank usually spans, or is in middle. 
                # For simplicity, draw it in middle, checking overlap?
                # Let's assume simple layout for now: P and S. If C exists, maybe standard layout checks needed.
                pass 
            
            current_x += box_w + gap
            
        # Draw Ship Outline (Decoration) - REMOVED as per request
        
        
        # --- SUMMARY TABLE ---
        # Top Right
        # Columns: Grade, Density, Color, Wgt
        
        # Aggregate data by parcel
        summary_data = {} # {parcel_id: {name, density, color, total_mt, total_gov}}
        
        for reading in voyage.tank_readings.values():
            pid = reading.parcel_id
            if not pid: continue
            
            if pid not in summary_data:
                p_obj = None
                name = "SLOP" if pid == "0" else "Unknown"
                color = "#9CA3AF" if pid == "0" else "#FFFFFF"
                density = 0.0
                
                if pid != "0":  # Not SLOP
                    for p in voyage.parcels:
                        if p.id == pid:
                            p_obj = p
                            name = p.name
                            color = p.color
                            density = p.density_vac
                            break
                else:
                    # Slop defaults
                    density = reading.density_vac or 0.85
                
                summary_data[pid] = {
                    'name': name,
                    'color': color,
                    'density': density,
                    'total_mt': 0.0,
                    'total_gov': 0.0
                }
            
            summary_data[pid]['total_mt'] += reading.mt_air
            summary_data[pid]['total_gov'] += reading.gov
            
        # Draw Summary Grid
        sum_x = PAGE_WIDTH - 8 * cm - MARGIN_X
        sum_y = PAGE_HEIGHT - 3 * cm
        sum_w = 8 * cm
        row_h = 0.6 * cm
        
        # Header
        c.setFillColor(colors.lightgrey)
        c.rect(sum_x, sum_y, sum_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_bold, 8)
        c.drawString(sum_x + 0.2*cm, sum_y + 0.15*cm, "GRADE")
        c.drawString(sum_x + 3.0*cm, sum_y + 0.15*cm, "DENS")
        c.drawRightString(sum_x + sum_w - 0.2*cm, sum_y + 0.15*cm, "MT (AIR)")
        
        sum_y -= row_h
        
        for idx, item in summary_data.items():
            # Bg color
            try:
                bg = colors.HexColor(item['color'])
                txt = _get_contrast_color(item['color'])
            except:
                bg = colors.white
                txt = colors.black
                
            c.setFillColor(bg)
            c.rect(sum_x, sum_y, sum_w, row_h, fill=1, stroke=1)
            
            c.setFillColor(txt)
            c.setFont(font_normal, 8)
            c.drawString(sum_x + 0.2*cm, sum_y + 0.15*cm, item['name'][:15])
            c.drawString(sum_x + 3.0*cm, sum_y + 0.15*cm, f"{item['density']:.4f}")
            c.drawRightString(sum_x + sum_w - 0.2*cm, sum_y + 0.15*cm, f"{item['total_mt']:.0f}")
            
            sum_y -= row_h
            
        # --- FOOTER ---
        # Officers (Bottom Right)
        footer_y = MARGIN_Y
        footer_x = PAGE_WIDTH - MARGIN_X
        
        c.setFillColor(colors.black)
        c.setFont(font_bold, 10)
        
        # Master
        c.drawRightString(footer_x, footer_y, f"Master: {voyage.master}")
        
        # Chief Officer (above Master)
        c.drawRightString(footer_x, footer_y + 15, f"Chief Officer: {voyage.chief_officer}")

        c.save()
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error generating visual stowage plan: {e}")
        return False
