# Product Requirements Document (PRD) - UllageMaster

## 1. Introduction

UllageMaster is a Windows desktop application for calculating cargo quantities on oil tankers. It replaces manual Excel-based calculations with an automated, reliable system that handles:

- Ullage-to-volume conversion with interpolation
- Trim corrections (bilinear interpolation)
- Temperature-based volume correction (ASTM 54B / VCF)
- Discrepancy analysis between ship and shore figures

---

## 2. Technical Stack

| Component | Technology |
|-----------|------------|
| **OS** | Windows 10/11 |
| **Language** | Python 3.10+ |
| **GUI Framework** | PyQt6 |
| **Data Processing** | Pandas, NumPy |
| **Persistence** | JSON (config), CSV (tables, voyages) |

---

## 3. Data Structures

### 3.1. Ship Configuration (JSON)
```json
{
  "ship_name": "M/T EXAMPLE",
  "tank_pairs": 6,
  "tanks": [
    {"id": "1P", "name": "No.1 Port", "capacity_m3": 1500},
    {"id": "1S", "name": "No.1 Starboard", "capacity_m3": 1500},
    {"id": "2P", "name": "No.2 Port", "capacity_m3": 2000},
    ...
    {"id": "SlopP", "name": "Slop Port", "capacity_m3": 500},
    {"id": "SlopS", "name": "Slop Starboard", "capacity_m3": 500}
  ],
  "default_vef": 1.0000
}
```

### 3.2. Ullage Table (CSV per tank)
```csv
ullage_cm,volume_m3
0,1500.000
1,1498.750
2,1497.500
...
1500,0.000
```

### 3.3. Trim Correction Table (CSV per tank)
```csv
ullage_cm,trim_m_aft,correction_m3
100,-2.0,-5.5
100,-1.5,-4.2
100,-1.0,-2.8
100,0.0,0.0
100,1.0,2.8
...
```

---

## 4. Main Interface Layout

Based on the reference Excel spreadsheet, the main window has:

### 4.1. Header Section (Top)
| Field | Type | Description |
|-------|------|-------------|
| Loading Port | Input | Port name |
| Loading Terminal | Input | Terminal name |
| Voyage No | Input | Voyage number |
| Date | Input | Date of operation |
| V.E.F. | Input | Vessel Experience Factor (default 1.0000) |
| Draft AFT | Input | Aft draft reading (meters) |
| Draft FWD | Input | Forward draft reading (meters) |
| **Trim** | Calculated | `Draft AFT - Draft FWD` |

### 4.2. Tank Grid (Center) - Loading Side
Each row represents one tank with these columns:

| # | Column | Type | Description |
|---|--------|------|-------------|
| 1 | Tank No | ReadOnly | Tank ID (1P, 1S, 2P...) |
| 2 | Parcel | Input | Cargo parcel number |
| 3 | Grades (Products) | Input | Product type (K.BENZIN, MOTORIN, etc.) |
| 4 | Receiver | Input | Receiving company name |
| 5 | Tank No (Receiver) | Input | Receiver's tank number |
| 6 | Ullage | **Input (Blue)** | Ullage reading in cm - *auto-fills if % entered* |
| 7 | % Fill | **Input (Blue)** | Fill percentage - *auto-fills if Ullage entered* |
| 8 | Trim Corr | Calculated | Trim correction value |
| 9 | Corr | Calculated | Corrected volume |
| 10 | TOV | Calculated | Total Observed Volume |
| 11 | Temp | **Input (Blue)** | Cargo temperature (°C) |
| 12 | Thermal Corr | Calculated | Thermal correction factor |
| 13 | VAC Dens | **Input (Blue)** | Vacuum density |
| 14 | Air Dens | Calculated | Air density |
| 15 | VCF | Calculated | Volume Correction Factor |
| 16 | GSV | Calculated | Gross Standard Volume |
| 17 | MT (Air) | Calculated | Metric tons in air |
| 18 | M3 (VAC) | Calculated | Cubic meters in vacuum |
| 19 | B/L Figure | Input | Bill of Lading figure |
| 20 | Discrepancy | Calculated | Difference between calculated and B/L |

> [!IMPORTANT]
> **Dual Input Mode (Ullage ↔ % Fill)**
> - If user enters **Ullage**: System looks up volume from ullage table → calculates % Fill
> - If user enters **% Fill**: System calculates target volume (capacity × %) → reverse-interpolates ullage from table
> - Only ONE of these fields needs to be filled; the other auto-populates

> [!TIP]
> **Bulk Selection & Batch Input**
> - User can **select multiple cells** in the same column (Ctrl+Click or Shift+Click)
> - Typing a value applies it to **ALL selected cells** at once
> - Example: Select all Ullage cells → type "200" → all tanks get Ullage = 200 cm
> - Example: Select all % Fill cells → type "95" → all tanks set to 95% fill (Ullage auto-calculated per tank)

### 4.3. Summary Section (Bottom)
- **Total GSV**: Sum of all GSV values
- **Total MT**: Sum of all MT values
- **Present Port / Terminal**: Current location
- **Discrepancy (Loading)**: Ship vs Shore difference (%)
- **Discrepancy (Discharging)**: Ship vs Shore difference (%)

### 4.4. Footer
- Chief Officer name
- Master name
- Stowage Plan button

---

## 5. Calculation Logic

### 5.1. Ullage → Volume (TOV)
```
TOV = interpolate(ullage_table, ullage_input)
```
Linear interpolation if ullage_input falls between two table values.

### 5.2. Trim Correction
```
trim = draft_aft - draft_fwd
trim_correction = bilinear_interpolate(trim_table, ullage_input, trim)
corrected_volume = TOV + trim_correction
```

