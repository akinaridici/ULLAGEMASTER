"""
Stowage Plan PDF Report Generator.

Generates a visual stowage plan PDF with:
- Header (Ship name, Voyage, Port/Terminal)
- Parcel legend table with color coding
- Dynamic ship hull outline with tank grid
- Support for 6, 9, 12+ tank pair configurations
- SLOP tank support
- Transparent colors for ink saving
"""

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, List, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import traceback

if TYPE_CHECKING:
    from models.voyage import Voyage
    from models.ship import ShipConfig
    from models.tank import TankReading
    from models.parcel import Parcel


# Transparency level for colors (0.0 = fully transparent, 1.0 = opaque)
COLOR_ALPHA = 0.5

# Ship hull colors
HULL_STROKE_COLOR = colors.Color(0.2, 0.2, 0.2)
HULL_FILL_COLOR = colors.Color(0.95, 0.97, 1.0, 0.3)  # Very light blue with transparency
DECK_LINE_COLOR = colors.Color(0.3, 0.3, 0.3)


def _hex_to_transparent(hex_color: str, alpha: float = COLOR_ALPHA) -> colors.Color:
    """Convert hex color to transparent version."""
    try:
        if not hex_color or not hex_color.startswith('#'):
            return colors.Color(0.9, 0.9, 0.9, alpha)
        h = hex_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        return colors.Color(r, g, b, alpha)
    except:
        return colors.Color(0.9, 0.9, 0.9, alpha)


def _get_contrast_color(hex_color: str) -> colors.Color:
    """Determine best text color (black or white) for given background."""
    try:
        if not hex_color or not hex_color.startswith('#'):
            return colors.black
        h = hex_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return colors.black if luminance > 0.5 else colors.white
    except:
        return colors.black


def _register_fonts():
    """Register Arial fonts, fallback to Helvetica."""
    try:
        font_path = Path("C:/Windows/Fonts/arial.ttf")
        font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
        if font_path.exists():
            pdfmetrics.registerFont(TTFont('Arial', str(font_path)))
        if font_bold_path.exists():
            pdfmetrics.registerFont(TTFont('Arial-Bold', str(font_bold_path)))
        return 'Arial', 'Arial-Bold'
    except:
        return 'Helvetica', 'Helvetica-Bold'


def _draw_ship_hull(
    c: canvas.Canvas,
    x: float, y: float,
    hull_width: float, hull_height: float,
    bow_length: float, stern_length: float
) -> None:
    """
    Draw a professional ship hull outline.
    
    Layout (left to right):
    - Stern (square back) on the left
    - Main body (rectangular) in the middle
    - Bow (pointed/curved) on the right
    
    Args:
        c: Canvas object
        x: Left edge of the hull (stern)
        y: Bottom edge of the hull
        hull_width: Total width including bow and stern
        hull_height: Height of the hull
        bow_length: Length of the bow section
        stern_length: Length of the stern section
        
    Drawing Steps:
        1. Stern curve (left side)
        2. Top edge (straight line)
        3. Bow curves (pointed tip on right)
        4. Bottom edge (straight line back to stern)
        5. Center line (dashed deck marking)
    """
    body_width = hull_width - bow_length - stern_length
    
    # Start path for hull
    path = c.beginPath()
    
    # Define key points
    stern_x = x
    stern_top = y + hull_height
    stern_bottom = y
    
    body_left = x + stern_length
    body_right = x + stern_length + body_width
    
    bow_tip_x = x + hull_width
    bow_mid_y = y + hull_height / 2
    
    # Draw hull outline (clockwise from stern bottom-left)
    
    # 1. Stern - slightly rounded back
    path.moveTo(stern_x + stern_length * 0.3, stern_bottom)
    
    # Stern bottom curve
    path.curveTo(
        stern_x, stern_bottom,  # Control point 1
        stern_x, stern_bottom + hull_height * 0.2,  # Control point 2
        stern_x, stern_bottom + hull_height * 0.3  # End point
    )
    
    # Stern left edge (straight)
    path.lineTo(stern_x, stern_top - hull_height * 0.3)
    
    # Stern top curve
    path.curveTo(
        stern_x, stern_top - hull_height * 0.2,  # Control point 1
        stern_x, stern_top,  # Control point 2
        stern_x + stern_length * 0.3, stern_top  # End point
    )
    
    # 2. Top edge to bow
    path.lineTo(body_right, stern_top)
    
    # 3. Bow - smooth pointed curve (top side)
    path.curveTo(
        body_right + bow_length * 0.5, stern_top,  # Control point 1
        bow_tip_x - bow_length * 0.1, bow_mid_y + hull_height * 0.15,  # Control point 2
        bow_tip_x, bow_mid_y  # Bow tip
    )
    
    # 4. Bow - smooth pointed curve (bottom side)
    path.curveTo(
        bow_tip_x - bow_length * 0.1, bow_mid_y - hull_height * 0.15,  # Control point 1
        body_right + bow_length * 0.5, stern_bottom,  # Control point 2
        body_right, stern_bottom  # End at body bottom-right
    )
    
    # 5. Bottom edge back to stern
    path.lineTo(stern_x + stern_length * 0.3, stern_bottom)
    
    path.close()
    
    # Fill hull with light color
    c.setFillColor(HULL_FILL_COLOR)
    c.setStrokeColor(HULL_STROKE_COLOR)
    c.setLineWidth(1.5)
    c.drawPath(path, fill=1, stroke=1)
    
    # Draw center line (deck marking)
    c.setStrokeColor(DECK_LINE_COLOR)
    c.setLineWidth(0.5)
    c.setDash([3, 2])  # Dashed line
    c.line(stern_x + stern_length * 0.5, bow_mid_y, body_right + bow_length * 0.3, bow_mid_y)
    c.setDash([])  # Reset dash


