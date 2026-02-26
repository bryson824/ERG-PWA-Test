#!/usr/bin/env python3
"""
Build the air monitoring table from Excel (or existing CSVs).
Pipeline: Excel → CSVs (if needed) → merge → air_monitoring_table.json.
Output: data_reference/out/air_monitoring_table.json, then copy to pwa/air_monitoring_table.json.
Schema: docs/Air_Monitoring_Table_Schema.md (12 columns, one row per chemical/device/sensor).

Usage:
  python scripts/build_data.py
  python scripts/build_data.py path/to/workbook.xlsx
  ERG_XLSX_PATH=path/to/file.xlsx python scripts/build_data.py
"""
import json
import os
import re
import sys

try:
    import pandas as pd
except ImportError:
    pd = None

def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _data_ref():
    return os.path.join(_repo_root(), "data_reference")

def _out_dir():
    d = os.path.join(_data_ref(), "out")
    os.makedirs(d, exist_ok=True)
    return d

def _pwa_dir():
    return os.path.join(_repo_root(), "pwa")

def _xlsx_path():
    if os.environ.get("ERG_XLSX_PATH"):
        return os.path.abspath(os.environ["ERG_XLSX_PATH"])
    return os.path.join(_data_ref(), "Air_Monitoring_Relationships-2.xlsx")