### 5.3. VCF (ASTM Table 54B)

The Volume Correction Factor corrects observed volume to standard temperature (15°C).

**Formula:**
```
VCF = e^(-α × ΔT × (1 + 0.8 × α × ΔT))
```

Where:
- `e` = Euler's number (2.71828...)
- `ΔT` = Observed Temperature (°C) - 15
- `α` = Coefficient of thermal expansion

**ALPHA Calculation:**
```
α = (K0 + K1 × DEN15) / DEN15²
```

**Coefficients based on Density at 15°C (kg/m³):**

| Density Range (kg/m³) | K0 | K1 | Notes |
|-----------------------|------------|---------|-------|
| ≤ 770 | 346.42278 | 0.43884 | Light products |
| 770 - 778 | Special | Special | Transition zone: α = -0.0033612 + 2680.32/DEN15² |
| 778 - 839 | 594.5418 | 0 | Mid-range products |
| ≥ 839 | 186.9696 | 0.48618 | Heavy products |

**Final Calculation:**
```
GSV = GOV × VCF
```

### 5.4. Density Conversion (Vacuum → Air)

Terminals typically provide **Vacuum Density**. To calculate weight in air, convert to **Air Density**:

```
Density_Air (g/cm³) = Density_Vacuum (g/cm³) - 0.0011
```

Or in kg/m³:
```
Density_Air (kg/m³) = Density_Vacuum (kg/m³) - 1.1
```

### 5.5. Mass Calculation
```
MT_in_air = GSV × Density_Air / 1000
MT_in_vacuum = GSV × Density_Vacuum / 1000
```

### 5.6. V.E.F. Application
```
final_gsv = GSV * VEF
```

### 5.7. Fill Percentage & Level Warnings
```
fill_percentage = (current_volume / tank_capacity) * 100
```

**Industry Rule**: A tank can NEVER be loaded above 98% capacity.

| Fill Level | Condition | Color | Alert Type |
|------------|-----------|-------|------------|
| **High High** | ≥ 98% | 🔴 RED | Critical - Loading must stop immediately |
| **High** | > 95% | 🟡 YELLOW | Warning - Approaching maximum safe level |
| **Normal** | 65% - 95% | ⚪ None | Safe operating range |
| **Low** | < 65% | 🟠 ORANGE | Slosh Effect Warning - Free surface effect |

> **Note**: Low level (Slosh Effect) warning indicates potential cargo movement during voyage which affects ship stability.

---

## 6. Features

### 6.1. First Run Setup
1. Enter ship name and tank count (6, 8, or 10 pairs)
2. **Enter tank capacities (m³)** for each tank
2. For each tank:
   - Upload Ullage Table (CSV)
   - Upload Trim Correction Table (CSV)
3. Set default V.E.F. value

### 6.2. Voyage Operations
1. New Voyage: Clear all inputs, enter voyage details
2. Save Voyage: Export current state to JSON/CSV
3. Load Voyage: Import previous voyage data
4. Generate Report: Create printable ullage report

### 6.3. Unit System Toggle
- **Metric**: M³, °C, kg/m³
- **Imperial**: Barrels, °F, API gravity

### 6.4. Export Options

| Format | Description | Use Case |
|--------|-------------|----------|
| **Excel (.xlsx)** | Full spreadsheet with formulas | Archive, further analysis |
| **PDF** | Formatted printable report | Official documentation, signing |
| **ASCII (aligned text)** | Plain text with aligned columns | Email, terminal printing, legacy systems |
| **JSON** | Stowage Plan data structure | Integration, backup, data exchange |

**JSON Stowage Plan Structure:**
```json
{
  "voyage": { "number": "30/2025", "port": "TUTUNCIFTLIK", "terminal": "TUPRAS", "date": "2025-12-14" },
  "vef": 0.99980,
  "drafts": { "aft": 8.00, "fwd": 8.00, "trim": 0.00 },
  "tanks": [
    { "id": "1P", "ullage": 1205, "volume": 2122.086, "gsv": 5342.535, "mt": 2126.786 },
    ...
  ],
  "totals": { "gsv": 10233.840, "mt": 10286.151 }
}
```

### 6.5. Localization (Multi-Language)

| Language | Code | Status |
|----------|------|--------|
| **English** | EN | Primary |
| **Turkish** | TR | Primary |

- Language selection available in **Settings** menu
- All UI labels, messages, and reports switch language
- Date/number formatting follows locale conventions

---

## 7. UI Color Coding

| Color | Meaning |
|-------|---------|
| **Light Blue / Cyan** | User input field |
| **White / Light Gray** | Calculated field (read-only) |
| **Yellow** | High Level Warning (> 95% fill) |
| **Orange** | Low Level Warning (< 65% fill) - Slosh Effect |
| **Red** | High High Level (≥ 98%) or Critical Error |
| **Dark Gray** | Header/Label |

---

## 8. File I/O

| Operation | Format | Description |
|-----------|--------|-------------|
| Ship Config | JSON | Tank definitions, capacities |
| Ullage Tables | CSV | Per-tank ullage-to-volume tables |
| Trim Tables | CSV | Per-tank trim correction tables |
| Voyage Data | JSON | Current voyage inputs and results |
| Reports | CSV/PDF | Exportable summary reports |

---

## 9. Error Handling

- **Invalid Ullage**: Value outside table range → Show warning
- **Missing Table**: Tank without ullage table → Disable row
- **Temperature Out of Range**: ASTM table limits → Show warning
- **Save Failure**: Disk full or permission error → Alert user

---

## 10. Future Enhancements

- [ ] Multi-voyage history tracking
- [ ] Cloud sync for fleet management
- [ ] Integration with ship's draft sensors
- [ ] API calculation via external ASTM service
