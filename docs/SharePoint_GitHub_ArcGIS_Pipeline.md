# SharePoint → GitHub → PWA & ArcGIS Pipeline

**Purpose:** How the GitHub repo and GitHub Pages fit into your existing flow where the Excel file lives on **SharePoint** and gets **uploaded to ArcGIS** to populate the ExB app. How updates to that sheet show up in the **PWA** and the **air monitoring table**.

---

## 1. Current flows (as understood)

| Step | What happens today |
|------|---------------------|
| **Source of truth** | Excel workbook (e.g. Air_Monitoring_Relationships-2.xlsx) lives on **SharePoint**. |
| **ArcGIS / ExB** | That Excel (or data from it) is **uploaded to ArcGIS** (AGOL) and populates the **Experience Builder (ExB)** app — e.g. 9-table reference layers or views. |
| **This repo** | Contains the **build script** (`scripts/build_data.py`) and the **PWA** (`pwa/`). The script reads Excel (or CSVs exported from it), merges to one table, and writes `pwa/air_monitoring_table.json`. The PWA serves that JSON and caches it for offline. |
| **GitHub Pages** | The workflow `.github/workflows/deploy-pages.yml` deploys the **existing** `pwa/` folder to GitHub Pages on push to `main`. It does **not** run the build script; it only publishes whatever is already in `pwa/` (including whatever `air_monitoring_table.json` was last committed). |

So today:

- **ExB** gets its data from **ArcGIS**, which is fed from your **SharePoint Excel** (via whatever upload process you use).
- **PWA** gets its data from **`pwa/air_monitoring_table.json`** in this repo. That file only changes when someone runs `build_data.py` (with the Excel or CSVs) and commits the new JSON.

There is no automatic link between “edit the sheet on SharePoint” and “PWA or repo updates.” Below are ways to add GitHub into the pipeline so updates to the sheet can show up in the PWA (and optionally keep one source for both PWA and ExB).

---

## 2. Where GitHub fits

The **GitHub repo** is the place where:

1. The **merge logic** lives (`scripts/build_data.py`).
2. The **PWA** is built and deployed from (GitHub Pages serves the `pwa/` folder).

So the pipeline is:

- **SharePoint** = source of truth for the Excel.
- **This repo** = where the Excel (or a copy) is turned into `air_monitoring_table.json` and where the PWA is deployed.
- **ArcGIS** = still fed from SharePoint (or from this repo; see options below).

Updates to the sheet can reach the PWA in one of these ways.

---

## 3. Option A — Manual refresh (simplest)

1. When the Excel on **SharePoint** is updated, someone **downloads** it.
2. Run the build **locally** with that file:
   ```bash
   python scripts/build_data.py path/to/downloaded/Air_Monitoring_Relationships-2.xlsx
   ```
3. **Commit** the updated `pwa/air_monitoring_table.json` (and optionally `data_reference/out/air_monitoring_table.json` and the CSVs in `data_reference/` if you keep them in the repo).
4. **Push** to `main` → GitHub Actions deploys the PWA to GitHub Pages with the new table.

- **PWA:** Users get the new table after the next load (and cache refresh).
- **ArcGIS/ExB:** Unchanged; you keep uploading the Excel (or AGOL layers) from SharePoint as you do today.

---

## 4. Option B — Excel in repo + build on deploy

Keep a **copy** of the Excel in the repo (e.g. `data_reference/Air_Monitoring_Relationships-2.xlsx`), updated whenever SharePoint is updated (manual or via Power Automate / sync).

1. **Extend the GitHub Actions workflow** so that on every push to `main` it:
   - Checks out the repo (so the Excel and scripts are there).
   - Installs Python + dependencies (`pandas`, `openpyxl`).
   - Runs `python scripts/build_data.py` (uses the Excel in `data_reference/` by default).
   - Deploys the **resulting** `pwa/` folder (which now has the new `air_monitoring_table.json`) to GitHub Pages.

