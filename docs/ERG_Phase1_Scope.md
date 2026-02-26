# ERG Phase 1 — Scope and Data Reference

**Owner:** Team-lead (delegates to esri-sme, ui-engineer, business-analyst)  
**Last updated:** From team-lead synthesis; clarify with Bryson if anything is stale.

---

## 1. Platform and Surfaces

| Surface | Role | When |
|--------|------|------|
| **ExB (ArcGIS Experience Builder)** | Primary app: chemical reference lookup, search, SOP/QSG list (clickable links), print sensor + cross-sensitivity. | Online only. |
| **PWA (Progressive Web App)** | Shell that (1) links to ExB, (2) serves **offline air monitoring table** (merged/tidied from Excel). | Online: entry point to ExB. Offline: cached air monitoring table (+ optional PDFs later). |
| **Phone** | Day-one target; no tablets. ExB and PWA both phone-friendly. | Beta testers → ~30 users. |

- **ExB:** Prefer hosted; open to **Developer Edition** for custom widgets (e.g. PDF generation) if needed.
- **Data:** 9-table reference DB in AGOL used where it fits; **air monitoring table** for offline is a **merged, tidied derivative** of the Excel in `data_reference`, consumed by the PWA.

---

## 2. Phase 1 Must-Haves

- **Chemical reference lookup** (ExB, using AGOL/views as needed).
- **Offline air monitoring table** (PWA): one merged/tidied table derived from the Excel in `data_reference`, cached for offline.
- **SOP/QSG links in ExB:** List widget populated from **ERG_URLs** data; Power Automate exports CSV from SharePoint → that CSV (or an AGOL layer fed from it) drives the list widget so rows have **clickable links** (`file_url`).
- **Print in app:** Sensor info and cross-sensitivity printable (ExB or custom widget if required).
- **Searchable, fast, updateable** site (client’s top-level ask).

Out of scope for Phase 1: check-out/check-in, photo routing, inspection schedule (may return later).

---

## 3. Data Sources and Flows

### 3.1 SOP/QSG links (ExB list widget)

- **Source:** SharePoint; **Power Automate** exports to CSV.
- **File in repo:** `data_reference/ERG_URLs_1.csv`.
- **Columns:** `OBJECTID`, `device_type`, `document_type`, `version`, `category`, `file_url`.
- **ExB use:** List widget bound to a layer or table that has these columns so each row can show a clickable `file_url` (e.g. link to SharePoint PDF). Options: (1) CSV → AGOL hosted table/feature layer, updated when Power Automate runs; (2) or equivalent so ExB list can render links.

### 3.2 Air monitoring table (offline in PWA)

- **Source:** Merged and tidied version derived from **`data_reference/Air_Monitoring_Relationships-2.xlsx`** (workflow: merge/tidy → single table → PWA caches it for offline). The Excel is binary; scripts (e.g. Python/pandas or openpyxl) will read it; optionally export a sheet to CSV for structure review.
- **Reference for structure/content:** [EPA R9 Air Monitoring Tables](https://r9data.response.epa.gov/r9responseguide/MainPage/AirMonitoringTables.html) (old non-ExB version): Target Compound, Instrument, Detection Level, PID Lamp/CF, Intrinsically Safe, IP (eV), Conversion, PEL, REL, TLV, IDLH, PAC-1/2/3, Air Sampling Method, Media, Holding Time, Flow Rate, Sample Volume, etc.
- **PWA:** Pre-generate or sync this merged table and store in PWA (e.g. IndexedDB or static JSON) so it works offline.

### 3.3 Chemical reference (ExB)

- **Source:** AGOL 9-table reference DB (and/or view layers) for chemical lookup, device/sensor, cross-sensitivity.
- **ExB:** View layers recommended for list/filter/query; keep normalized tables for integrity and other consumers.

---

## 4. Constraints

- **AGOL:** Solo visibility for now (Bryson only); notebooks stay in AGOL (GitHub for editing, copy back); no new IT asks for Phase 1.
- **Client:** Expects ExB; open to PWA + ExB split as above. Biggest fix: very searchable, fast, updateable site.

---

## 5. Reference Links

- **Current air monitoring table (reference only):** https://r9data.response.epa.gov/r9responseguide/MainPage/AirMonitoringTables.html  
- **SOP/QSG list data (sample):** `data_reference/ERG_URLs_1.csv`

---

## 6. Next Steps (team-lead delegation)

- **esri-sme:** ExB view layers for chemical/reference; where ERG_URLs data lives in AGOL for list widget links; offline data shape for PWA; Developer Edition need for PDF.
- **ui-engineer:** Phone-first layout; search UX; list widget link UX; consistency between ExB and PWA.
- **business-analyst:** Beta success criteria; “updateable” definition for client.