def _draw_tank_cell(
    c: canvas.Canvas,
    x: float, y: float,
    w: float, h: float,
    tank_label: str,
    reading: Optional['TankReading'],
    parcel: Optional['Parcel'],
    is_slop: bool,
    slop_label: str,
    font_norm: str,
    font_bold: str
) -> None:
    """
    Draw a single tank cell.
    
    Layout (top to bottom):
    - Header: Parcel name (colored background)
    - Receiver row (colored background)
    - Data rows: ULL, MT, CBM, %
    - Footer: Tank label (e.g., "8P", "1S")
    """
    # Determine colors and text
    if reading is None or (not reading.parcel_id and reading.ullage is None):
        # Empty tank
        header_color = _hex_to_transparent("#E5E7EB", 0.3)
        header_text = "EMPTY"
        receiver_text = ""
        text_color = colors.black
        hex_color = "#E5E7EB"
    elif is_slop:
        # SLOP tank
        header_color = _hex_to_transparent("#9CA3AF", COLOR_ALPHA)
        header_text = slop_label or "SLOP"
        receiver_text = ""
        text_color = colors.black
        hex_color = "#9CA3AF"
    elif parcel:
        # Normal parcel
        hex_color = parcel.color if parcel.color else "#FFFFFF"
        header_color = _hex_to_transparent(hex_color, COLOR_ALPHA)
        header_text = parcel.name or ""
        receiver_text = parcel.receiver or ""
        text_color = _get_contrast_color(hex_color)
    else:
        # Unknown state
        header_color = _hex_to_transparent("#E5E7EB", 0.3)
        header_text = ""
        receiver_text = ""
        text_color = colors.black
        hex_color = "#E5E7EB"

    # Layout dimensions
    header_h = 0.5 * cm
    receiver_h = 0.5 * cm  # Increased for 2 lines
    footer_h = 0.4 * cm
    data_h = h - header_h - receiver_h - footer_h
    
    # 1. Header (Parcel Name) - colored with transparency
    c.setFillColor(header_color)
    c.setStrokeColor(colors.Color(0.4, 0.4, 0.4))
    c.setLineWidth(0.5)
    c.rect(x, y + h - header_h, w, header_h, fill=1, stroke=1)
    
    c.setFillColor(text_color)
    c.setFont(font_bold, 6)
    display_header = header_text[:12] if len(header_text) > 12 else header_text
    c.drawCentredString(x + w/2, y + h - header_h + 0.12*cm, display_header)
    
    # 2. Receiver row - colored with transparency (2 lines with word wrap)
    rec_y = y + h - header_h - receiver_h
    c.setFillColor(header_color)
    c.rect(x, rec_y, w, receiver_h, fill=1, stroke=1)
    
    c.setFillColor(text_color)
    c.setFont(font_norm, 5)
    
    # Word wrap logic - break at spaces
    if receiver_text:
        max_chars_per_line = int(w / 1.8)  # Approximate chars per line based on width
        words = receiver_text.split()
        line1 = ""
        line2 = ""
        
        for word in words:
            if len(line1) + len(word) + 1 <= max_chars_per_line:
                line1 = (line1 + " " + word).strip()
            elif len(line2) + len(word) + 1 <= max_chars_per_line:
                line2 = (line2 + " " + word).strip()
            else:
                break  # No more space
        
        # Draw 2 lines centered
        if line1:
            c.drawCentredString(x + w/2, rec_y + receiver_h - 0.22*cm, line1)  # Moved down
        if line2:
            c.drawCentredString(x + w/2, rec_y + 0.06*cm, line2)
    
    # 3. Data body - white background
    data_y = y + footer_h
    c.setFillColor(colors.white)
    c.rect(x, data_y, w, data_h, fill=1, stroke=1)
    
    # Data rows
    c.setFillColor(colors.black)
    c.setFont(font_bold, 6)
    
    row_h = data_h / 4
    labels = ["ULL", "MT", "CBM", "%"]
    
    if reading and reading.parcel_id:
        values = [
            f"{reading.ullage:.0f}" if reading.ullage else "",
            f"{reading.mt_air:.0f}" if reading.mt_air else "0",
            f"{reading.gov:.0f}" if reading.gov else "0",
            f"{reading.fill_percent:.1f}" if reading.fill_percent else ""
        ]
    else:
        values = ["", "", "", ""]
    
    for i, (label, value) in enumerate(zip(labels, values)):
        row_y = data_y + data_h - (i + 1) * row_h + 0.06*cm
        c.drawString(x + 1, row_y, label)
        c.drawRightString(x + w - 1, row_y, value)
    
    # 4. Footer (Tank Label) - white background
    c.setFillColor(colors.white)
    c.rect(x, y, w, footer_h, fill=1, stroke=1)
    
    c.setFillColor(colors.black)
    c.setFont(font_bold, 7)
    c.drawCentredString(x + w/2, y + 0.08*cm, tank_label)


