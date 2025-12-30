"""
ASCII text export with aligned columns.
Suitable for email, terminal printing, and legacy systems.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..models.voyage import Voyage


def export_ascii_report(voyage: 'Voyage', filepath: str) -> bool:
    """
    Export voyage data as aligned ASCII text.
    
    Args:
        voyage: Voyage object with all tank readings
        filepath: Output file path
        
    Returns:
        True if successful
        
    Format:
        - Fixed-width columns for alignment
        - Header with Voyage/Port info
        - Draft/Trim section
        - Tank table with Warning indicators
        - Totals and Officer Signatures
    """
    try:
        lines = []
        
        # Header
        lines.append("=" * 100)
        lines.append("                           ULLAGE REPORT")
        lines.append("=" * 100)
        lines.append("")
        
        # Voyage info
        lines.append(f"Voyage No    : {voyage.voyage_number:<20} Date         : {voyage.date}")
        lines.append(f"Port         : {voyage.port:<20} Terminal     : {voyage.terminal}")
        lines.append(f"V.E.F.       : {voyage.vef:.5f}")
        lines.append("")
        
        # Draft info
        lines.append(f"Draft AFT    : {voyage.drafts.aft:.2f} m")
        lines.append(f"Draft FWD    : {voyage.drafts.fwd:.2f} m")
        lines.append(f"Trim         : {voyage.drafts.trim:+.2f} m")
        lines.append("")
        
        # Table header
        lines.append("-" * 100)
        header = (
            f"{'Tank':<6} {'Grade':<12} {'Receiver':<12} {'Ullage':>8} "
            f"{'%Fill':>6} {'TOV':>10} {'VCF':>8} {'GSV':>10} {'MT(Air)':>10}"
        )
        lines.append(header)
        lines.append("-" * 100)
        
        # Tank rows
        for tank_id, reading in voyage.tank_readings.items():
            ullage_str = f"{reading.ullage:.1f}" if reading.ullage else "-"
            fill_str = f"{reading.fill_percent:.1f}" if reading.fill_percent else "-"
            
            row = (
                f"{tank_id:<6} "
                f"{reading.grade[:12]:<12} "        # Truncate Grade to 12 chars
                f"{reading.receiver[:12]:<12} "     # Truncate Receiver to 12 chars
                f"{ullage_str:>8} "
                f"{fill_str:>6} "
                f"{reading.tov:>10.3f} "
                f"{reading.vcf:>8.5f} "
                f"{reading.gsv:>10.3f} "
                f"{reading.mt_air:>10.3f}"
            )
            
            # Add warning indicator
            if reading.warning == "high_high":
                row += " [!!]"
            elif reading.warning == "high":
                row += " [!]"
            elif reading.warning == "low":
                row += " [L]"
            
            lines.append(row)
        
        # Totals
        lines.append("-" * 100)
        lines.append(
            f"{'TOTAL':<6} {'':<12} {'':<12} {'':<8} {'':<6} "
            f"{'':<10} {'':<8} {voyage.total_gsv:>10.3f} {voyage.total_mt:>10.3f}"
        )
        lines.append("=" * 100)
        
        # Officers
        lines.append("")
        lines.append(f"Chief Officer: {voyage.chief_officer:<30} Master: {voyage.master}")
        lines.append("")
        
        # Legend
        lines.append("Legend: [!!] = High High (>=98%), [!] = High (>95%), [L] = Low (<65%)")
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return True
    except Exception as e:
        print(f"Error exporting ASCII report: {e}")
        return False


def generate_ascii_report(voyage: 'Voyage') -> str:
    """
    Generate ASCII report as string (for preview/clipboard).
    
    Args:
        voyage: Voyage object
        
    Returns:
        Report as string
    """
    import tempfile
    import os
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    export_ascii_report(voyage, temp_path)
    
    with open(temp_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    os.unlink(temp_path)
    return content
