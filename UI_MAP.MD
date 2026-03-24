# UllageMaster — UI Component Map

Use the **ID codes** to reference specific areas when reporting bugs.

---

## Main Window

| ID | Element | Description |
|---|---|---|
| `MW-MENU` | Menu Bar | Top menu strip |
| `MW-TABS` | Tab Bar | 5 tabs across the top |
| `MW-STATUS` | Status Bar | Bottom status strip |

### Menu Bar (`MW-MENU`)

| ID | Menu | Sub-items |
|---|---|---|
| `M-FILE` | File | New Voyage, Open Voyage, Save, Save As, Exit |
| `M-FILE-SETTINGS` | File → Settings | Ship Config, Import/Delete Config, Backup/Restore, Report Headers, Company Logo, Language (EN/TR) |
| `M-STOWAGE` | Stowage Plan | Empty All Tanks, ➡️ Transfer to Ullage |
| `M-ULLAGE` | Ullage Table | Edit Parcels, Export → Template Report (XLSM), ⬅️ Transfer to Stowage |
| `M-HELP` | Help | User Manual (F1), About |

---

## Tab 1: 📂 Voyages (`T1`)

| ID | Component | Description |
|---|---|---|
| `T1-EXPLORER` | Voyage Explorer | File browser for saved voyages |
| `T1-PREVIEW` | Voyage Preview | Preview pane for selected voyage |

## Tab 2: 📋 Stowage Plan (`T2`)

| ID | Component | Description |
|---|---|---|
| `T2-LEGEND` | Cargo Legend | Draggable cargo cards (color-coded) |
| `T2-COLORIZE` | Colorize Button | Hold to group by receiver (purple button) |
| `T2-FILL97` | Set 97.7% Button | Fill all loaded tanks to 97.7% (orange button) |
| `T2-SCHEMATIC` | Ship Schematic | Visual tank grid (Port/Starboard layout) |
| `T2-INPUT` | Charterer Order (left panel) | Cargo input table (quantities, receivers) |
| `T2-PLAN` | Loading Plan (right panel) | Plan viewer showing assignments |

## Tab 3: 📊 Ullage Calculation (`T3`)

| ID | Component | Description |
|---|---|---|
| `T3-HEADER` | Header Section | Port, Terminal, Voyage No, Date, V.E.F., Draft AFT/FWD, Trim |
| `T3-GRID` | Tank Grid | Main calculation table (20 columns per tank row) |
| `T3-GRID-COL-TANK` | → Tank column | Tank ID (read-only) |
| `T3-GRID-COL-PARCEL` | → Parcel column | Dropdown parcel selector (input) |
| `T3-GRID-COL-GRADE` | → Grade column | Auto from parcel |
| `T3-GRID-COL-RECEIVER` | → Receiver column | Auto from parcel |
| `T3-GRID-COL-TANKNO` | → Tank No column | Receiver's tank number |
| `T3-GRID-COL-ULLAGE` | → Ullage column | User input (blue) |
| `T3-GRID-COL-TEMP` | → Temp column | User input (blue) |
| `T3-GRID-COL-FILL` | → % Fill column | User input, bidirectional with Ullage |
| `T3-GRID-COL-TRIM` | → Trim Corr column | Calculated |
| `T3-GRID-COL-CORRULL` | → Corr Ullage column | Calculated |
| `T3-GRID-COL-TOV` | → TOV column | Calculated |
| `T3-GRID-COL-THERM` | → Therm.Corr column | Calculated |
| `T3-GRID-COL-GOV` | → GOV column | Calculated |
| `T3-GRID-COL-VCF` | → VCF column | Calculated |
| `T3-GRID-COL-GSV` | → GSV column | Calculated |
| `T3-GRID-COL-VACDENS` | → VAC Dens column | Auto from parcel |
| `T3-GRID-COL-MTVAC` | → MT(VAC) column | Calculated |
| `T3-GRID-COL-AIRDENS` | → Air Dens column | Calculated |
| `T3-GRID-COL-MTAIR` | → MT(Air) column | Calculated |
| `T3-TOTALS` | Totals Row | Sum of GSV, MT at bottom |

## Tab 4: 📑 Report Functions (`T4`)

| ID | Component | Description |
|---|---|---|
| `T4-META` | Report Metadata | Actual Port, Terminal, MMC No, Report Date, Remarks |
| `T4-PARCELS` | Parcel Checklist | Select which parcels to include |
| `T4-DRAFTS` | Draft Display | Synced FWD/AFT drafts |
| `T4-GENERATE` | Generate Buttons | Total report, selected parcels, stowage plan |

## Tab 5: ⚖️ Discrepancy / Protests (`T5`)

| ID | Component | Description |
|---|---|---|
| `T5-DISC` | Discrepancy Table | Ship vs Shore figure comparison |
| `T5-PROTEST` | Protest Letter | Protest letter generation |

---

## Dialogs (Pop-ups)

| ID | Dialog | Triggered From |
|---|---|---|
| `D-SHIP` | Ship Setup Wizard | File → Settings → Ship Config |
| `D-PARCEL` | Parcel Setup | Ullage Table → Edit Parcels |
| `D-CONFIG` | Config Editor | File → Settings |
| `D-HEADER` | Report Header Setup | File → Settings → Report Headers |
| `D-LOGO` | Company Logo Setup | File → Settings → Company Logo |
| `D-BACKUP` | Backup Dialog | File → Settings → Backup |
| `D-RESTORE` | Restore Dialog | File → Settings → Restore |
| `D-MANUAL` | User Manual | Help → User Manual (F1) |
| `D-ABOUT` | About Dialog | Help → About |
