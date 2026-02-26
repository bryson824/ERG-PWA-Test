# ERG Offline Table, PWA, and Excel Data Script — Plan

**Purpose:** Get (1) offline table merge and (2) PWA done; keep (3) Excel → data script trivial to re-run.  
**Status:** Plan + design approved; implementation delegated to specialists (see `docs/ERG_Handoff_Implementation.md`).

---

## 0. Design: Air Sheet & PWA (approved)

**Goal:** Take the Excel file → build a PWA that presents the **air monitoring table** in a pretty, usable way, with a clear link to the primary ERG guide.

### Air sheet (main content)

| Requirement | Spec |
|-------------|------|
| **Source** | Pre-merged table from Excel (Excel → CSVs → merge → `air_monitoring_table.json`). |
| **Layout** | Single scrollable table with **frozen header row** and **frozen first column** so users always see column titles and the row identifier (e.g. Target Compound or chemical name) while scrolling. |
| **Look & feel** | Pretty and usable: clear typography, readable row/column spacing, accessible contrast. Align with EPA R9 Air Monitoring Tables style where it makes sense (Target Compound, Instrument, Detection Level, PEL, REL, TLV, IDLH, PAC, Air Sampling Method, etc.). |
| **Offline** | Table data cached by PWA (service worker) so the air sheet works offline. |

### Primary ERG guide link

| Requirement | Spec |
|-------------|------|
| **Placement** | A dedicated, prominent spot for a **link to the primary ERG guide** (e.g. EPA R9 ERG or the main ExB app). Not buried in the table; always visible (e.g. in the shell header or a sticky bar above/below the table). |
| **Behavior** | Single clear CTA (e.g. “Open ERG Guide” or “Full ERG App”) that opens the primary guide in the same tab or new tab per product decision. |

### PWA shell

| Requirement | Spec |
|-------------|------|
| **Entry point** | Installable PWA (manifest + service worker). Shell includes: (1) ERG guide link, (2) air sheet (frozen header + frozen first column), (3) optional link/embed to full ExB app. |
| **Caching** | App shell + `air_monitoring_table.json` cached for offline; strategy per §3 of this doc. |

### Summary

- **Excel** → script → merged table → PWA loads and caches it.
- **Air sheet:** frozen header + frozen first column; pretty, usable.
- **ERG guide link:** dedicated spot, always visible.
- Implementation order and agent handoff: **`docs/ERG_Handoff_Implementation.md`**.

---

## 1. What the codebase has today

| Area | Current state |
|------|----------------|
| **Offline table / merge** | Not implemented. Docs describe the merge: `docs/Air_Monitoring_Data_Model.md` §3 (Sensor_Chemical → Sensors → Device_Sensor → Devices + Chemicals; optional Chemical_Method → Sampling_Methods). |
| **PWA** | None. No `manifest.json`, no service worker, no PWA config in repo. ExB app is hosted separately (ArcGIS); this repo is data + scripts + docs. |
| **Excel → data** | One script: `scripts/export_xlsx_sheets_to_csv.py`. Reads `data_reference/Air_Monitoring_Relationships-2.xlsx`, writes one CSV per sheet into `data_reference/` with naming `{workbook_base}_{sheet_name}.csv`. Requires `openpyxl`. No merge step. |
| **Data reference** | `data_reference/`: one Excel file (`Air_Monitoring_Relationships-2.xlsx`), ~14 CSVs (sheet exports from that workbook), plus `ERG_URLs_1.csv` (separate source for SOP/QSG links). |

CSV structure: first row is often a title; second row is the header (e.g. `cas_number (PK)`, `chemical_id (FK)`). Join keys: **chemical_id** in junction tables = **cas_number** in Chemicals; **sensor_id** / **device_id** as in the data model.

---

## 2. Offline table merge — concrete plan

### What to merge

