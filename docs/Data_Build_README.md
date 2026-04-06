# How the PWA Uses the Data & How to Update

## How the data is used to build the PWA

1. **Excel → CSV** (`scripts/export_xlsx_sheets_to_csv.py`, invoked from the build when the workbook is newer than the CSVs) exports each workbook sheet except **MultiRAE_Cleaned**, **AreaRAE_Cleaned**, **TVA_PID**, **TVA_FID**, and **Drager_Cleaned** (those tabs are for manual use only and are not written to `data_reference/`).

2. **Build script** (`scripts/build_data.py`) reads your Excel-derived CSVs in `data_reference/`, merges them into one air monitoring table (one row per chemical/device/sensor), and writes:
   - `data_reference/out/air_monitoring_table.json`
   - a copy to `pwa/air_monitoring_table.json`

3. **The PWA** is the folder `pwa/`. When you open the PWA in a browser:
   - `pwa/index.html` loads `pwa/air_monitoring_table.json` and renders it as a table (frozen header, frozen first column, and grouped view so chemical/device show once per group).

4. **Offline:** The PWA’s service worker caches the shell and the JSON so the table works offline after the first load.

---

## Can I see the PWA yet?

Yes. From the project root, serve the `pwa/` folder over HTTP and open the URL in a browser:

```bash
npx serve pwa
```

Then open **http://localhost:3000** (or the port shown). You should see the ERG guide link at the top and the air monitoring table below.

---

## How do I update the table?

1. **Put the Excel file in place**  
   - Either replace `data_reference/Air_Monitoring_Relationships-2.xlsx` with your updated workbook,  
   - Or keep your file elsewhere and pass its path when you run the script (see below).

2. **Run the build script** (from the project root):

   ```bash
   python scripts/build_data.py
   ```

   Or with a specific Excel file:

   ```bash
   python scripts/build_data.py path/to/your/file.xlsx
   ```

   Or using an environment variable:

   ```bash
   ERG_XLSX_PATH=path/to/your/file.xlsx python scripts/build_data.py
   ```

3. **What gets overwritten**  
   - If the Excel file is newer than the CSVs, the script re-exports the workbook to CSVs in `data_reference/` (overwrites `Air_Monitoring_Relationships-2_*.csv`).  
   - The script always overwrites `data_reference/out/air_monitoring_table.json` and `pwa/air_monitoring_table.json` with the new merged table.

So: **drop (or point to) your Excel file, run the one command above, then refresh the PWA** to see the updated table.

---

## Include column (source sheets)

Optional column **`include`** on merge sources (header is matched case-insensitively after the usual PK/FK strip in `build_data.py`): `Sensor_Chemical`, `Sensors`, `Device_Sensor`, `Devices`, `Chemicals`, `Chemical_Method`, `Sampling_Methods`. The same rule applies when you run **`node pwa/scripts/build_cross_sens.js`** for **Sensors** and **Sensor_CrossSens**.

| Value (case-insensitive) | Effect |
|--------------------------|--------|
| **No** | Row is **omitted** from merges / cross-sens JSON. |
| **Yes**, empty, or anything else | Row is **kept**. |

If **`include`** is missing on a sheet, every row is kept (the build prints a **stderr note for Sensors** when the column is absent so you can tell the CSV is out of date). Re-export from Excel and run **`python3 scripts/build_data.py`** to refresh CSVs. The column is stripped before joins so it never appears in `air_monitoring_table.json`.

---

## Correction factors (PID) — source format and tools

Values in **`Sensor_Chemical.correction_factor`** (merged to column **`Correction Factor`** in `air_monitoring_table.json`) are stored as **plain text** in the sheet. Conventions:

| Form | Example | Meaning |
|------|---------|--------|
| Single | `10`, `1.5` | One correction factor (positive number). |
| Range with “to” | `0.7 to 0.9` | Vendor range; endpoints can be in either order. |
| Range with dash | `0.7-0.9`, `0.7 - 0.9` | Same as range; hyphen, en-dash (`–`), or em-dash (`—`) between numbers are accepted in the PID calculator. |

Avoid commas inside numbers for ranges unless parser support is added later (e.g. use `0.7-0.9` not `0,7-0,9`). Use `—` / leave empty / `ND` where there is no CF.

**Reference implementation:** `parseCf()` in `pwa/pid-calculator.html` turns these strings into `{ kind: 'single' \| 'range' \| 'none', ... }` for math (including implied-ppm bands for ranges).

**Future tools (e.g. IDLH-aware calculator):** Reuse the same parsing rules and interval logic as `parseCf` / `impliedPpmFromRef` so CF ranges stay consistent app-wide; consider extracting a shared small JS module when you add that feature.
