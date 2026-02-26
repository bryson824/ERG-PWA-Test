# ERG PWA & Air Sheet — Implementation Handoff

**From:** team-lead  
**To:** esri-sme (lead), ui-engineer, business-analyst  
**Design reference:** `docs/ERG_Offline_PWA_Data_Plan.md` (especially §0 Design, §2–4)

---

## 1. Goal (reminder)

- **Source:** Excel file → script → merged air monitoring table (JSON).
- **Deliverable:** A PWA with (1) a **pretty, usable air sheet** (frozen header row + frozen first column), (2) a **dedicated spot for the primary ERG guide link**, (3) offline caching of the table.

---

## 2. Who leads and who to talk to

### esri-sme leads implementation first

- **You own:** Whether the PWA lives inside ExB or as a separate shell; how the merged table gets into the Esri/AGOL world if needed; ExB constraints (widgets, hosting, PWA capability); any ArcGIS/Esri-specific implementation.
- **You must coordinate with:**
  - **ui-engineer** — Air sheet UI: frozen header + frozen first column, layout, typography, spacing, and the dedicated ERG guide link placement. Do not finalize UI/UX without their input on look, feel, and consistency. If you implement the shell/table first, hand off to ui-engineer for design pass and component polish.
  - **business-analyst** — Data shape: column set for the merged table, header names, and any business rules (e.g. EPA R9 column alignment, which fields are required). Confirm merge spec and outputs with them before locking the build script or table schema. **Locked spec:** `docs/Air_Monitoring_Table_Schema.md`.

### ui-engineer

- **You own:** Air sheet layout (frozen header, frozen first column), visual design, ERG guide link placement and styling, and consistency with ERG patterns.
- **Coordinate with:** esri-sme for ExB/Esri constraints; business-analyst for column names and content requirements.

### business-analyst

- **You own:** Merge spec (which tables/columns), final column set for the air sheet, and acceptance criteria for “correct” table content.
- **Coordinate with:** esri-sme on how the merged table is consumed (PWA/ExB); ui-engineer on labeling and any content rules that affect layout.

---

## 3. Order of work (team-lead recommendation)

1. **esri-sme (first):**
   - Decide: separate PWA shell in repo vs ExB-as-PWA; document and share with team.
   - If separate shell: set up `pwa/` (or equivalent) with manifest, service worker, and minimal shell that can load a static JSON table and show a placeholder table + ERG link.
   - Confirm with business-analyst: merge output shape and column set.
   - **Then involve ui-engineer:** Hand off shell/table for frozen header/column implementation, styling, and ERG guide link placement.

2. **ui-engineer:**
   - Implement air sheet: frozen header row, frozen first column, pretty/usable layout.
   - Add and style the dedicated “Primary ERG guide” link per design (§0 in plan).
   - Align with esri-sme on any ExB/widget constraints; with business-analyst on labels/columns.

3. **business-analyst:**
   - Lock merge spec and column names; support build script (e.g. `build_data.py`) so output matches what PWA and ui-engineer expect.
   - Review table content and acceptance criteria once data flows end-to-end.

4. **Data/build script (can run in parallel with PWA shell):**
   - Excel → CSVs → merge → `air_monitoring_table.json` (see plan §2, §4). business-analyst + dev (ui-engineer or esri-sme) as needed for script and schema.

---

## 4. Design references

- **Air sheet & PWA design:** `docs/ERG_Offline_PWA_Data_Plan.md` — §0 Design (frozen header/column, ERG link, PWA shell).
- **Merge logic & table shape:** `docs/Air_Monitoring_Data_Model.md` — §3 (denormalized air monitoring table). **Locked schema (column set, merge spec, acceptance criteria):** `docs/Air_Monitoring_Table_Schema.md`.
- **File paths, commands, caching:** `docs/ERG_Offline_PWA_Data_Plan.md` — §2–5.
- **PWA vs ExB decision + coordination:** `docs/ERG_PWA_ExB_Decision.md` — esri-sme recommendation (separate PWA shell), ExB/AGOL constraints, and explicit asks for ui-engineer and business-analyst.

---

## 5. Success criteria (team-lead)

- PWA is installable and works offline for the air sheet.
- Air sheet has frozen header row and frozen first column; layout is pretty and usable.
- Primary ERG guide link has a dedicated, always-visible spot.
- One script (e.g. `python scripts/build_data.py`) regenerates the merged table from the Excel file for QA and ongoing updates.
- esri-sme, ui-engineer, and business-analyst have coordinated so data shape, ExB/shell decisions, and UI are aligned.