def run_excel_export(xlsx_path):
    """Reuse existing export script to refresh CSVs from Excel."""
    export_script = os.path.join(os.path.dirname(__file__), "export_xlsx_sheets_to_csv.py")
    import subprocess
    r = subprocess.run([sys.executable, export_script, xlsx_path], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        raise SystemExit(r.returncode)

def normalize_header(name):
    if not isinstance(name, str):
        return str(name).strip()
    name = name.strip()
    name = re.sub(r"\s*\(PK\)\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(FK\)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()

def read_csv_with_title_row(path, header_row_index=1):
    import pandas as pd
    # First row is often title; header is second row
    df = pd.read_csv(path, header=header_row_index, encoding="utf-8", on_bad_lines="warn", low_memory=False)
    df.columns = [normalize_header(c) for c in df.columns]
    return df

def safe_str(val):
    if val is None or (isinstance(val, float) and pd is not None and pd.isna(val)):
        return "—"
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "na", "n/a"):
        return "—"
    # Collapse newlines for display
    return " ".join(s.split())

def build_merged_table():
    data_ref = _data_ref()
    base = "Air_Monitoring_Relationships-2"

    def path(name):
        return os.path.join(data_ref, f"{base}_{name}.csv")

    # Load tables (header on row 1)
    sc = read_csv_with_title_row(path("Sensor_Chemical"))
    sens = read_csv_with_title_row(path("Sensors"))
    ds = read_csv_with_title_row(path("Device_Sensor"))
    dev = read_csv_with_title_row(path("Devices"))
    chem = read_csv_with_title_row(path("Chemicals"))

    # Normalize join keys
    for df in (sc, sens, ds, dev, chem):
        df.columns = [c.strip() for c in df.columns]

    # Drop rows where key join columns are missing
    sc = sc.dropna(subset=["sensor_id", "chemical_id"])
    sens = sens.dropna(subset=["sensor_id"])
    ds = ds.dropna(subset=["device_id", "sensor_id"])
    dev = dev.dropna(subset=["device_id"])
    chem = chem.dropna(subset=["cas_number"])

    # Join: Sensor_Chemical -> Sensors (sensor_id); then Device_Sensor (sensor_id) -> Devices (device_id); then Chemicals (chemical_id -> cas_number)
    m = sc.merge(sens, on="sensor_id", how="left")
    m = m.merge(ds, on="sensor_id", how="left")
    m = m.merge(dev, on="device_id", how="left", suffixes=("", "_dev"))
    m = m.merge(chem, left_on="chemical_id", right_on="cas_number", how="left", suffixes=("", "_chem"))

    # Drop rows that didn't match (e.g. chemical_id not in Chemicals)
    m = m.dropna(subset=["chemical_name", "model", "plain_name"])

    # Device and Sensor (separate columns for grouped UI: show device once, each sensor its own row)
    m["Device"] = m["model"].astype(str).str.strip()
    m["Sensor"] = m["plain_name"].astype(str).str.strip()

    # Detection Level: detection_range_low–high range_unit, or Sensors.detection_range
    def detection_level(row):
        low = row.get("detection_range_low")
        high = row.get("detection_range_high")
        unit = row.get("range_unit")
        if pd.notna(low) and pd.notna(high) and pd.notna(unit):
            return f"{low}–{high} {unit}"
        dr = row.get("detection_range")
        if pd.notna(dr) and str(dr).strip():
            return safe_str(dr)
        return "—"
    m["Detection Level"] = m.apply(detection_level, axis=1)

    # Ionization Potential (eV): from Chemicals, same per chemical — merged in UI
    m["Ionization Potential (eV)"] = m.get("IP (eV)", pd.Series([None] * len(m))).apply(safe_str)
    # Correction Factor: from Sensor_Chemical, per sensor row; "—" when not applicable (e.g. non-PID)
    def correction_factor(row):
        tech = str(row.get("technology") or "")
        if "PID" in tech or "pid" in tech:
            cf = row.get("correction_factor")
            return safe_str(cf) if pd.notna(cf) else "—"
        return "—"
    m["Correction Factor"] = m.apply(correction_factor, axis=1) if "correction_factor" in m.columns else pd.Series(["—"] * len(m))

    # Regulatory from Chemicals
    m["PEL"] = m.get("pel_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["REL"] = m.get("rel", pd.Series(["—"] * len(m))).apply(safe_str)
    m["TLV"] = m.get("tlv_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["IDLH"] = m.get("idlh_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-1"] = m.get("aegl_1", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-2"] = m.get("aegl_2", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-3"] = m.get("aegl_3", pd.Series(["—"] * len(m))).apply(safe_str)
    m["Air Sampling Method"] = "—"

    # Target Compound = chemical_name
    m["Target Compound"] = m["chemical_name"].astype(str).apply(lambda x: " ".join(x.split()))

    # Sort so consecutive rows group by chemical, then device, then sensor (for UI merged cells)
    m = m.sort_values(by=["Target Compound", "Device", "Sensor"], kind="stable")

    # Build output rows: Target Compound, Device, Sensor, Detection Level, Ionization Potential (eV), Correction Factor, then regulatory
    columns_order = [
        "Target Compound", "Device", "Sensor", "Detection Level", "Ionization Potential (eV)", "Correction Factor",
        "PEL", "REL", "TLV", "IDLH", "PAC-1", "PAC-2", "PAC-3", "Air Sampling Method"
    ]
    out = []
    for _, row in m.iterrows():
        out.append({col: safe_str(row[col]) for col in columns_order})

    # Include ALL chemicals: add one row per chemical that has no sensor data (fill with —)
    cas_with_sensors = set(m["cas_number"].astype(str).unique()) if len(m) else set()
    chem_all = chem[~chem["cas_number"].astype(str).isin(cas_with_sensors)]
    for _, row in chem_all.iterrows():
        name = " ".join(str(row.get("chemical_name", "") or "").split())
        out.append({
            "Target Compound": name or "—",
            "Device": "—",
            "Sensor": "—",
            "Detection Level": "—",
            "Ionization Potential (eV)": safe_str(row.get("IP (eV)")),
            "Correction Factor": "—",
            "PEL": safe_str(row.get("pel_ppm")),
            "REL": safe_str(row.get("rel")),
            "TLV": safe_str(row.get("tlv_ppm")),
            "IDLH": safe_str(row.get("idlh_ppm")),
            "PAC-1": safe_str(row.get("aegl_1")),
            "PAC-2": safe_str(row.get("aegl_2")),
            "PAC-3": safe_str(row.get("aegl_3")),
            "Air Sampling Method": "—",
        })
    # Re-sort so all rows are by Target Compound, then Device, then Sensor (chemicals-without-sensors end up as single-row blocks)
    out.sort(key=lambda r: (r["Target Compound"], r["Device"], r["Sensor"]))
    return out

def main():
    if pd is None:
        print("Need pandas. Run: pip install -r requirements.txt")
        sys.exit(1)
    xlsx_path = _xlsx_path()
    if len(sys.argv) > 1:
        xlsx_path = os.path.abspath(sys.argv[1])
    data_ref = _data_ref()
    base = "Air_Monitoring_Relationships-2"
    csv_path = os.path.join(data_ref, f"{base}_Sensor_Chemical.csv")

    # If Excel exists and is newer than the key CSV, re-export
    if os.path.isfile(xlsx_path):
        if not os.path.isfile(csv_path) or os.path.getmtime(xlsx_path) > os.path.getmtime(csv_path):
            print("Exporting Excel to CSVs...")
            run_excel_export(xlsx_path)
    else:
        print(f"Excel not found at {xlsx_path}; using existing CSVs in data_reference/")

    if not os.path.isfile(csv_path):
        print(f"Missing {csv_path}. Run with Excel path or export first.")
        sys.exit(1)

    print("Building merged air monitoring table...")
    rows = build_merged_table()
    out_path = os.path.join(_out_dir(), "air_monitoring_table.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} rows to {out_path}")

    pwa_path = os.path.join(_pwa_dir(), "air_monitoring_table.json")
    if os.path.isdir(_pwa_dir()):
        with open(pwa_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        print(f"Copied to {pwa_path}")
    print("Done.")

if __name__ == "__main__":
    main()
