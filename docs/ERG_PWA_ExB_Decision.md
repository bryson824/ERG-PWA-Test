# ERG PWA vs ExB — Decision & Constraints

**Author:** esri-sme  
**Audience:** team-lead, ui-engineer, business-analyst  
**Design ref:** `docs/ERG_Offline_PWA_Data_Plan.md` §3, `docs/ERG_Handoff_Implementation.md`

---

## 1. Recommendation: Separate PWA shell (Option A)

**Use a separate PWA shell in this repo (e.g. `pwa/`) that loads the merged table and links to ExB. Do not rely on ExB as the PWA.**

| Option | Verdict | Reason |
|--------|--------|--------|
| **A — Separate shell** | **Recommended** | Full control over manifest, service worker, and caching of `air_monitoring_table.json`. Deploy to any static host (GitHub Pages, S3, etc.). ExB remains the full app on ArcGIS; PWA is the installable entry that works offline for the air sheet. |
| **B — ExB as PWA** | **Not recommended** | ArcGIS Experience Builder does not provide a built-in way to create a PWA with a custom manifest and service worker. ExB apps are hosted by ArcGIS; you cannot inject a custom SW to cache a separate JSON asset (the merged table) or guarantee installability with our desired shell (ERG link + air sheet first). Community ideas exist for “PWA from ExB” but there is no supported, out-of-the-box path. |

---

## 2. ExB / AGOL constraints (relevant to this decision)

- **ExB hosting:** ExB apps run under ArcGIS Online (or Enterprise). The app URL and assets are under Esri’s control. Custom service workers and app manifests are not part of the standard ExB deployment model.
- **Caching custom data:** Caching the merged `air_monitoring_table.json` for offline use requires a service worker (or similar) that we control. That implies an origin we control (the separate PWA shell), not the ExB-hosted app.
- **Link from PWA to ExB:** The PWA shell will include a dedicated link (e.g. “Open ERG Guide” / “Full ERG App”) that opens the primary ERG guide (ExB app). Opening in the same tab or new tab is a product/UX decision; technically both are straightforward from the shell.
- **Same data in ExB (optional):** The same merged table can be uploaded to AGOL as a hosted table or used in ExB via a layer/view if we want one source for both PWA and ExB. The build script output (`data_reference/out/air_monitoring_table.json`) can drive both.

---

## 3. What was implemented (esri-sme)

- **Decision documented** in this file.
- **Minimal PWA shell** under `pwa/`:
  - `manifest.json` — installable PWA (name, start_url, display standalone, theme/background colors, placeholder icons).
  - `sw.js` — service worker: cache-first for shell (HTML, JS, CSS, manifest) and for `air_monitoring_table.json`.
  - `index.html` — entry point: registers SW, fetches and renders the merged table (placeholder table UI), and a **dedicated spot for the primary ERG guide link** (placeholder for ui-engineer to style and place).
- **Placeholder data:** `pwa/air_monitoring_table.json` is a small placeholder so the shell runs before `build_data.py` exists. The real file will replace it when the merge script runs and its output is copied into `pwa/` (see plan §4).

---

## 4. What I need from the team

### (a) From ui-engineer

- **Frozen header row + frozen first column** for the air sheet. The current shell renders a simple scrollable table; this is **placeholder**. You own the layout and component implementation (e.g. sticky `<thead>` and first column, or a different approach).
- **ERG guide link:** Placement and styling of the “Primary ERG guide” CTA (design: dedicated, always-visible spot — e.g. shell header or sticky bar). The shell has a clear **placeholder** block for this link; replace with final design and copy.
- **Design pass:** Typography, spacing, contrast, and alignment with EPA R9 Air Monitoring Tables style. The shell is minimal on purpose so you can own the look and feel.

**Tagged in repo:** In `pwa/index.html`, comments mark `<!-- PLACEHOLDER: ui-engineer -->` for the ERG link block and the table container so you can replace them.

**Implementation note (ui-engineer):** Air sheet UI implemented with frozen header row and frozen first column. Column order and names are taken from the merged table JSON keys (first key = row identifier, frozen in the first column). **business-analyst** will lock the final column set and merge output shape; once locked, the PWA will render whatever keys the merge script outputs (no code change needed unless column order or “first column” semantics change).

### (b) From business-analyst

- **Final column set and merge output shape** for the air monitoring table. The PWA expects a JSON array of objects (one object per row; keys = column names). Example: `[{ "Target Compound": "...", "Instrument": "...", "PEL": "...", ... }, ...]`.
- **Confirm:** Column names and order that the merge script (`build_data.py`) will output, so the shell and any future ExB consumption stay in sync. Once locked, the script should write `air_monitoring_table.json` in that shape to `data_reference/out/` (and the file can be copied to `pwa/` for the PWA to serve).
- **Acceptance criteria** for “correct” table content (e.g. required fields, alignment with EPA R9 columns).

---

## 5. Build / deploy note

- **Merged table path:** Script output: `data_reference/out/air_monitoring_table.json`. For the PWA to serve it, copy that file to `pwa/air_monitoring_table.json` (e.g. as part of `build_data.py` or a separate deploy step). The service worker caches `air_monitoring_table.json` from the PWA origin.
- **Run the PWA locally:** Serve the `pwa/` folder over HTTP (e.g. `npx serve pwa` or any static server). The app will load and cache the table; with the placeholder JSON it runs without the merge script.
