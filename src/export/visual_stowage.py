"""
Visual Stowage Plan Export Module.
Generates a graphical representation of the ship's cargo plan matching the specific "spreadsheet-like" layout.
"""

from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple
from reportlab.lib import colors # type: ignore
from reportlab.lib.pagesizes import A4, landscape # type: ignore
from reportlab.lib.units import cm, mm # type: ignore
from reportlab.pdfgen import canvas # type: ignore
from reportlab.pdfbase import pdfmetrics # type: ignore
from reportlab.pdfbase.ttfonts import TTFont # type: ignore
import traceback

if TYPE_CHECKING:
    from ..models.voyage import Voyage
    from ..models.tank import TankReading
    from ..models.parcel import Parcel

REPORTLAB_AVAILABLE = True

def _get_contrast_color(hex_color: str) -> colors.Color:
    """Determine best text color (black or white) for a given background color."""
    try:
        if not hex_color or not hex_color.startswith('#'):
            return colors.black
        h = hex_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return colors.black if luminance > 0.5 else colors.white
    except:
        return colors.black

def _draw_tank_cell(c: canvas.Canvas, x: float, y: float, w: float, h: float, 
                   reading: 'TankReading', parcel: Optional['Parcel'], 
                   tank_id: str, side: str) -> None:
    """
    Draw a single tank cell with specific layout.
    side: 'P' (Port, Top) or 'S' (Starboard, Bottom)
    """
    # Colors
    bg_color = colors.white
    header_color = colors.white
    header_text_color = colors.black
    
    if parcel and parcel.color:
        try:
            fill_c = colors.HexColor(parcel.color)
            header_color = fill_c
            header_text_color = _get_contrast_color(parcel.color)
        except:
            pass
    elif reading.parcel_id == "0":  # SLOP
        header_color = colors.HexColor("#9CA3AF")
        header_text_color = colors.black

    # Layout dimensions
    header_h = 0.5 * cm
    footer_h = 0.5 * cm
    receiver_h = 0.5 * cm
    data_h = h - header_h - footer_h - receiver_h
    
    # ---------------------------------------------------------
    # PORT SIDE LAYOUT (Top)
    # ---------------------------------------------------------
    # Header (Top): Tank ID
    # Sub-Header: Receiver
    # Data Body
    # Footer (Bottom): Grade Name (Colored)
    # ---------------------------------------------------------
    if side == 'P' or side == 'C': 
        # 1. Header: Tank ID (White bg, Black text)
        c.setFillColor(colors.white) 
        c.setStrokeColor(colors.black)
        c.rect(x, y + h - header_h, w, header_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black)
        c.setFont("Arial-Bold", 9)
        c.drawCentredString(x + w/2, y + h - header_h + 0.15*cm, tank_id)
        
        # 2. Receiver (White bg, Black text)
        rec_y = y + h - header_h - receiver_h
        c.setFillColor(colors.white)
        c.rect(x, rec_y, w, receiver_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black)
        c.setFont("Arial", 6)
        receiver = parcel.receiver if parcel else ""
        c.drawCentredString(x + w/2, rec_y + 0.15*cm, receiver[:20]) # Limit length
        
        # 3. Data Body 
        data_bg = colors.HexColor("#60A5FA") # Blueish
        c.setFillColor(data_bg) 
        c.rect(x, y + footer_h, w, data_h, fill=1, stroke=1)
        
        # Draw Data lines
        c.setFillColor(colors.white) # White text on blue bg
        c.setFont("Arial-Bold", 8)
        
        # Data Rows
        start_text_y = y + footer_h + data_h - 0.4*cm
        step = 0.4*cm
        
        # ULL
        c.drawString(x + 2, start_text_y, "ULL")
        val = f"{reading.ullage:.0f}" if reading.ullage else ""
        c.drawRightString(x + w - 2, start_text_y, val)
        
        # MT
        c.drawString(x + 2, start_text_y - step, "MT")
        val = f"{reading.mt_air:.0f}"
        c.drawRightString(x + w - 2, start_text_y - step, val)
        
        # CBM (GOV)
        c.drawString(x + 2, start_text_y - 2*step, "CBM")
        val = f"{reading.gov:.0f}"
        c.drawRightString(x + w - 2, start_text_y - 2*step, val)
        
        # %
        c.drawString(x + 2, start_text_y - 3*step, "%")
        val = f"{reading.fill_percent:.1f}" if reading.fill_percent else ""
        c.drawRightString(x + w - 2, start_text_y - 3*step, val)
        
        # 4. Footer: Grade (Colored) - Touches center line
        foot_y = y
        c.setFillColor(header_color) # Parcel Color
        c.rect(x, foot_y, w, footer_h, fill=1, stroke=1)
        
        c.setFillColor(header_text_color)
        c.setFont("Arial-Bold", 8)
        pname = parcel.name if parcel else ("SLOP" if reading.parcel_id=="0" else "")
        c.drawCentredString(x + w/2, foot_y + 0.15*cm, pname)

    # ---------------------------------------------------------
    # STARBOARD SIDE LAYOUT (Bottom) - MIRRORED
    # ---------------------------------------------------------
    # Header (Top): Grade Name (Colored)
    # Sub-Header: Receiver
    # Data Body
    # Footer (Bottom): Tank ID
    # ---------------------------------------------------------
    elif side == 'S':
        # 1. Header: Grade (Colored) - Touches center line
        c.setFillColor(header_color)
        c.setStrokeColor(colors.black)
        c.rect(x, y + h - header_h, w, header_h, fill=1, stroke=1)
        
        c.setFillColor(header_text_color)
        c.setFont("Arial-Bold", 8)
        pname = parcel.name if parcel else ("SLOP" if reading.parcel_id=="0" else "")
        c.drawCentredString(x + w/2, y + h - header_h + 0.15*cm, pname)
        
        # 2. Receiver
        # Need to be positioned below the Grade header
        rec_y = y + h - header_h - receiver_h
        c.setFillColor(colors.white)
        c.rect(x, rec_y, w, receiver_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black)
        c.setFont("Arial", 6)
        receiver = parcel.receiver if parcel else ""
        c.drawCentredString(x + w/2, rec_y + 0.15*cm, receiver[:20])
        
        # 3. Data Body
        data_bg = colors.HexColor("#86EFAC") # Light Green
        c.setFillColor(data_bg)
        c.rect(x, y + footer_h, w, data_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black) # Black text on light green
        c.setFont("Arial-Bold", 8)
        
        start_text_y = y + footer_h + data_h - 0.4*cm
        step = 0.4*cm
        
        # ULL
        c.drawString(x + 2, start_text_y, "ULL")
        val = f"{reading.ullage:.0f}" if reading.ullage else ""
        c.drawRightString(x + w - 2, start_text_y, val)
        
        # MT
        c.drawString(x + 2, start_text_y - step, "MT")
        val = f"{reading.mt_air:.0f}"
        c.drawRightString(x + w - 2, start_text_y - step, val)
        
        # CBM
        c.drawString(x + 2, start_text_y - 2*step, "CBM")
        val = f"{reading.gov:.0f}"
        c.drawRightString(x + w - 2, start_text_y - 2*step, val)
        
        # %
        c.drawString(x + 2, start_text_y - 3*step, "%")
        val = f"{reading.fill_percent:.1f}" if reading.fill_percent else ""
        c.drawRightString(x + w - 2, start_text_y - 3*step, val)
        
        # 4. Footer: Tank ID
        c.setFillColor(colors.white)
        c.rect(x, y, w, footer_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black) 
        c.setFont("Arial-Bold", 9)
        c.drawCentredString(x + w/2, y + 0.15*cm, tank_id)