- **Inputs:** The same tables produced from the Excel (after “Excel → CSV” step): Chemicals, Sensors, Devices, Device_Sensor, Sensor_Chemical; optionally Chemical_Method, Sampling_Methods; optionally Sensor_CrossSens (as separate artifact or extra columns).
- **Output:** One **denormalized table** (EPA-style): one row per (chemical, device, sensor) with columns such as: Target Compound, Instrument (device + sensor), Detection Level, PID Lamp/CF, PEL, REL, TLV, IDLH, PAC-1/2/3, Air Sampling Method, etc. Exact column set to align with ExB/ERG and [EPA R9 Air Monitoring Tables](https://r9data.response.epa.gov/r9responseguide/MainPage/AirMonitoringTables.html).

### Where it runs

- **Build-time / script-time** (recommended): Run as part of the “easy Excel script” (see §4). Script: Excel → CSVs → **merge** → output one file (e.g. `air_monitoring_table.json` and/or `air_monitoring_table.csv`) into a known folder (e.g. `data_reference/out/` or `data_reference/`). No runtime merge in the browser.
- **Consumers:**  
  - PWA shell: loads this pre-merged file and caches it (e.g. IndexedDB or Cache API) for offline.  
  - Optionally: same file can be used for AGOL/ExB (e.g. upload to hosted table or view) so ExB and PWA stay in sync.

### How it plugs into ExB/ERG

- **ExB:** Can keep using AGOL 9-table layers/views for full chemical reference. The merged table is primarily for the **PWA offline** experience. If you want one source for both, the script’s output can be uploaded to AGOL as a hosted table that ExB can also use.
- **PWA:** Shell app (see §3) fetches the pre-merged file from its own origin (or a CDN) and caches it; when offline, the app reads from cache and still shows the air monitoring table.

### Suggested implementation owner

- **Merge logic:** business-analyst or ui-engineer (data shape, column names); implementation can be Python (pandas) in repo, or delegated to a small script maintained alongside the Excel export.

---

## 3. PWA — concrete plan

### What to add

| Piece | Purpose |
|-------|--------|
| **Web App Manifest** (`manifest.json`) | Name, short_name, start_url, display (standalone), icons, theme_color, background_color. Makes the app installable and defines shell behavior. |
| **Service worker** | Offline and caching: (1) cache the shell (HTML/JS/CSS), (2) cache the pre-merged air monitoring table (e.g. `air_monitoring_table.json`), (3) optional: cache strategy for ExB iframe (e.g. network-first or cache-only for critical assets). |
| **Shell app** | Minimal HTML/JS: entry point that (1) links to ExB (e.g. “Open full app” or iframe), (2) loads and displays the offline air monitoring table (from cache when offline), (3) registers the service worker. |

### Where it fits in the project

- **Option A (recommended for this repo):** Add a **PWA shell** inside this repo (e.g. `pwa/` or `shell/`): static site with `index.html`, `manifest.json`, `sw.js` (or Workbox), and the cached merged table. Build step: run Excel script so `air_monitoring_table.json` is in a known path; PWA serves it and SW caches it. Deploy this shell to any static host (e.g. GitHub Pages, S3, or same host as ExB). ExB remains the “full” app (hosted on ArcGIS); the PWA is the installable entry that works offline for the table.
- **Option B:** If ExB is ever published as a PWA by ArcGIS (Esri), then manifest/SW might live in ExB’s build; this repo would still produce the **data** (merged table) that the ExB app could cache. Clarify with esri-sme whether ExB can serve a custom manifest and SW.

### Caching strategy (for Option A)

- **App shell:** Cache-first for `index.html`, main JS/CSS, `manifest.json`. Versioned so updates invalidate old cache.
- **Merged table:** Cache-first for `air_monitoring_table.json` (or whatever path). Updated when you re-run the Excel script and redeploy.
- **ExB (if iframed):** Network-first or bypass (open in same tab); avoid caching the entire ExB app unless Esri supports it.

### Suggested implementation owner

- **PWA shell + manifest + SW:** ui-engineer. **ExB hosting / PWA capability:** esri-sme (whether ExB can be “the” PWA or we need a separate shell).

---

## 4. Easy-to-run Excel script — concrete plan

### Goals

- **One obvious command** (or double-click) to re-run.
- **Idempotent:** safe to run repeatedly; overwrites outputs in a known place.
- **Clear inputs/outputs:** document where the Excel file lives and what gets overwritten.
- **Supports frequent updates:** no one-off steps; same flow for QA (next couple of weeks) and ongoing updates.

### Inputs

- **Primary input:** Excel file. Default path: `data_reference/Air_Monitoring_Relationships-2.xlsx`.
- **Override:** Env var (e.g. `ERG_XLSX_PATH`) or CLI arg (e.g. `python scripts/build_data.py path/to/file.xlsx`). Document in README or script docstring.

### Pipeline (single script or two steps)

1. **Excel → CSVs** (existing behavior): Read workbook; write one CSV per sheet into `data_reference/` with naming `{workbook_base}_{sheet_name}.csv`. (Reuse or call `scripts/export_xlsx_sheets_to_csv.py`.)
2. **Merge:** Read the relevant CSVs (Chemicals, Sensors, Devices, Device_Sensor, Sensor_Chemical; optional: Chemical_Method, Sampling_Methods, Sensor_CrossSens), normalize headers (strip “(PK)”/“(FK)” if needed), perform joins per `Air_Monitoring_Data_Model.md` §3, write one denormalized table.
3. **Output:** Write merged table to a fixed path, e.g.:
   - `data_reference/out/air_monitoring_table.json` (and/or `.csv`).
   - Optionally: same file copied to `pwa/public/air_monitoring_table.json` if PWA lives in this repo, so a simple build copies the artifact where the PWA serves it.

### One command / trivial re-run

- **Option 1:** Single entry script, e.g. `scripts/build_data.py` (or `scripts/run_build_data.sh` that activates venv and runs the script). Command:  
  `python scripts/build_data.py`  
  or, with env:  
  `ERG_XLSX_PATH=data_reference/MyUpdated.xlsx python scripts/build_data.py`
- **Option 2:** npm script if you add a minimal `package.json` at repo root:  
  `npm run build-data` → runs the Python script (e.g. via `node -e "require('child_process').execSync('python scripts/build_data.py')"` or a small `scripts/build-data.js` that spawns it). Easiest for non-devs: “run `npm run build-data`.”
- **Option 3:** Double-click: a small `.command` (macOS) or `.bat` (Windows) in repo root that runs the one command; document “put your Excel file in `data_reference/` as `Air_Monitoring_Relationships-2.xlsx` (or set path) and double-click `BuildData.command`.”

### What gets overwritten

- **By Excel → CSV:** All `data_reference/Air_Monitoring_Relationships-2_*.csv` (and similarly for another workbook if you use a different name). Document: “Do not edit these CSVs by hand; they are overwritten by the script.”
- **By merge:** `data_reference/out/air_monitoring_table.json` (and `.csv` if produced). If you copy to `pwa/public/`, that copy is overwritten too.

### Dependencies

- **Excel → CSV:** `openpyxl` (already required by existing script).
- **Merge:** Prefer `pandas` for joins; otherwise pure Python + csv. Add `requirements.txt` at repo root, e.g. `openpyxl`, `pandas`, and document: `pip install -r requirements.txt` (or use existing `.venv`).

### Documentation (for QA and ongoing use)

- **README section or `docs/Data_Build_README.md`:**  
  - “Place the Excel file at `data_reference/Air_Monitoring_Relationships-2.xlsx` (or set `ERG_XLSX_PATH` / pass path as argument).”  
  - “Run: `python scripts/build_data.py` (or `npm run build-data`).”  
  - “Outputs: CSVs in `data_reference/`, merged table in `data_reference/out/air_monitoring_table.json`. These are overwritten each run.”

### Suggested implementation owner

- **Unified script (export + merge):** business-analyst (merge spec, column names) + ui-engineer or general dev (script and CLI). **Optional npm/double-click wrapper:** ui-engineer.

---

## 5. File paths and commands summary

| Item | Path / command |
|------|-----------------|
| Excel source (default) | `data_reference/Air_Monitoring_Relationships-2.xlsx` |
| Existing export script | `scripts/export_xlsx_sheets_to_csv.py` |
| Proposed unified script | `scripts/build_data.py` (Excel → CSV → merge → write merged table) |
| Proposed output (merged table) | `data_reference/out/air_monitoring_table.json` (and optionally `.csv`) |
| Proposed PWA shell (if in repo) | `pwa/` or `shell/` (e.g. `pwa/index.html`, `pwa/manifest.json`, `pwa/sw.js`) |
| Run command (example) | `python scripts/build_data.py` or `npm run build-data` |
| Override Excel path | `ERG_XLSX_PATH=path/to/file.xlsx python scripts/build_data.py` or `python scripts/build_data.py path/to/file.xlsx` |
| Dependencies | `requirements.txt`: `openpyxl`, `pandas` |

---

## 6. Order of work (for delegation)

1. **Easy Excel script (with merge):** Add `scripts/build_data.py` (and optionally `requirements.txt`, npm script, or `.command`), implement export step (reuse existing logic) + merge step; document inputs/outputs and one-command run. *Optional: one minimal runnable script stub to demonstrate the flow.*  
2. **Offline table consumption:** PWA shell (or ExB) loads `air_monitoring_table.json` and caches it; when offline, read from cache. Depends on (1) for the artifact.  
3. **PWA:** Add manifest, service worker, and shell UI in `pwa/` (or equivalent); configure caching for shell + merged table; document deploy and install.

---

## 7. Risks / follow-up

- **CSV header parsing:** Some CSVs have a title row then header row; merge script must skip or detect title row and use the real header (e.g. strip `(PK)`/`(FK)` for column names if needed for consistency).  
- **ExB vs PWA:** If the “app” is only ExB and there is no separate static host, the PWA shell needs a home (e.g. GitHub Pages or a small static server). esri-sme can confirm whether ExB can act as the PWA entry and how to pass the cached table into it.  
- **ERG_URLs_1.csv:** Separate from the Excel; produced by Power Automate. No change to the Excel script; keep as-is for ExB list widget.