Then:

- **Updates to the sheet** = update the Excel in the repo (e.g. re-export from SharePoint and commit) and push. The workflow rebuilds the table and deploys; the PWA and underlying air table in the repo stay in sync.
- **ArcGIS/ExB** can still be updated separately from SharePoint, or you could add a step (e.g. script or manual) to upload `data_reference/out/air_monitoring_table.json` (or a CSV) to AGOL so ExB uses the same merged table.

---

## 5. Option C — Automated: SharePoint → repo or CI

Use **Power Automate** (or similar) to:

1. When the **SharePoint** workbook is updated, **download** the new Excel and either:
   - **C1:** Push it into the repo (e.g. commit to a branch and open a PR, or commit to `main`), or  
   - **C2:** Upload it to a place that **GitHub Actions** can fetch (e.g. artifact store, secure URL).

2. **Trigger** the pipeline:
   - **C1:** Push triggers the workflow; if you use Option B (build in CI), the new Excel is already in the repo and the same job builds and deploys.
   - **C2:** A scheduled or manual workflow fetches the Excel, runs `build_data.py`, then deploys the `pwa/` folder (and optionally commits the new JSON back to the repo).

Then **updates to the sheet on SharePoint** flow: SharePoint → (Power Automate) → repo or CI → build → new `air_monitoring_table.json` → PWA on GitHub Pages. The PWA and the air table in the repo stay in sync with the sheet.

---

## 6. Keeping ExB and PWA on the same data (optional)

Today, ExB is populated from **ArcGIS** (fed by your SharePoint Excel). The PWA is populated from **`air_monitoring_table.json`** produced by this repo.

To have **one source** for both:

- **Option 1:** Keep two paths: (1) SharePoint → ArcGIS → ExB (as now). (2) SharePoint → this repo (Option A/B/C) → `build_data.py` → `air_monitoring_table.json` → PWA. Same Excel, two distribution paths.
- **Option 2:** Use the **merge output** for both: run `build_data.py` (from Excel in repo or from SharePoint), then (a) deploy PWA from repo (GitHub Pages), and (b) **upload** `data_reference/out/air_monitoring_table.json` (or a CSV) to **AGOL** as a hosted table/layer and point ExB at it. Then both PWA and ExB read from the same denormalized table; you only need to refresh that table when the sheet changes (manually or via Option B/C).

---

## 7. Summary

| Question | Answer |
|----------|--------|
| How does **GitHub** fit in? | The repo holds the build script and the PWA. GitHub Pages deploys the PWA. So “the pipeline” can be: SharePoint Excel → (get into repo or run in CI) → `build_data.py` → `air_monitoring_table.json` in `pwa/` → deploy → PWA shows the new table. |
| How do **updates to the sheet** show up in the **PWA**? | By running the build (locally or in CI) with the updated Excel and then deploying. Option A = manual run + commit + push. Option B = Excel in repo + build step in the deploy workflow. Option C = automate getting the Excel from SharePoint into the repo or into CI, then same as B. |
| How do updates show up in the **underlying air table**? | The “underlying” table is `pwa/air_monitoring_table.json` (and `data_reference/out/air_monitoring_table.json`). Both are **outputs** of `build_data.py`. So whenever you run the script with the latest Excel, the air table is updated; if you commit and push (and deploy from that), the PWA serves that updated table. |
| What about **ArcGIS/ExB**? | ExB continues to use whatever you upload to ArcGIS from SharePoint. If you want ExB to use the same merged table as the PWA, add a step to upload the build script output to AGOL and use that in ExB (Option 2 in §6). |

If you tell me which option you prefer (A: manual, B: Excel in repo + build on deploy, or C: automate from SharePoint), I can outline the exact workflow steps and the exact changes to `.github/workflows/deploy-pages.yml` (e.g. adding the Python build step for Option B).
