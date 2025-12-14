# TODO List - UllageMaster

## Phase 1: Documentation ✅
- [x] Create GEMINI.MD (Project Vision)
- [x] Create PRD.MD (Requirements)
- [x] Create TODO.MD (This file)
- [x] Define ASTM 54B VCF formula
- [x] Define VAC→AIR density conversion
- [x] Define tank level warnings (High High/High/Low)
- [x] Define export formats (Excel/PDF/ASCII/JSON)
- [x] Define localization (EN/TR)

---

## Phase 2: Project Setup ✅
- [x] Initialize Python virtual environment
- [x] Create `requirements.txt` (PyQt6, pandas, numpy, openpyxl, reportlab)
- [x] Create directory structure (src/core, models, ui, export, i18n, data)

---

## Phase 3: Core Engine ✅
- [x] `core/interpolation.py` - Linear, bilinear, reverse interpolation
- [x] `core/astm_54b.py` - VCF calculation with ASTM coefficients
- [x] `core/density.py` - VAC↔AIR conversion
- [x] `core/calculations.py` - Full tank calculation pipeline

---

## Phase 4: Data Models ✅
- [x] `models/ship.py` - Ship configuration with JSON persistence
- [x] `models/tank.py` - Tank with CSV table loading
- [x] `models/voyage.py` - Voyage data with readings

---

## Phase 5: User Interface ✅
- [x] `ui/main_window.py` - Main window with Excel-like grid
- [x] Header: Port, Terminal, Voyage, Date, V.E.F., Drafts
- [x] Tank Grid: 17 columns with dual input (Ullage ↔ %)
- [x] Footer: Totals (GSV, MT), Officer names
- [x] Menu bar: File, Export, Settings, Help
- [x] **Ship Setup Dialog** - Tank config, CSV upload, bulk upload
- [x] **Preferences Dialog** - Language (EN/TR), Units, Defaults
- [x] **Bulk cell selection** - Multi-select + keyboard input

---

## Phase 6: Export ✅
- [x] `export/json_export.py` - Stowage Plan JSON
- [x] `export/ascii_export.py` - Aligned text report
- [x] `export/excel_export.py` - Excel with formatting
- [x] `export/pdf_export.py` - PDF with tables

---

## Phase 7: Localization ✅
- [x] `i18n/en.json` - English translations
- [x] `i18n/tr.json` - Turkish translations
- [x] Language switching helper

---

## Phase 8: Testing & Verification
- [x] Application launches successfully
- [ ] Upload actual ship ullage tables
- [ ] End-to-end calculation test with real data
- [ ] Compare results with original Excel spreadsheet

---

## Phase 9: Packaging
- [ ] PyInstaller executable
- [ ] User documentation

---

## How to Run
```powershell
cd d:\ULLAGEMASTER
.\venv\Scripts\python src\main.py
```

---

## Features Summary
| Feature | Status |
|---------|--------|
| ASTM 54B VCF | ✅ |
| VAC↔AIR Density | ✅ |
| Interpolation (Linear/Bilinear) | ✅ |
| Dual Input (Ullage↔%) | ✅ |
| Bulk Cell Selection | ✅ |
| Tank Level Warnings | ✅ |
| Export (Excel/PDF/ASCII/JSON) | ✅ |
| Localization (EN/TR) | ✅ |
| Ship Config Dialog | ✅ |
| Preferences Dialog | ✅ |
