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


def _include_column_name(df):
    for c in df.columns:
        if str(c).strip().lower() == "include":
            return c
    return None


def filter_rows_by_include(df, table_label=None):
    """
    Column **include** (case-insensitive header): only **No** excludes a row; **Yes**, blank, or anything else keeps it.
    If the column is missing, all rows are kept. The column is dropped after filtering.
    """
    import pandas as pd

    col = _include_column_name(df)
    if col is None:
        if table_label == "Sensors":
            print(
                "Note: Sensors table has no Include column in the CSV — all sensor rows are included. "
                "Save the Excel file and run the build so sheets re-export if you added Include.",
                file=sys.stderr,
            )
        return df

    def keep(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return True
        return str(val).strip().lower() != "no"

    out = df[df[col].apply(keep)].copy()
    out = out.drop(columns=[col], errors="ignore")
    return out.reset_index(drop=True)

def safe_str(val):
    if val is None or (isinstance(val, float) and pd is not None and pd.isna(val)):
        return "—"
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "na", "n/a"):
        return "—"
    # Collapse newlines for display
    return " ".join(s.split())

def summarize_methods_group(group):
    """Keep method rows aligned across columns for chemical-level rendering."""
    seen = set()
    rows = []
    for _, row in group.iterrows():
        rec = (
            safe_str(row.get("method_id")),
            safe_str(row.get("sample_volume")),
            safe_str(row.get("flow_rate")),
            safe_str(row.get("media_type")),
            safe_str(row.get("hold_time")),
        )
        # De-duplicate exact repeated method rows while preserving order.
        if rec in seen:
            continue
        seen.add(rec)
        rows.append(rec)
    if not rows:
        rows = [("—", "—", "—", "—", "—")]
    # " || " is a row delimiter for renderer split.
    return pd.Series({
        "method_id": " || ".join(r[0] for r in rows),
        "sample_volume": " || ".join(r[1] for r in rows),
        "flow_rate": " || ".join(r[2] for r in rows),
        "media_type": " || ".join(r[3] for r in rows),
        "hold_time": " || ".join(r[4] for r in rows),
    })

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
    cm = read_csv_with_title_row(path("Chemical_Method"))
    sm = read_csv_with_title_row(path("Sampling_Methods"))

    # Normalize join keys
    for df in (sc, sens, ds, dev, chem):
        df.columns = [c.strip() for c in df.columns]
    for df in (cm, sm):
        df.columns = [c.strip() for c in df.columns]

    sc = filter_rows_by_include(sc, "Sensor_Chemical")
    sens = filter_rows_by_include(sens, "Sensors")
    ds = filter_rows_by_include(ds, "Device_Sensor")
    dev = filter_rows_by_include(dev, "Devices")
    chem = filter_rows_by_include(chem, "Chemicals")
    cm = filter_rows_by_include(cm, "Chemical_Method")
    sm = filter_rows_by_include(sm, "Sampling_Methods")

    # Drop rows where key join columns are missing
    sc = sc.dropna(subset=["sensor_id", "chemical_id"])
    sens = sens.dropna(subset=["sensor_id"])
    ds = ds.dropna(subset=["device_id", "sensor_id"])
    dev = dev.dropna(subset=["device_id"])
    chem = chem.dropna(subset=["cas_number"])
    cm = cm.dropna(subset=["chemical_id", "method_id"])
    sm = sm.dropna(subset=["method_id"])

    # Build per-chemical method metadata from Chemical_Method (junction) plus Sampling_Methods.
    # Requested source split:
    # - From Chemical_Method: method_id, sample_volume, flow_rate
    # - From Sampling_Methods: media_type, hold_time
    cm_sm = cm.merge(sm[["method_id", "media_type", "hold_time"]], on="method_id", how="left")
    cm_summary = (
        cm_sm.groupby("chemical_id", dropna=False, sort=False)[["method_id", "sample_volume", "flow_rate", "media_type", "hold_time"]]
        .apply(summarize_methods_group)
        .reset_index()
    )

    # Join: Sensor_Chemical -> Sensors (sensor_id); then Device_Sensor (sensor_id) -> Devices (device_id); then Chemicals (chemical_id -> cas_number)
    m = sc.merge(sens, on="sensor_id", how="left")
    m = m.merge(ds, on="sensor_id", how="left")
    m = m.merge(dev, on="device_id", how="left", suffixes=("", "_dev"))
    m = m.merge(chem, left_on="chemical_id", right_on="cas_number", how="left", suffixes=("", "_chem"))
    m = m.merge(cm_summary, on="chemical_id", how="left")

    # Drop rows that didn't match (e.g. chemical_id not in Chemicals)
    m = m.dropna(subset=["chemical_name", "model", "plain_name"])

    # Device and Sensor (separate columns for grouped UI: show device once, each sensor its own row)
    m["Device"] = m["model"].astype(str).str.strip()
    m["Sensor"] = m["plain_name"].astype(str).str.strip()
    if "technology" in m.columns:
        m["Technology"] = m["technology"].apply(safe_str)
    else:
        m["Technology"] = pd.Series(["—"] * len(m))

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
    # Correction Factor: from Sensor_Chemical whenever populated (LEL response factors, PID CFs, etc.)
    def correction_factor(row):
        cf = row.get("correction_factor")
        if cf is None or (isinstance(cf, float) and pd.isna(cf)):
            return "—"
        s = str(cf).strip()
        if s == "" or s.lower() in ("nan", "na", "n/a"):
            return "—"
        return safe_str(cf)

    m["Correction Factor"] = m.apply(correction_factor, axis=1) if "correction_factor" in m.columns else pd.Series(["—"] * len(m))

    # Regulatory from Chemicals
    m["PEL"] = m.get("pel_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["REL"] = m.get("rel", pd.Series(["—"] * len(m))).apply(safe_str)
    m["TLV"] = m.get("tlv_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["IDLH"] = m.get("idlh_ppm", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-1"] = m.get("aegl_1", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-2"] = m.get("aegl_2", pd.Series(["—"] * len(m))).apply(safe_str)
    m["PAC-3"] = m.get("aegl_3", pd.Series(["—"] * len(m))).apply(safe_str)
    m["method_id"] = m.get("method_id", pd.Series(["—"] * len(m))).apply(safe_str)
    m["sample_volume"] = m.get("sample_volume", pd.Series(["—"] * len(m))).apply(safe_str)
    m["flow_rate"] = m.get("flow_rate", pd.Series(["—"] * len(m))).apply(safe_str)
    m["media_type"] = m.get("media_type", pd.Series(["—"] * len(m))).apply(safe_str)
    m["hold_time"] = m.get("hold_time", pd.Series(["—"] * len(m))).apply(safe_str)
    m["Air Sampling Method"] = m["method_id"]

    # Target Compound = chemical_name
    m["Target Compound"] = m["chemical_name"].astype(str).apply(lambda x: " ".join(x.split()))

    # Sort so consecutive rows group by chemical, then device, then sensor (for UI merged cells)
    m = m.sort_values(by=["Target Compound", "Device", "Sensor"], kind="stable")

    # Build output rows: Target Compound, Device, Sensor, Detection Level, Ionization Potential (eV), Correction Factor, then regulatory
    columns_order = [
        "Target Compound", "Device", "Sensor", "Technology", "Detection Level", "Ionization Potential (eV)", "Correction Factor",
        "PEL", "REL", "TLV", "IDLH", "PAC-1", "PAC-2", "PAC-3",
        "method_id", "sample_volume", "flow_rate", "media_type", "hold_time", "Air Sampling Method"
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
            "Technology": "—",
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
            "method_id": "—",
            "sample_volume": "—",
            "flow_rate": "—",
            "media_type": "—",
            "hold_time": "—",
            "Air Sampling Method": "—",
        })
    # Fill chemical-only rows with method data where available.
    chem_method_map = cm_summary.set_index("chemical_id").to_dict(orient="index") if len(cm_summary) else {}
    for row in out:
        if row["method_id"] != "—":
            continue
        key = row.get("Target Compound")
        # chemical_id values align to Chemicals.cas_number, while Target Compound is name;
        # map by chemical_name -> cas_number first for reliable lookup.
        # Build this map once lazily.
        if "_chem_name_to_cas" not in locals():
            _chem_name_to_cas = {}
            for _, cr in chem.iterrows():
                nm = " ".join(str(cr.get("chemical_name", "") or "").split())
                cas = safe_str(cr.get("cas_number"))
                if nm and cas != "—":
                    _chem_name_to_cas[nm] = cas
        cas = _chem_name_to_cas.get(key)
        method_meta = chem_method_map.get(cas) if cas else None
        if method_meta:
            row["method_id"] = safe_str(method_meta.get("method_id"))
            row["sample_volume"] = safe_str(method_meta.get("sample_volume"))
            row["flow_rate"] = safe_str(method_meta.get("flow_rate"))
            row["media_type"] = safe_str(method_meta.get("media_type"))
            row["hold_time"] = safe_str(method_meta.get("hold_time"))
            row["Air Sampling Method"] = row["method_id"]
    # Re-sort so all rows are by Target Compound, then Device, then Sensor (chemicals-without-sensors end up as single-row blocks)
    out.sort(key=lambda r: (r["Target Compound"], r["Device"], r["Sensor"]))
    return out


def build_matrix_sampling_rows():
    """
    Contaminant / matrix / sampling media reference from Matrix_Sampling.csv.
    Truncates before the in-sheet footnote (row starting with 'Note:'); forward-fills Contaminant.
    """
    path = os.path.join(_data_ref(), "Matrix_Sampling.csv")
    if not os.path.isfile(path):
        return []

    df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    df.columns = [normalize_header(c) for c in df.columns]
    drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")

    col_cont = "Contaminant"
    if col_cont not in df.columns:
        print("Matrix_Sampling.csv: missing Contaminant column", file=sys.stderr)
        return []

    cut = len(df)
    for i, val in enumerate(df[col_cont].astype(str)):
        s = str(val).strip() if pd.notna(val) and str(val) != "nan" else ""
        if s.lower().startswith("note:"):
            cut = i
            break
    df = df.iloc[:cut].copy()
    df = df.dropna(how="all")

    method_col = "Analytical Method"
    matrix_col = "Matrix"
    media_col = "Sampling Media"

    def row_has_sampling_info(row):
        for c in (method_col, matrix_col, media_col):
            if c not in df.columns:
                continue
            v = row.get(c)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            if str(v).strip():
                return True
        return False

    df = df[df.apply(row_has_sampling_info, axis=1)].copy()
    df[col_cont] = df[col_cont].apply(
        lambda x: x if (pd.notna(x) and str(x).strip() and str(x).strip().lower() != "nan") else pd.NA
    )
    df[col_cont] = df[col_cont].ffill()
    df = df.dropna(subset=[col_cont])
    df[col_cont] = df[col_cont].apply(lambda x: str(x).strip())

    rows_out = []
    for _, row in df.iterrows():
        rec = {}
        for c in df.columns:
            rec[c] = safe_str(row.get(c))
        rows_out.append(rec)

    rows_out.sort(
        key=lambda r: (
            r.get(col_cont, "").lower(),
            r.get(method_col, "").lower(),
            r.get(matrix_col, "").lower(),
        )
    )
    return rows_out


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

    print("Building matrix / sampling reference...")
    matrix_rows = build_matrix_sampling_rows()
    matrix_out = os.path.join(_out_dir(), "matrix_sampling.json")
    with open(matrix_out, "w", encoding="utf-8") as f:
        json.dump(matrix_rows, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(matrix_rows)} rows to {matrix_out}")
    matrix_pwa = os.path.join(_pwa_dir(), "matrix_sampling.json")
    if os.path.isdir(_pwa_dir()):
        with open(matrix_pwa, "w", encoding="utf-8") as f:
            json.dump(matrix_rows, f, indent=2, ensure_ascii=False)
        print(f"Copied to {matrix_pwa}")

    print("Done.")

if __name__ == "__main__":
    main()
