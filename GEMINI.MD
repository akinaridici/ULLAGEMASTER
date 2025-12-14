# GEMINI - Project Vision

**Project Name**: UllageMaster (Tanker Cargo Calculator)  
**Platform**: Windows Desktop Application  
**Core Technology**: Python (PyQt6)

---

## Project Soul

UllageMaster replaces the traditional Excel-based cargo calculation spreadsheet used on oil tankers. It provides a reliable, automated, and user-friendly solution for Chief Officers to calculate cargo quantities during loading and discharging operations.

The application must feel like a **"digital upgrade"** of the Excel sheet—not a completely new system. Officers who have used spreadsheets for years should feel instantly comfortable.

---

## Key Directives

| Directive | Description |
|-----------|-------------|
| **Precision** | All calculations (interpolation, VCF, trim correction) must match or exceed Excel's precision. |
| **Familiarity** | The UI must resemble the Excel grid layout. Blue cells = input, others = calculated. |
| **Reliability** | Auto-save, crash recovery, and clear error messages are mandatory. |
| **Flexibility** | Support for 6-pair, 8-pair, or 10-pair tank configurations. Metric and Imperial units. |
| **Portability** | Ship configuration and voyage data must be easily exportable/importable (JSON/CSV). |

---

## Core Calculations

1. **Ullage → Volume**: Lookup from tank-specific ullage table with linear interpolation.
2. **Trim Correction**: Bilinear interpolation based on ullage AND trim value.
3. **VCF (Volume Correction Factor)**: ASTM 54B calculation based on temperature and density.
4. **GSV (Gross Standard Volume)**: `(TOV + Trim Correction) × VCF`
5. **MT (Metric Tons)**: `GSV × Density`
6. **V.E.F. (Vessel Experience Factor)**: Optional multiplier for historical correction.

---

## User Experience

- **Blue Cells**: User input only (Ullage, Temp, Density, Receiver, etc.)
- **Gray/White Cells**: Auto-calculated (TOV, GSV, MT, etc.)
- **Red/Yellow Cells**: Warnings (high ullage, temperature out of range, discrepancy alerts)

The user should be able to:
1. Set up their ship once (tank configuration, tables).
2. Enter voyage details (Port, Date, V.E.F., Drafts).
3. Input ullage readings per tank.
4. See all calculations update in real-time.
5. Generate a total ullage report.

---

## Reference

![Excel Interface Reference](C:/Users/akina/.gemini/antigravity/brain/3a402ead-18d3-48b5-837b-023be3492519/uploaded_image_1765711000323.png)

This Excel spreadsheet is the primary inspiration for the UI layout and workflow.
