# ERG PWA shell

Minimal installable PWA: air monitoring table (offline) + link to primary ERG guide.

- **Entry:** `index.html` — loads `air_monitoring_table.json`, registers service worker.
- **Data:** Placeholder `air_monitoring_table.json` is included. For production, replace with output from the merge script: copy `data_reference/out/air_monitoring_table.json` to `pwa/air_monitoring_table.json` (or add a build step that does this).

## Run locally

Serve this folder over HTTPS or localhost (required for service worker):

```bash
npx serve pwa
# or: python -m http.server 8080 --directory pwa
```

Then open the URL (e.g. http://localhost:3000) and use “Add to home screen” / “Install app” if available.

## Placeholders for ui-engineer

- **ERG guide link:** Header block and `#erg-guide-link` — replace with final URL, copy, and styling.
- **Air sheet table:** `#table-container` and `.air-table` — replace with frozen header row + frozen first column implementation per design.

## Correction factors (PID)

How to enter CFs in Excel and how the PID calculator parses them (single value vs ranges, dash form) is documented in **`docs/Data_Build_README.md`** under *Correction factors (PID)*. Future tools such as an **IDLH calculator** should follow that spec and align with `parseCf` in `pid-calculator.html` (or a shared module extracted from it).

## Coordination

See `docs/ERG_PWA_ExB_Decision.md` for esri-sme decision, ExB constraints, and what’s needed from ui-engineer and business-analyst.