def generate_stowage_plan_pdf(
    voyage: 'Voyage',
    ship_config: 'ShipConfig',
    filepath: str,
    report_data: dict
) -> bool:
    """
    Generate the Stowage Plan PDF report.
    
    Args:
        voyage: Voyage object with parcels and tank_readings
        ship_config: Ship configuration with tanks list
        filepath: Output PDF path
        report_data: Dict from Report Functions widget (port, terminal, slop_label, etc.)
    
    Returns:
        True if successful, False otherwise
        
    Layout Overview:
        - Landscape A4
        - Top Left: Parcel Summary Table (Legend)
        - Top Center/Right: Ship Title and Voyage Info
        - Top Right: Final Drafts Box
        - Center/Bottom: Ship Hull Diagram containing Tank Grid
        - Hull Layout: Stern (Left) -> Tanks (8..1) -> Bow (Right)
    """
    try:
        c = canvas.Canvas(filepath, pagesize=landscape(A4))
        width, height = landscape(A4)
        c.setTitle("Stowage Plan")
        
        font_norm, font_bold = _register_fonts()
        
        # Margins (2cm on all sides)
        margin_x = 2 * cm
        margin_y = 2 * cm
        
        # =================================================================
        # 1. HEADER
        # =================================================================
        # Fix ship name - remove duplicate M/T if already present
        ship_name = ship_config.ship_name
        if ship_name.upper().startswith('M/T ') or ship_name.upper().startswith('MT '):
            title = f"{ship_name} STOWAGE PLAN"
        else:
            title = f"M/T {ship_name} STOWAGE PLAN"
        c.setFont(font_bold, 16)
        c.drawCentredString(width/2, height - 2*cm, title)  # 2cm from top
        
        # NOTE: Voyage/Port info will be drawn after hull position is calculated for alignment
        
        # =================================================================
        # PRE-CALCULATE HULL POSITION FOR ALIGNMENT
        # =================================================================
        # Count tanks for hull width calculation
        tank_count = len([t for t in ship_config.tanks if 'SLOP' not in t.name.upper()])
        num_cols = (tank_count // 2) + (1 if any('SLOP' in t.name.upper() for t in ship_config.tanks) else 0)
        if num_cols < 1:
            num_cols = 8  # Default
        
        hull_padding = 0.2 * cm
        bow_length = 2.0 * cm
        stern_length = 0.8 * cm
        cell_h = 2.8 * cm
        gap = 0.04 * cm
        
        available_width = width - 2 * margin_x - 1.5*cm - bow_length - stern_length
        cell_w = min((available_width - gap * (num_cols - 1)) / num_cols, 2.8 * cm)
        total_tank_width = num_cols * cell_w + (num_cols - 1) * gap
        hull_width = total_tank_width + bow_length + stern_length + 2 * hull_padding
        
        # Hull X position (centered)
        pre_hull_x = (width - hull_width) / 2
        pre_hull_right = pre_hull_x + hull_width  # Right edge of hull
        
        # =================================================================
        # 1b. VOYAGE/PORT INFO (Aligned with hull/table)
        # =================================================================
        c.setFont(font_bold, 10)
        info_y = height - 2.8*cm
        c.drawString(pre_hull_x, info_y, f"VOYAGE/SEFER: {voyage.voyage_number}")
        c.drawString(pre_hull_x, info_y - 0.5*cm, f"PORT/TERMINAL: {report_data.get('port', voyage.port)} / {report_data.get('terminal', voyage.terminal)}")
        
        # =================================================================
        # 2. PARCEL LEGEND TABLE (Top area) - Aligned with hull
        # =================================================================
        table_x = pre_hull_x  # Align with hull left edge
        table_y = height - 4.3*cm  # Adjusted for 2cm top margin
        row_h = 0.5*cm
        
        # Column definitions
        col_widths = [4*cm, 3*cm, 1.8*cm, 1.8*cm, 2.2*cm]
        headers = ["TERMINAL", "GRADE", "DENSITY", "AVG TEMP", "WEIGHT (MT)"]
        
        # Header row - light gray
        c.setFillColor(colors.Color(0.82, 0.84, 0.86, 0.7))
        c.rect(table_x, table_y, sum(col_widths), row_h, fill=1, stroke=1)
        
        c.setFillColor(colors.black)
        c.setFont(font_bold, 8)
        curr_x = table_x
        for i, h_text in enumerate(headers):
            c.drawString(curr_x + 2, table_y + 0.12*cm, h_text)
            curr_x += col_widths[i]
        
        # Aggregate parcel data
        parcel_summary = {}  # parcel_id -> {receiver, name, density, temp_sum, temp_count, mt_total, color}
        slop_label = report_data.get('slop_label', 'SLOP')
        
        for tid, reading in voyage.tank_readings.items():
            pid = reading.parcel_id
            if not pid:
                continue
            
            if pid not in parcel_summary:
                if pid == "0":
                    # SLOP
                    parcel_summary[pid] = {
                        'receiver': '',
                        'name': slop_label,
                        'density': reading.density_vac or 0.0,
                        'temp_sum': 0.0,
                        'temp_count': 0,
                        'mt_total': 0.0,
                        'color': '#9CA3AF'
                    }
                else:
                    # Find parcel
                    parcel = next((p for p in voyage.parcels if p.id == pid), None)
                    if parcel:
                        parcel_summary[pid] = {
                            'receiver': parcel.receiver or '',
                            'name': parcel.name or '',
                            'density': parcel.density_vac or 0.0,
                            'temp_sum': 0.0,
                            'temp_count': 0,
                            'mt_total': 0.0,
                            'color': parcel.color or '#FFFFFF'
                        }
                    else:
                        continue
            
            # Accumulate
            parcel_summary[pid]['mt_total'] += reading.mt_air or 0.0
            if reading.temp_celsius:
                parcel_summary[pid]['temp_sum'] += reading.temp_celsius
                parcel_summary[pid]['temp_count'] += 1
        
        # Draw parcel rows with transparency
        table_y -= row_h
        for pid, data in parcel_summary.items():
            # Background color with transparency
            bg = _hex_to_transparent(data['color'], COLOR_ALPHA)
            
            c.setFillColor(bg)
            c.rect(table_x, table_y, sum(col_widths), row_h, fill=1, stroke=1)
            
            # Text
            text_c = _get_contrast_color(data['color'])
            c.setFillColor(text_c)
            c.setFont(font_norm, 7)
            
            curr_x = table_x
            # Terminal (Receiver)
            c.drawString(curr_x + 2, table_y + 0.12*cm, data['receiver'][:20])
            curr_x += col_widths[0]
            # Grade
            c.drawString(curr_x + 2, table_y + 0.12*cm, data['name'][:15])
            curr_x += col_widths[1]
            # Density
            c.drawString(curr_x + 2, table_y + 0.12*cm, f"{data['density']:.4f}")
            curr_x += col_widths[2]
            # Avg Temp
            avg_temp = data['temp_sum'] / data['temp_count'] if data['temp_count'] > 0 else 0
            c.drawString(curr_x + 2, table_y + 0.12*cm, f"{avg_temp:.1f}")
            curr_x += col_widths[3]
            # Weight
            c.drawRightString(curr_x + col_widths[4] - 2, table_y + 0.12*cm, f"{data['mt_total']:.0f}")
            
            table_y -= row_h
        
        # =================================================================
        # 3. DRAFT BOX (Top right) - Aligned with hull right edge
        # =================================================================
        draft_w = 4*cm
        draft_x = pre_hull_right - draft_w  # Right edge aligned with hull
        draft_y = height - 4.3*cm  # Same level as table
        
        # Header
        c.setFillColor(colors.Color(0.82, 0.84, 0.86, 0.7))
        c.rect(draft_x, draft_y, draft_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_bold, 8)
        c.drawCentredString(draft_x + draft_w/2, draft_y + 0.12*cm, "FINAL VALUES")
        
        # Draft FWD
        draft_y -= row_h
        c.setFillColor(colors.white)
        c.rect(draft_x, draft_y, draft_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_norm, 8)
        c.drawString(draft_x + 2, draft_y + 0.12*cm, "Draft FWD")
        c.drawRightString(draft_x + draft_w - 2, draft_y + 0.12*cm, f"{voyage.drafts.fwd:.2f}")
        
        # Draft AFT
        draft_y -= row_h
        c.setFillColor(colors.white)
        c.rect(draft_x, draft_y, draft_w, row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(draft_x + 2, draft_y + 0.12*cm, "Draft AFT")
        c.drawRightString(draft_x + draft_w - 2, draft_y + 0.12*cm, f"{voyage.drafts.aft:.2f}")
        
        # =================================================================
        # 4. TANK GRID WITH SHIP HULL
        # =================================================================
        # Group tanks by number and side - including SLOP tanks
        tank_groups: Dict[int, Dict[str, Tuple[str, Optional['TankReading'], str]]] = {}
        slop_tanks: Dict[str, Tuple[str, Optional['TankReading'], str]] = {}  # Side -> (label, reading, id)
        
        for tank in ship_config.tanks:
            tank_name_upper = tank.name.upper()
            reading = voyage.tank_readings.get(tank.id)
            
            # Check if this is a SLOP tank (by name)
            if 'SLOP' in tank_name_upper:
                # Determine side
                if 'S' in tank_name_upper and 'P' not in tank_name_upper.replace('SLOP', ''):
                    side = 'S'
                elif 'P' in tank_name_upper:
                    side = 'P'
                else:
                    side = 'P'  # Default
                
                tank_label = f"SL{side}"
                slop_tanks[side] = (tank_label, reading, tank.id)
                continue
            
            # Extract number from tank name/id
            digits = ''.join(filter(str.isdigit, tank.name))
            if not digits:
                continue
            num = int(digits)
            
            # Determine side from name
            if 'STARBOARD' in tank_name_upper or tank_name_upper.endswith('S'):
                side = 'S'
            elif 'PORT' in tank_name_upper or tank_name_upper.endswith('P'):
                side = 'P'
            else:
                side = 'P'  # Default to Port
            
            if num not in tank_groups:
                tank_groups[num] = {}
            
            # Create abbreviated tank label (e.g., "8P", "1S")
            tank_label = f"{num}{side}"
            
            tank_groups[num][side] = (tank_label, reading, tank.id)
        
        if not tank_groups and not slop_tanks:
            c.save()
            return True
        
        # Grid positioning
        grid_center_y = 6.5 * cm  # Center Y of the grid area
        cell_h = 2.8 * cm
        gap = 0.06 * cm
        
        # Total height for both rows
        total_tank_height = cell_h * 2 + gap
        grid_top_y = grid_center_y + total_tank_height / 2
        grid_bottom_y = grid_center_y - total_tank_height / 2
        
        # Calculate cell width based on tank count (including SLOP column if exists)
        num_cols = len(tank_groups) + (1 if slop_tanks else 0)
        
        # Ship hull dimensions (matching pre-calculation)
        hull_padding = 0.2 * cm
        bow_length = 2.0 * cm
        stern_length = 0.8 * cm
        
        available_width = width - 2 * margin_x - 1.5*cm - bow_length - stern_length
        cell_w = min((available_width - gap * (num_cols - 1)) / num_cols, 2.8 * cm)
        
        total_tank_width = num_cols * cell_w + (num_cols - 1) * gap
        
        # Hull dimensions
        hull_width = total_tank_width + bow_length + stern_length + 2 * hull_padding
        hull_height = total_tank_height + 2 * hull_padding
        
        # Center the hull on page
        hull_x = (width - hull_width) / 2
        hull_y = grid_bottom_y - hull_padding
        
        # Draw ship hull first (behind tanks)
        _draw_ship_hull(c, hull_x, hull_y, hull_width, hull_height, bow_length, stern_length)
        
        # Tank starting position (inside hull, after stern)
        start_x = hull_x + stern_length + hull_padding
        
        # Build parcel lookup
        parcel_map = {p.id: p for p in voyage.parcels}
        
        # Draw SLOP tanks first (leftmost position, near stern)
        curr_x = start_x
        port_y = grid_top_y - cell_h
        starboard_y = grid_bottom_y
        
        if slop_tanks:
            # Port SLOP
            if 'P' in slop_tanks:
                tank_label, reading, tank_id = slop_tanks['P']
                is_slop = reading and reading.parcel_id == "0"
                parcel = parcel_map.get(reading.parcel_id) if reading and reading.parcel_id and reading.parcel_id != "0" else None
                
                _draw_tank_cell(
                    c, curr_x, port_y, cell_w, cell_h,
                    tank_label, reading, parcel, is_slop, slop_label,
                    font_norm, font_bold
                )
            
            # Starboard SLOP
            if 'S' in slop_tanks:
                tank_label, reading, tank_id = slop_tanks['S']
                is_slop = reading and reading.parcel_id == "0"
                parcel = parcel_map.get(reading.parcel_id) if reading and reading.parcel_id and reading.parcel_id != "0" else None
                
                _draw_tank_cell(
                    c, curr_x, starboard_y, cell_w, cell_h,
                    tank_label, reading, parcel, is_slop, slop_label,
                    font_norm, font_bold
                )
            
            curr_x += cell_w + gap
        
        # Draw main tanks (ordered by number, highest on left = stern, 1 on right = bow)
        sorted_nums = sorted(tank_groups.keys(), reverse=True)
        
        for num in sorted_nums:
            group = tank_groups[num]
            
            # Port tank (top row)
            if 'P' in group:
                tank_label, reading, tank_id = group['P']
                parcel = None
                is_slop = False
                
                if reading and reading.parcel_id:
                    if reading.parcel_id == "0":
                        is_slop = True
                    else:
                        parcel = parcel_map.get(reading.parcel_id)
                
                _draw_tank_cell(
                    c, curr_x, port_y, cell_w, cell_h,
                    tank_label, reading, parcel, is_slop, slop_label,
                    font_norm, font_bold
                )
            
            # Starboard tank (bottom row)
            if 'S' in group:
                tank_label, reading, tank_id = group['S']
                parcel = None
                is_slop = False
                
                if reading and reading.parcel_id:
                    if reading.parcel_id == "0":
                        is_slop = True
                    else:
                        parcel = parcel_map.get(reading.parcel_id)
                
                _draw_tank_cell(
                    c, curr_x, starboard_y, cell_w, cell_h,
                    tank_label, reading, parcel, is_slop, slop_label,
                    font_norm, font_bold
                )
            
            curr_x += cell_w + gap
        
        # =================================================================
        # 5. SIDE LABELS (P/S indicators) - Left of hull
        # =================================================================
        label_x = hull_x - 0.8*cm
        
        c.setFont(font_bold, 14)
        c.setFillColor(colors.Color(0.86, 0.15, 0.15))  # Red for Port
        c.drawCentredString(label_x, port_y + cell_h/2, "P")
        
        c.setFillColor(colors.Color(0.13, 0.72, 0.30))  # Green for Starboard
        c.drawCentredString(label_x, starboard_y + cell_h/2, "S")
        
        # BOW/STERN labels removed as per user request
        
        # =================================================================
        # 7. CHIEF OFFICER SIGNATURE (Bottom Right)
        # =================================================================
        chief_officer = voyage.chief_officer if hasattr(voyage, 'chief_officer') else ""
        if chief_officer:
            c.setFillColor(colors.black)
            c.setFont(font_norm, 9)
            c.drawRightString(width - margin_x, margin_y + 0.8*cm, "Chief Officer:")
            c.setFont(font_bold, 10)
            c.drawRightString(width - margin_x, margin_y + 0.2*cm, chief_officer)
        
        c.save()
        print(f"Stowage Plan PDF generated: {filepath}")
        return True
        
    except Exception as e:
        traceback.print_exc()
        print(f"Error generating stowage plan PDF: {e}")
        return False
