# ERG PWA — Update & Deployment Instructions

This document explains how to update the app, how the Excel data ties in, how to push changes to GitHub (and GitHub Pages), and how the system was built so a maintainer can work with it confidently.

---

## Table of contents

1. [Quick reference: pushing updates to GitHub](#1-quick-reference-pushing-updates-to-github)
1a. [Operator quickstart: local commit, GitHub auth, push, and cache refresh](#1a-operator-quickstart-local-commit-github-auth-push-and-cache-refresh)
2. [How the app works](#2-how-the-app-works)
3. [Editing copy (splash, hints, placeholders)](#3-editing-copy-splash-hints-placeholders)
4. [How the Excel ties in and gets updated](#4-how-the-excel-ties-in-and-gets-updated)
5. [Deployment: GitHub and GitHub Pages](#5-deployment-github-and-github-pages)
6. [How it was built (architecture)](#6-how-it-was-built-architecture)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick reference: pushing updates to GitHub

**To publish app or data changes so the live PWA updates:**

### Fast path (copy/paste) — most common update flow

Use this exact sequence when you changed text/UI and want it live.

```bash
# 1) Go to repo
cd "/Users/bryson/Documents/Cursor Testing/Full ERG App Rebuild v1"

# 2) Check what changed
git status

# 3) Stage files you want in this commit (example file shown)
git add "pwa/index.html"

# 4) Commit locally (this saves only on your computer)
git commit -m "Update home page text"

# 5) Push to GitHub (this makes it online and triggers deploy)
git push origin main
```

After push:
1. Open GitHub -> **Actions**.
2. Wait for **Deploy to GitHub Pages** to succeed.
3. Open the site URL and hard refresh once.

If push fails on a new computer, run this once:

```bash
gh auth login
gh auth status
```

If users still see old content, bump `CACHE_VERSION` in `pwa/sw.js`, then commit and push again.

1. **Make your changes** in this repo (code, content, or run the build script with new Excel — see §4).
2. **Commit** everything you want to go live:
   ```bash
   git add -A
   git status   # double-check what’s staged
   git commit -m "Brief description of the update"
   ```
3. **Push to `main`**:
   ```bash
   git push origin main
   ```
4. **GitHub Actions** runs automatically on push to `main` and deploys the **`pwa/`** folder to GitHub Pages. No extra step needed.
5. **Live site** (once Pages is configured): e.g. `https://<org>.github.io/<repo>/` — users get the new version on next load (and cache refresh).

**If you only changed data (e.g. updated `pwa/air_monitoring_table.json`):** Same flow — commit and push. The workflow does *not* run the Python build; it only uploads whatever is in `pwa/` at push time. So either run the build locally first (see §4) and commit the new JSON, or use a CI build step (see `docs/SharePoint_GitHub_ArcGIS_Pipeline.md` Option B).

## 1a. Operator quickstart: local commit, GitHub auth, push, and cache refresh

Use this when you just changed text/UI/data and want to get it live safely.

### A) Commit locally (save snapshot on your computer)

1. Make sure you are in the repo root.
   ```bash
   cd "/path/to/Full ERG App Rebuild v1"
   ```
2. See what changed:
   ```bash
   git status
   ```
3. Stage only what you want in this commit (example: home page text):
   ```bash
   git add "pwa/index.html"
   ```
4. Verify staged vs unstaged:
   ```bash
   git status
   ```
5. Commit locally:
   ```bash
   git commit -m "Update home page text"
   ```
6. Confirm commit exists locally:
   ```bash
   git log --oneline -3
   ```

### B) First-time setup on a new computer (GitHub authentication)

If `git push` fails with an auth prompt/error, authenticate once on that machine.

```bash
gh auth login
gh auth status
```

Notes:
- This repo uses an HTTPS remote (`https://github.com/...`).
- If `gh` is not installed, install it (macOS/Homebrew):
  ```bash
  brew install gh
  ```

### C) Push to GitHub (publish your local commits)

```bash
git push origin main
```

Then verify:
1. GitHub repo -> **Actions** tab.
2. Confirm **Deploy to GitHub Pages** runs successfully.
3. Open the Pages URL and hard refresh once.

### D) Force users to get latest PWA assets (cache refresh)

If users still see stale UI/data due to service worker cache, bump cache version in `pwa/sw.js`:

```js
const CACHE_VERSION = 'erg-pwa-v4';
```

Change `v4` -> `v5` (or next value), then commit and push.

Why this works:
- `install` pre-caches shell + table JSON files.
- `activate` deletes old `erg-pwa-*` caches.
- New version name forces clients onto fresh caches after update.

### E) Data-specific reminder (Excel is source of truth)

For table data updates, run the build before committing:

```bash
python scripts/build_data.py
```

This rebuilds from the Excel/CSV pipeline and updates:
- `data_reference/out/air_monitoring_table.json`
- `pwa/air_monitoring_table.json` (the deployed file)

---

## 2. How the app works

### What the PWA is

- **Installable web app** (Progressive Web App) that works offline for the air monitoring table and related tools.
- **Separate from the main ERG Experience Builder (ExB)** app on ArcGIS. The PWA is a lightweight shell that links to the full ERG guide/ExB and provides:
  - **Home/splash** (`index.html`) — nav to Air Monitoring Table, ExB link, HASP/PDF tool.
  - **Air Monitoring Table** (`table.html`) — full chemical–device–sensor reference with frozen header/first column, filters, and offline caching.
  - **HASP / Loadout PDF tool** (`hasp.html`) — build field-ready PDFs by chemical(s) or instrument(s).

### Data flow (runtime)

- **Shell (HTML/CSS/JS):** Served from the `pwa/` folder. The **service worker** (`pwa/sw.js`) caches the shell (index, table, hasp, manifest) so these pages work offline.
- **Table data:** The table page loads `pwa/air_monitoring_table.json` (and optionally `sensor_part_numbers.json`, `sensor_cross_sens.json`). The service worker caches these JSON files so the table works offline after first load. Data is **pre-cached on install** so the table is available even if the user never opened it while online.
- **ERG / ExB link:** Points to the primary ERG guide (e.g. EPA R9); configurable in the HTML.

### Caching (service worker)

- **Cache version** is set in `pwa/sw.js` (e.g. `CACHE_VERSION = 'erg-pwa-v4'`). Bump this when you want to force clients to drop old caches and fetch fresh shell/data.
- **Shell:** Cache-first for `index.html`, `table.html`, `hasp.html`, `manifest.json`, and the app root.
- **Table data:** Cache-first for `air_monitoring_table.json`, `sensor_part_numbers.json`, `sensor_cross_sens.json`; background network fetch updates the cache when online.

---

## 3. Editing copy (splash, hints, placeholders)

Misc. text—splash page heading/subtitle, nav card labels, hint text, input placeholders, and button labels—lives in the PWA HTML files and the manifest. Edit the files directly; no build step is required.

### Splash / home page — `pwa/index.html`

| What | Where (approx. lines) |
|------|------------------------|
| **Page title** (browser tab) | Line 7: `<title>ERG Air Monitoring — Home</title>` |
| **Header button** | Line 108: `Open ERG Guide` (and the `href` for the link) |
| **Main heading** | Line 112: `<h1>ERG Air Monitoring</h1>` |
| **Subtitle under heading** | Line 114: `<p class="subtitle">Region 9 — Reference table, loadout tool, and links.</p>` |
| **Nav card titles & descriptions** | Lines 116–127: each `<h2>` and `<p>` inside the `.nav-card` links (Air Monitoring Table, Experience Builder, HASP / Loadout PDF Tool) |

### HASP / Loadout PDF tool — `pwa/hasp.html`

| What | Where (approx. lines) |
|------|------------------------|
| **Page title** | Line 7: `<title>HASP / Loadout PDF Tool — ERG</title>` |
| **Loading message** | Line 183: `Loading reference data…` |
| **Page heading & subtitle** | Lines 186–187: `<h1>` and `<p class="subtitle">` |
| **Hint text** (all `<p class="hint">`) | Lines 199, 204, 209, 217, 222, 227 — one per form section |
| **Placeholders** (input hints) | Lines 237, 241, 245: Site/Incident, Incident #, Generated by |
| **Header links** | Line 181: `← ERG Home` and `Open ERG Guide` |

### Air Monitoring Table — `pwa/table.html`

| What | Where (approx. lines) |
|------|------------------------|
| **Page title** | Line 7: `<title>Air Monitoring Table — ERG</title>` |
| **Header links** | Line 225: `← ERG Home`, `Open ERG Guide` |
| **Filter button** | Line 231: `Hide filters` (toggle label) |
| **Filter placeholders** | Lines 237, 239, 241: `placeholder="Search…"` on Chemical, Device, Sensor inputs |
| **Filter column titles** | Lines 244–246: "Chemical (select first)", "Device (only compatible…)", "Sensor (only compatible…)" |
| **Loading message** | Line 253: `Loading air monitoring table…` |
| **No-results message** | Line 256: `No rows match the filter.` |

### App name / install — `pwa/manifest.json`

- **name**: `"ERG Air Monitoring"`
- **short_name**: `"ERG Air"`
- **description**: `"Offline air monitoring table and link to ERG guide"`

After editing, commit and push; the next deploy will serve the updated copy.

---

## 4. How the Excel ties in and gets updated

### Source of truth

- The **air monitoring table** is built from an **Excel workbook** (e.g. `Air_Monitoring_Relationships-2.xlsx`). That workbook typically lives on **SharePoint** as the source of truth; this repo can hold a copy or you can point the build at a downloaded file.

### Pipeline: Excel → CSVs → merged JSON → PWA

| Step | What happens |
|------|----------------|
| 1. Excel in place | Put the workbook in `data_reference/Air_Monitoring_Relationships-2.xlsx`, or keep it elsewhere and pass its path when running the build. |
| 2. Export to CSVs | The build script (or a separate export script) exports each sheet to CSV in `data_reference/` with names like `Air_Monitoring_Relationships-2_Sensor_Chemical.csv`, etc. |
| 3. Merge | `scripts/build_data.py` reads those CSVs, joins Sensor_Chemical → Sensors → Device_Sensor → Devices, Chemicals, and builds one row per chemical/device/sensor with columns like Target Compound, Device, Sensor, Detection Level, PEL, REL, IDLH, PAC-1/2/3, etc. |
| 4. Output | Script writes `data_reference/out/air_monitoring_table.json` and **copies it to `pwa/air_monitoring_table.json`** so the PWA serves the latest table. |

### How to update the table (manual)

1. **Update the Excel** (on SharePoint or replace the file in `data_reference/`).
2. **Run the build** from the **project root**:
   ```bash
   python scripts/build_data.py
   ```
   Or with a specific workbook:
   ```bash
   python scripts/build_data.py path/to/your/workbook.xlsx
   ```
   Or with an environment variable:
   ```bash
   ERG_XLSX_PATH=path/to/workbook.xlsx python scripts/build_data.py
   ```
3. **What the script does:**
   - If the Excel file exists and is **newer** than the key CSV, it re-exports all sheets to CSVs in `data_reference/` (overwrites the `Air_Monitoring_Relationships-2_*.csv` files).
   - It always rebuilds the merged table and overwrites:
     - `data_reference/out/air_monitoring_table.json`
     - `pwa/air_monitoring_table.json`
4. **Commit and push** the updated `pwa/air_monitoring_table.json` (and optionally the CSVs and `data_reference/out/` if you keep them in the repo). Push to `main` → GitHub Actions deploys the PWA with the new table.

### Dependencies for the build

- **Python 3** with:
  - `pandas` (merge logic)
  - `openpyxl` (Excel read; used by the export step)
- Install once: `pip install -r requirements.txt` (from project root).

### Excel → SharePoint / ArcGIS

- The **ExB** app on ArcGIS is typically fed from the same or a related Excel source (uploaded to AGOL). This repo’s pipeline is for the **PWA** table. To keep ExB and PWA on the same data, see `docs/SharePoint_GitHub_ArcGIS_Pipeline.md` (Options A/B/C and §6).

---

## 5. Deployment: GitHub and GitHub Pages

### Repo and branch

- **Default branch:** `main`. The deploy workflow runs on **push to `main`** and on **manual dispatch**.
- **Workflow file:** `.github/workflows/deploy-pages.yml`.

### What the workflow does

1. Checkout the repo.
2. Configure GitHub Pages.
3. Upload the **`pwa/`** folder as the site artifact (so `pwa/` becomes the **root** of the published site).
4. Deploy to GitHub Pages.

So the live site is exactly the contents of the `pwa/` directory at the time of the push. The workflow **does not** run the Python build; it only publishes what’s in `pwa/`. To have the latest table on each deploy, either:

- Run `python scripts/build_data.py` locally before committing and push the updated `pwa/air_monitoring_table.json`, or  
- Add a build step to the workflow (see `docs/SharePoint_GitHub_ArcGIS_Pipeline.md` Option B: Excel in repo + build on deploy).

### Enabling GitHub Pages

- In the repo: **Settings → Pages**.
- **Source:** choose **GitHub Actions** (not “Deploy from a branch”).
- After the first successful run, the site URL will be something like `https://<username>.github.io/<repo-name>/`.

### Manual workflow run

- **Actions** tab → **Deploy to GitHub Pages** → **Run workflow** → Run. Uses the current `main` branch; redeploys the current `pwa/` folder.

---

## 6. How it was built (architecture)

### Repo layout

| Path | Purpose |
|------|--------|
| `pwa/` | PWA app: HTML, service worker, manifest, and static assets. This folder is deployed to GitHub Pages as the site root. |
| `scripts/` | `build_data.py` (Excel/CSV → merged table JSON); `export_xlsx_sheets_to_csv.py` (Excel → CSVs). |
| `data_reference/` | Excel workbook (optional in repo), CSVs exported from it, and `out/air_monitoring_table.json`. |
| `docs/` | Design and pipeline docs: data model, schema, SharePoint/GitHub/ArcGIS pipeline, PWA vs ExB decision, etc. |
| `update-instructions/` | This folder: instructions for updating and deploying the app. |
| `.github/workflows/` | GitHub Actions workflow for deploying `pwa/` to GitHub Pages. |

### Design decisions

- **PWA vs ExB:** The PWA is a **separate shell** (not ExB as the PWA). ExB doesn’t support a custom service worker and manifest for our offline table; this repo’s PWA gives full control over caching and installability. See `docs/ERG_PWA_ExB_Decision.md`.
- **One merged table:** The build produces a single denormalized JSON (one row per chemical/device/sensor) so the PWA doesn’t do joins at runtime. Schema is locked in `docs/Air_Monitoring_Table_Schema.md`.
- **Excel as source:** The merge reads CSVs exported from the Excel workbook; the script can re-export when the workbook is newer than the CSVs, so one command updates everything from Excel to PWA JSON.

### Build script details

- **Inputs:** Excel (or pre-exported CSVs in `data_reference/`). Key sheets: Sensor_Chemical, Sensors, Device_Sensor, Devices, Chemicals.
- **Logic:** Join tables, normalize column names (strip (PK)/(FK)), build display columns (Target Compound, Device, Sensor, Detection Level, PEL, REL, TLV, IDLH, PAC-1/2/3, etc.), add rows for chemicals with no sensor data (filled with —), sort by Target Compound / Device / Sensor.
- **Output:** JSON array of objects; written to `data_reference/out/air_monitoring_table.json` and copied to `pwa/air_monitoring_table.json`.

### Service worker (high level)

- **Install:** Pre-caches shell URLs (index, table, hasp, manifest) and table data JSONs.
- **Activate:** Deletes old caches for previous versions (keys starting with `erg-pwa-` but not the current shell/table caches).
- **Fetch:** Same-origin only. Shell and manifest: cache-first. Table JSONs: cache-first, then fetch and update cache in background when online. Path matching supports both root and subpath deployment (e.g. `/table.html` or `/pwa/table.html`).

---

## 7. Troubleshooting

| Issue | What to check |
|-------|----------------|
| **Table or shell doesn’t work offline** | Ensure the device loaded the app at least once online so the service worker installed. Bump `CACHE_VERSION` in `pwa/sw.js` and redeploy to force cache refresh. |
| **Old table data after updating Excel** | Run `python scripts/build_data.py` (with the correct Excel path), then commit and push `pwa/air_monitoring_table.json`. |
| **Build script says Excel not found** | Put the workbook at `data_reference/Air_Monitoring_Relationships-2.xlsx` or pass the path: `python scripts/build_data.py /path/to/file.xlsx`. |
| **Build fails (missing module)** | Run `pip install -r requirements.txt` (pandas, openpyxl). |
| **GitHub Pages not updating** | Confirm **Settings → Pages** uses **GitHub Actions**. Check the **Actions** tab for a successful run after your push to `main`. |
| **Deploy runs but site is old** | The workflow deploys whatever is in `pwa/` on the branch. Ensure your latest changes are committed and pushed to `main`. |

---

## Related docs

- **Data build and PWA usage:** `docs/Data_Build_README.md`
- **SharePoint, GitHub, ArcGIS, and update options (A/B/C):** `docs/SharePoint_GitHub_ArcGIS_Pipeline.md`
- **PWA vs ExB and build/deploy note:** `docs/ERG_PWA_ExB_Decision.md`
- **Table schema and column set:** `docs/Air_Monitoring_Table_Schema.md`
- **Offline table and PWA plan:** `docs/ERG_Offline_PWA_Data_Plan.md`
- **PWA folder overview:** `pwa/README.md`
