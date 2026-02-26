# How the PWA Uses the Data & How to Update

## How the data is used to build the PWA

1. **Build script** (`scripts/build_data.py`) reads your Excel-derived CSVs in `data_reference/`, merges them into one air monitoring table (one row per chemical/device/sensor), and writes:
   - `data_reference/out/air_monitoring_table.json`
   - a copy to `pwa/air_monitoring_table.json`

2. **The PWA** is the folder `pwa/`. When you open the PWA in a browser:
   - `pwa/index.html` loads `pwa/air_monitoring_table.json` and renders it as a table (frozen header, frozen first column, and grouped view so chemical/device show once per group).

3. **Offline:** The PWA’s service worker caches the shell and the JSON so the table works offline after the first load.

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