def generate_stowage_plan(voyage: 'Voyage', filepath: str, ship_name: str = "") -> bool:
    """Generate the visual stowage plan PDF."""
    if not REPORTLAB_AVAILABLE:
        print("ReportLab not available.")
        return False
        
    try:
        c = canvas.Canvas(filepath, pagesize=landscape(A4))
        width, height = landscape(A4)
        c.setTitle("Stowage Plan")
        
        # Register Fonts
        try:
            font_path = Path("C:/Windows/Fonts/arial.ttf")
            font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
            if font_path.exists(): pdfmetrics.registerFont(TTFont('Arial', str(font_path)))
            if font_bold_path.exists(): pdfmetrics.registerFont(TTFont('Arial-Bold', str(font_bold_path)))
            font_norm, font_bold = 'Arial', 'Arial-Bold'
        except:
            font_norm, font_bold = 'Helvetica', 'Helvetica-Bold'

        # =================================================================
        # 1. HEADER & SUMMARY
        # =================================================================
        # Title
        title = f"M/T {ship_name} STOWAGE PLAN" if ship_name else "STOWAGE PLAN"
        c.setFont(font_bold, 18)
        c.drawCentredString(width/2, height - 1.5*cm, title)
        
        # Info Text (Voyage/Port) - Centered or Top-Right now? 
        # User requested Summary to Top-Left. 
        # So let's put Summary at Left, and Info at Center/Right.
        
        c.setFont(font_bold, 10)
        c.drawRightString(width - 1*cm, height - 2.5*cm, f"VOYAGE: {voyage.voyage_number}")
        c.drawRightString(width - 1*cm, height - 3.0*cm, f"PORT/TERMINAL: {voyage.port} / {voyage.terminal}")
        
        # Cargo Summary Table (Top Left)
        # Columns: TERMINAL, GRADE, DENSITY, TEMP, WEIGHT (MT IN AIR)
        
        c_x = 1*cm # Start Left
        c_y = height - 2.5*cm # Start high up
        c_w = 14*cm 
        row_h = 0.6*cm
        
        # Headers
        headers = ["TERMINAL", "GRADE", "DENSITY", "AVG.TEMP", "WEIGHT (MT)"]
        col_widths = [4*cm, 3*cm, 2*cm, 2.5*cm, 2.5*cm]
        curr_x = c_x
        
        c.setFillColor(colors.HexColor("#9CA3AF")) # Gray header
        c.rect(c_x, c_y, sum(col_widths), row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_bold, 8)
        
        for i, h_text in enumerate(headers):
            c.drawString(curr_x + 2, c_y + 0.15*cm, h_text)
            curr_x += col_widths[i]
            
        c_y -= row_h
        
        # Aggregate Parcel Data
        summary_data = {} 
        
        for reading in voyage.tank_readings.values():
            pid = reading.parcel_id
            if not pid: continue
            if pid not in summary_data:
                # Init based on Parcel (or Slop)
                name = "SLOP" if pid == "0" else "Unknown"
                color = "#E5E7EB" if pid == "0" else "#FFFFFF"
                dens = 0.0
                receiver = ""
                if pid != "0":
                    for p in voyage.parcels:
                        if p.id == pid:
                            name = p.name
                            color = p.color
                            dens = p.density_vac
                            receiver = p.receiver
                            break
                else:
                    # Slop data
                    dens = reading.density_vac or 0.0
                    
                summary_data[pid] = {
                    'term': receiver[:15], 'grade': name[:10], 'dens': dens, 
                    'color': color, 'temp': reading.temp_celsius, 'mt': 0
                }
            
            summary_data[pid]['mt'] += reading.mt_air
        
        # Draw Rows
        total_mt = 0
        for pid, data in summary_data.items():
            # Bg Color
            try: bg = colors.HexColor(data['color'])
            except: bg = colors.white
            
            c.setFillColor(bg)
            c.rect(c_x, c_y, sum(col_widths), row_h, fill=1, stroke=1)
            
            # Text
            c.setFillColor(_get_contrast_color(data['color']))
            c.setFont(font_norm, 8)
            
            curr_x = c_x
            # Terminal
            c.drawString(curr_x + 2, c_y + 0.15*cm, data['term'])
            curr_x += col_widths[0]
            # Grade
            c.drawString(curr_x + 2, c_y + 0.15*cm, data['grade'])
            curr_x += col_widths[1]
            # Density
            c.drawString(curr_x + 2, c_y + 0.15*cm, f"{data['dens']:.4f}")
            curr_x += col_widths[2]
            # Temp
            c.drawString(curr_x + 2, c_y + 0.15*cm, f"{data['temp']:.1f}")
            curr_x += col_widths[3]
            # Weight
            c.drawRightString(curr_x + col_widths[4] - 2, c_y + 0.15*cm, f"{data['mt']:.0f}")
            
            total_mt += data['mt']
            c_y -= row_h
            
        # DRAFT BOX (Top Right - below info?)
        d_x = width - 5*cm
        d_y = height - 4*cm
        d_w = 4*cm
        
        c.setFillColor(colors.lightgrey)
        c.rect(d_x, d_y, d_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_bold, 8)
        c.drawCentredString(d_x + d_w/2, d_y + 0.15*cm, "FINAL DRAFTS")
        
        d_y -= row_h
        # Fwd
        c.setFillColor(colors.white)
        c.rect(d_x, d_y, d_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(d_x + 2, d_y + 0.15*cm, "Draft FWD")
        c.drawRightString(d_x + d_w - 2, d_y + 0.15*cm, f"{voyage.drafts.fwd:.2f}")
        
        d_y -= row_h
        # Aft
        c.setFillColor(colors.white)
        c.rect(d_x, d_y, d_w, row_h, fill=1, stroke=1)
        c.drawString(d_x + 2, d_y + 0.15*cm, "Draft AFT")
        c.drawRightString(d_x + d_w - 2, d_y + 0.15*cm, f"{voyage.drafts.aft:.2f}")

        # =================================================================
        # 2. TANK GRID (Main Visual)
        # =================================================================
        # Order: 8 -> 1 (Left to Right)
        
        tank_groups = {} 
        slop_group = {} 
        
        for tid, reading in voyage.tank_readings.items():
            if "SLOP" in tid.upper():
                s_side = 'P' if 'P' in tid.upper() else 'S'
                slop_group[s_side] = (tid, reading)
                continue
                
            digits = ''.join(filter(str.isdigit, tid))
            if digits:
                num = int(digits)
                if num not in tank_groups: tank_groups[num] = {}
                side = 'S' if 'S' in tid.upper() else ('P' if 'P' in tid.upper() else 'C')
                tank_groups[num][side] = (tid, reading)
        
        sorted_nums = sorted(tank_groups.keys(), reverse=True)
        
        # Grid settings
        grid_cx = width / 2
        grid_cy = 10*cm # Moves the strip up/down
        
        box_w = 2.4*cm
        gap = 0.1*cm
        
        col_count = len(sorted_nums) + (1 if slop_group else 0)
        total_w = col_count * (box_w + gap)
        
        start_x = grid_cx - (total_w / 2)
        curr_x = start_x
        
        cell_h = 5.0*cm 
        center_y = grid_cy
        
        # Draw SLOPS (Left)
        if slop_group:
            # Port Slop
            if 'P' in slop_group:
                tid, reading = slop_group['P']
                parcel = None 
                _draw_tank_cell(c, curr_x, center_y, box_w, cell_h, reading, parcel, tid, 'P')
            
            # Stbd Slop
            if 'S' in slop_group:
                tid, reading = slop_group['S']
                parcel = None
                # FIXED: Draw at center_y - cell_h
                _draw_tank_cell(c, curr_x, center_y - cell_h, box_w, cell_h, reading, parcel, tid, 'S')
            
            curr_x += box_w + gap
            
        # Draw Main Tanks (8..1)
        for num in sorted_nums:
            group = tank_groups[num]
            
            # Port
            if 'P' in group:
                tid, reading = group['P']
                parcel = next((p for p in voyage.parcels if p.id == reading.parcel_id), None)
                _draw_tank_cell(c, curr_x, center_y, box_w, cell_h, reading, parcel, tid, 'P')
            
            # Starboard
            if 'S' in group:
                tid, reading = group['S']
                parcel = next((p for p in voyage.parcels if p.id == reading.parcel_id), None)
                _draw_tank_cell(c, curr_x, center_y - cell_h, box_w, cell_h, reading, parcel, tid, 'S')
                
            curr_x += box_w + gap
            
        c.save()
        return True
        
    except Exception as e:
        traceback.print_exc()
        print(f"Error generating visual stowage plan: {e}")
        return False
